"""
A simple Pipeline algorithm that longs the top 3 stocks by RSI and shorts
the bottom 3 each day.
"""
from six import viewkeys
from zipline.api import (
    attach_pipeline,
    date_rules,
    order_target_percent,
    pipeline_output,
    record,
    schedule_function,
    order,
)
from zipline.finance import commission
from zipline_extensions_cn.finance.slippage import VolumeShareSlippage
from zipline.pipeline import Pipeline
from zipline.pipeline.factors import RSI


def make_pipeline():
    rsi = RSI()
    return Pipeline(
        columns={
            'longs': rsi.top(1),
            'shorts': rsi.bottom(1),
        },
    )


def rebalance(context, data):
    # Pipeline data will be a dataframe with boolean columns named 'longs' and
    # 'shorts'.
    pipeline_data = context.pipeline_data
    all_assets = pipeline_data.index

    longs = all_assets[pipeline_data.longs]
    shorts = all_assets[pipeline_data.shorts]

    record(universe_size=len(all_assets))

    # Build a 2x-leveraged, equal-weight, long-short portfolio.
    one_third = 1.0 / 3.0
    for asset in longs:
        # order_target_percent(asset, one_third)
        order(asset, 100)
    # for asset in shorts:
    #     # order_target_percent(asset, -one_third)
    #     order(asset, -100)

    # Remove any assets that should no longer be in our portfolio.
    portfolio_assets = longs | shorts
    positions = context.portfolio.positions
    for asset in viewkeys(positions) - set(portfolio_assets):
        # This will fail if the asset was removed from our portfolio because it
        # was delisted.
        if data.can_trade(asset):
            order_target_percent(asset, 0)


def initialize(context):
    attach_pipeline(make_pipeline(), 'my_pipeline')

    # Rebalance each day.  In daily mode, this is equivalent to putting
    # `rebalance` in our handle_data, but in minute mode, it's equivalent to
    # running at the start of the day each day.
    schedule_function(rebalance, date_rules.every_day())

    # Explicitly set the commission/slippage to the "old" value until we can
    # rebuild example data.
    # github.com/quantopian/zipline/blob/master/tests/resources/
    # rebuild_example_data#L105
    context.set_commission(commission.PerShare(cost=.0075, min_trade_cost=1.0))
    context.set_slippage(VolumeShareSlippage())


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
    end = pd.Timestamp('2019-8-25', tz='utc')
    run_algorithm(
        start=start,
        end=end,
        initialize=initialize,
        before_trading_start=before_trading_start,
        analyze=analyze,
    )