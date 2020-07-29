from zipline.api import order, record, symbol
from zipline.finance import commission
from zipline_extensions_cn.finance.slippage import VolumeShareSlippage
from zipline.pipeline import Pipeline
from zipline_extensions_cn.pipeline.data import CNFinancialData, CNEquityPricing
from six import viewkeys
from zipline.api import (
    attach_pipeline,
    date_rules,
    time_rules,
    order_target_percent,
    pipeline_output,
    record,
    schedule_function,
    get_open_orders,
)
from logbook import Logger

log = Logger(__name__)


def make_pipeline():
    filter1 = CNEquityPricing.volume.latest > 4000
    # filter2 = CNEquityPricing.high.latest < CNEquityPricing.up_limit.latest/1000
    # filter3 = CNEquityPricing.high.latest > CNEquityPricing.down_limit.latest/1000

    market_cap = CNEquityPricing.close.latest * CNFinancialData.total_share_0QE.latest
    universe = filter1 & market_cap.notnull()

    maket_cap_1 = market_cap.deciles(mask=universe).eq(0)

    market_cap_top5 = market_cap.bottom(5, mask=maket_cap_1)

    # market_cap_1_top = market_cap.top(5, mask=maket_cap_1)
    pipe = Pipeline()
    pipe.add(market_cap, 'market_cap')
    pipe.set_screen(market_cap_top5)

    return pipe


def rebalance(context, data):
    # Pipeline data will be a dataframe with boolean columns named 'longs' and
    # 'shorts'.
    pipeline_data = context.pipeline_data
    all_assets = pipeline_data.index

    record(universe_size=len(all_assets))

    # Build a 2x-leveraged, equal-weight, long-short portfolio.
    one_third = 1.0 / len(all_assets)
    for asset in all_assets:
        order_target_percent(asset, one_third)

    # Remove any assets that should no longer be in our portfolio.
    positions = context.portfolio.positions
    for asset in viewkeys(positions) - set(all_assets):
        # This will fail if the asset was removed from our portfolio because it
        # was delisted.
        if data.can_trade(asset):
            order_target_percent(asset, 0)


def initialize(context):
    attach_pipeline(make_pipeline(), 'my_pipeline')

    # Explicitly set the commission/slippage to the "old" value until we can
    # rebuild example data.
    # github.com/quantopian/zipline/blob/master/tests/resources/
    # rebuild_example_data#L105
    context.set_commission(commission.PerShare(cost=.0075, min_trade_cost=1.0))
    context.set_slippage(VolumeShareSlippage())

    schedule_function(rebalance, date_rules.every_day())


def before_trading_start(context, data):
    context.pipeline_data = pipeline_output('my_pipeline')


def analyze(context=None, results=None):
    import matplotlib.pyplot as plt
    # Plot the portfolio and asset data.
    results.portfolio_value.plot()

    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()


if __name__ == '__main__':
    from zipline_extensions_cn.utils.run_algo import run_algorithm

    import pandas as pd

    start = pd.Timestamp('2019-7-15', tz='utc')
    end = pd.Timestamp('2019-7-25', tz='utc')
    run_algorithm(
        start=start,
        end=end,
        initialize=initialize,
        analyze=analyze,
        before_trading_start=before_trading_start,
    )
