.. _howto:

======================
如何运行
======================

运行方式
=========

目前运行方式下面几种:

#. 执行脚本命令, 通过 ``zipline run --help`` 可以查看帮助选项, 下面是一个例子:

    .. code-block:: bash

        $ zipline run -f zipline/examples/buyashare.py --start 2016-1-1 --end 2018-1-1 -b mydb --no-benchmark

   其中 ``zipline/examples/buyashare.py`` 是仿照 ``buyapple.py`` 编写的策略代码,

    .. code-block:: python

        from zipline.api import order, record, symbol
        from zipline.finance import commission, slippage


        def initialize(context):
            context.asset = symbol('000001.SZ')

            # Explicitly set the commission/slippage to the "old" value until we can
            # rebuild example data.
            # github.com/quantopian/zipline/blob/master/tests/resources/
            # rebuild_example_data#L105
            context.set_commission(commission.PerShare(cost=.0075, min_trade_cost=1.0))
            context.set_slippage(slippage.VolumeShareSlippage())


        def handle_data(context, data):
            order(context.asset, 10)
            record(AAPL=data.current(context.asset, 'price'))


        # Note: this function can be removed if running
        # this algorithm on quantopian.com
        def analyze(context=None, results=None):
            import matplotlib.pyplot as plt
            # Plot the portfolio and asset data.
            ax1 = plt.subplot(211)
            results.portfolio_value.plot(ax=ax1)
            ax1.set_ylabel('Portfolio value (USD)')
            ax2 = plt.subplot(212, sharex=ax1)
            results.AAPL.plot(ax=ax2)
            ax2.set_ylabel('AAPL price (USD)')

            # Show the plot.
            plt.gcf().set_size_inches(18, 8)
            plt.show()


        def _test_args():
            """Extra arguments to use when zipline's automated tests run this example.
            """
            import pandas as pd

            return {
                'start': pd.Timestamp('2014-01-01', tz='utc'),
                'end': pd.Timestamp('2014-11-01', tz='utc'),
            }

#. ``notebook`` 中使用