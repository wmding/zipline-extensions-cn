from zipline.finance.slippage import SlippageModel
import math
from pandas import isnull
from zipline.finance.transaction import create_transaction


# SELL = 1 << 0
# BUY = 1 << 1
# STOP = 1 << 2
# LIMIT = 1 << 3
#
# SQRT_252 = math.sqrt(252)
#
DEFAULT_EQUITY_VOLUME_SLIPPAGE_BAR_LIMIT = 0.25


# DEFAULT_FUTURE_VOLUME_SLIPPAGE_BAR_LIMIT = 0.05


class LiquidityExceeded(Exception):
    pass


def fill_price_worse_than_limit_price(fill_price, order):
    """
    Checks whether the fill price is worse than the order's limit price.

    Parameters
    ----------
    fill_price: float
        The price to check.

    order: zipline.finance.order.Order
        The order whose limit price to check.

    Returns
    -------
    bool: Whether the fill price is above the limit price (for a buy) or below
    the limit price (for a sell).
    """
    if order.limit:
        # this is tricky! if an order with a limit price has reached
        # the limit price, we will try to fill the order. do not fill
        # these shares if the impacted price is worse than the limit
        # price. return early to avoid creating the transaction.

        # buy order is worse if the impacted price is greater than
        # the limit price. sell order is worse if the impacted price
        # is less than the limit price
        if (order.direction > 0 and fill_price > order.limit) or \
                (order.direction < 0 and fill_price < order.limit):
            return True

    return False


def reach_limit_price(impacted_price, pre_price, order):
    print(order.asset, "达到价格限制")
    if math.isnan(pre_price):
        return True
    if order.direction > 0:
        return impacted_price >= round(pre_price * 1.1, 2)
    else:
        return impacted_price <= round(pre_price * 0.9, 2)


class VolumeShareSlippage(SlippageModel):
    """
    Model slippage as a quadratic function of percentage of historical volume.

    Orders to buy will be filled at::

       price * (1 + price_impact * (volume_share ** 2))

    Orders to sell will be filled at::

       price * (1 - price_impact * (volume_share ** 2))

    where ``price`` is the close price for the bar, and ``volume_share`` is the
    percentage of minutely volume filled, up to a max of ``volume_limit``.

    Parameters
    ----------
    volume_limit : float, optional
        Maximum percent of historical volume that can fill in each bar. 0.5
        means 50% of historical volume. 1.0 means 100%. Default is 0.025 (i.e.,
        2.5%).
    price_impact : float, optional
        Scaling coefficient for price impact. Larger values will result in more
        simulated price impact. Smaller values will result in less simulated
        price impact. Default is 0.1.
    """

    def __init__(self,
                 volume_limit=DEFAULT_EQUITY_VOLUME_SLIPPAGE_BAR_LIMIT,
                 price_impact=0.1):

        super(VolumeShareSlippage, self).__init__()

        self.volume_limit = volume_limit
        self.price_impact = price_impact

    def __repr__(self):
        return """
{class_name}(
    volume_limit={volume_limit},
    price_impact={price_impact})
""".strip().format(class_name=self.__class__.__name__,
                   volume_limit=self.volume_limit,
                   price_impact=self.price_impact)

    def process_order(self, data, order):
        volume = data.current(order.asset, "volume")

        max_volume = int(self.volume_limit * volume)

        # price impact accounts for the total volume of transactions
        # created against the current minute bar
        remaining_volume = max_volume - self.volume_for_bar

        if remaining_volume < 1:
            # we can't fill any more transactions
            raise LiquidityExceeded()

        # the current order amount will be the min of the
        # volume available in the bar or the open amount.
        cur_volume = int(min(remaining_volume, abs(order.open_amount)))
        print(data.current_dt, order.asset, volume, max_volume, remaining_volume, order.open_amount, self.volume_for_bar, order.id)

        if cur_volume < 1:
            return None, None

        # tally the current amount into our total amount ordered.
        # total amount will be used to calculate price impact
        total_volume = self.volume_for_bar + cur_volume

        volume_share = min(total_volume / volume,
                           self.volume_limit)

        price = data.current(order.asset, "close")
        pre_price = data.history(order.asset, bar_count=2, fields='close', frequency='1d')[0]

        # BEGIN
        #
        # Remove this block after fixing data to ensure volume always has
        # corresponding price.
        if isnull(price):
            return
        # END

        simulated_impact = volume_share ** 2 \
                           * math.copysign(self.price_impact, order.direction) \
                           * price
        impacted_price = price + simulated_impact

        if fill_price_worse_than_limit_price(impacted_price, order):
            return None, None

        if reach_limit_price(impacted_price, pre_price, order):
            return None, None

        return (
            impacted_price,
            math.copysign(cur_volume, order.direction)
        )

    def simulate(self, data, asset, orders_for_asset):
        self._volume_for_bar = 0
        volume = data.current(asset, "volume")

        if volume == 0:
            return

        # can use the close price, since we verified there's volume in this
        # bar.
        price = data.current(asset, "close")

        # BEGIN
        #
        # Remove this block after fixing data to ensure volume always has
        # corresponding price.
        if isnull(price):
            return
        # END
        dt = data.current_dt

        for order in orders_for_asset:
            if order.open_amount == 0:
                continue

            order.check_triggers(price, dt)
            if not order.triggered:
                continue

            txn = None

            try:
                execution_price, execution_volume = \
                    self.process_order(data, order)
                if execution_price is not None:
                    print("执行价格判断成功")

                    txn = create_transaction(
                        order,
                        data.current_dt,
                        execution_price,
                        execution_volume
                    )

            except LiquidityExceeded:
                break

            if txn:
                self._volume_for_bar += abs(txn.amount)
                yield order, txn

    def asdict(self):
        return self.__dict__