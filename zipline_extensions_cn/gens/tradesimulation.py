from zipline.gens.tradesimulation import AlgorithmSimulator

from contextlib2 import ExitStack
from zipline.utils.api_support import ZiplineAPI
from six import viewkeys

from zipline.gens.sim_engine import (
    BAR,
    SESSION_START,
    SESSION_END,
    MINUTE_END,
    BEFORE_TRADING_START_BAR
)


class CNAlgorithmSimulator(AlgorithmSimulator):

    def transform(self):
        """
        Main generator work loop.
        """
        algo = self.algo
        metrics_tracker = algo.metrics_tracker
        emission_rate = metrics_tracker.emission_rate

        def every_bar(dt_to_use, current_data=self.current_data,
                      handle_data=algo.event_manager.handle_data):
            for capital_change in calculate_minute_capital_changes(dt_to_use):
                yield capital_change

            self.simulation_dt = dt_to_use
            # called every tick (minute or day).
            algo.on_dt_changed(dt_to_use)


            handle_data(algo, current_data, dt_to_use)


            blotter = algo.blotter


            # handle any transactions and commissions coming out new orders
            # placed in the last bar
            new_transactions, new_commissions, closed_orders = \
                blotter.get_transactions(current_data)

            blotter.prune_orders(closed_orders)

            for transaction in new_transactions:
                metrics_tracker.process_transaction(transaction)

                # since this order was modified, record it
                order = blotter.orders[transaction.order_id]
                metrics_tracker.process_order(order)

            for commission in new_commissions:
                metrics_tracker.process_commission(commission)


            # grab any new orders from the blotter, then clear the list.
            # this includes cancelled orders.
            new_orders = blotter.new_orders
            blotter.new_orders = []

            # if we have any new orders, record them so that we know
            # in what perf period they were placed.
            for new_order in new_orders:
                metrics_tracker.process_order(new_order)

        def once_a_day(midnight_dt, current_data=self.current_data,
                       data_portal=self.data_portal):
            # process any capital changes that came overnight
            for capital_change in algo.calculate_capital_changes(
                    midnight_dt, emission_rate=emission_rate,
                    is_interday=True):
                yield capital_change

            # set all the timestamps
            self.simulation_dt = midnight_dt
            algo.on_dt_changed(midnight_dt)

            metrics_tracker.handle_market_open(
                midnight_dt,
                algo.data_portal,
            )

            # handle any splits that impact any positions or any open orders.
            assets_we_care_about = (
                    viewkeys(metrics_tracker.positions) |
                    viewkeys(algo.blotter.open_orders)
            )

            if assets_we_care_about:
                splits = data_portal.get_splits(assets_we_care_about,
                                                midnight_dt)
                if splits:
                    algo.blotter.process_splits(splits)
                    metrics_tracker.handle_splits(splits)

        def on_exit():
            # Remove references to algo, data portal, et al to break cycles
            # and ensure deterministic cleanup of these objects when the
            # simulation finishes.
            self.algo = None
            self.benchmark_source = self.current_data = self.data_portal = None

        with ExitStack() as stack:
            stack.callback(on_exit)
            stack.enter_context(self.processor)
            stack.enter_context(ZiplineAPI(self.algo))

            if algo.data_frequency == 'minute':
                def execute_order_cancellation_policy():
                    algo.blotter.execute_cancel_policy(SESSION_END)

                def calculate_minute_capital_changes(dt):
                    # process any capital changes that came between the last
                    # and current minutes
                    return algo.calculate_capital_changes(
                        dt, emission_rate=emission_rate, is_interday=False)
            else:
                def execute_order_cancellation_policy():
                    pass

                def calculate_minute_capital_changes(dt):
                    return []

            for dt, action in self.clock:
                if action == BAR:
                    for capital_change_packet in every_bar(dt):
                        yield capital_change_packet
                elif action == SESSION_START:
                    for capital_change_packet in once_a_day(dt):
                        yield capital_change_packet
                elif action == SESSION_END:
                    # End of the session.
                    positions = metrics_tracker.positions
                    position_assets = algo.asset_finder.retrieve_all(positions)
                    self._cleanup_expired_assets(dt, position_assets)

                    execute_order_cancellation_policy()
                    algo.validate_account_controls()

                    yield self._get_daily_message(dt, algo, metrics_tracker)
                elif action == BEFORE_TRADING_START_BAR:
                    self.simulation_dt = dt
                    algo.on_dt_changed(dt)
                    algo.before_trading_start(self.current_data)
                elif action == MINUTE_END:
                    minute_msg = self._get_minute_message(
                        dt,
                        algo,
                        metrics_tracker,
                    )

                    yield minute_msg

            risk_message = metrics_tracker.handle_simulation_end(
                self.data_portal,
            )
            yield risk_message
