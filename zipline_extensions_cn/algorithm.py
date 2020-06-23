from zipline import TradingAlgorithm
from trading_calendars.utils.pandas_utils import days_at_time
from datetime import time
from zipline.gens.sim_engine import MinuteSimulationClock


class CNTradingAlgorithm(TradingAlgorithm):

    def _create_clock(self):
        """
        If the clock property is not set, then create one based on frequency.
        """
        trading_o_and_c = self.trading_calendar.schedule.ix[
            self.sim_params.sessions]
        market_closes = trading_o_and_c['market_close']
        minutely_emission = False

        if self.sim_params.data_frequency == 'minute':
            market_opens = trading_o_and_c['market_open']
            minutely_emission = self.sim_params.emission_rate == "minute"

            # The calendar's execution times are the minutes over which we
            # actually want to run the clock. Typically the execution times
            # simply adhere to the market open and close times. In the case of
            # the futures calendar, for example, we only want to simulate over
            # a subset of the full 24 hour calendar, so the execution times
            # dictate a market open time of 6:31am US/Eastern and a close of
            # 5:00pm US/Eastern.
            execution_opens = \
                self.trading_calendar.execution_time_from_open(market_opens)
            execution_closes = \
                self.trading_calendar.execution_time_from_close(market_closes)
        else:
            # in daily mode, we want to have one bar per session, timestamped
            # as the last minute of the session.
            execution_closes = \
                self.trading_calendar.execution_time_from_close(market_closes)
            execution_opens = execution_closes

        # FIXME generalize these values
        # 修改为东八市区
        before_trading_start_minutes = days_at_time(
            self.sim_params.sessions,
            time(8, 45),
            "Asia/Shanghai"
        )

        return MinuteSimulationClock(
            self.sim_params.sessions,
            execution_opens,
            execution_closes,
            before_trading_start_minutes,
            minute_emission=minutely_emission,
        )
