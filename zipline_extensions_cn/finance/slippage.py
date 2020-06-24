from zipline.finance.slippage import SlippageModel
import math
from pandas import isnull

# SELL = 1 << 0
# BUY = 1 << 1
# STOP = 1 << 2
# LIMIT = 1 << 3
#
# SQRT_252 = math.sqrt(252)
#
DEFAULT_EQUITY_VOLUME_SLIPPAGE_BAR_LIMIT = 0.025
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

        max_volume = self.volume_limit * volume

        # price impact accounts for the total volume of transactions
        # created against the current minute bar
        remaining_volume = max_volume - self.volume_for_bar
        if remaining_volume < 1:
            # we can't fill any more transactions
            raise LiquidityExceeded()

        # the current order amount will be the min of the
        # volume available in the bar or the open amount.
        cur_volume = int(min(remaining_volume, abs(order.open_amount)))

        if cur_volume < 1:
            return None, None

        # tally the current amount into our total amount ordered.
        # total amount will be used to calculate price impact
        total_volume = self.volume_for_bar + cur_volume

        volume_share = min(total_volume / volume,
                           self.volume_limit)

        price = data.current(order.asset, "close")

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

        return (
            impacted_price,
            math.copysign(cur_volume, order.direction)
        )
