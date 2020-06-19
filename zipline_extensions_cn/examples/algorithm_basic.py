#!/usr/bin/env python
#
# Copyright 2014 Quantopian, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from zipline.api import order, record, symbol
from zipline.finance import commission, slippage

from zipline.api import (
    attach_pipeline,
    date_rules,
    time_rules,
    order_target,
    pipeline_output,
    record,
    schedule_function,
    get_open_orders,
)
from logbook import Logger

log = Logger(__name__)


def initialize(context):
    context.asset = symbol('000001.SZ')

    # Explicitly set the commission/slippage to the "old" value until we can
    # rebuild example data.
    # github.com/quantopian/zipline/blob/master/tests/resources/
    # rebuild_example_data#L105
    context.set_commission(commission.PerShare(cost=.0075, min_trade_cost=1.0))
    context.set_slippage(slippage.VolumeShareSlippage())

    schedule_function(
        my_func,
        date_rules.every_day(),
        time_rules.market_open(minutes=15)
    )


def my_func(context, data):
    # Order 100 shares of AAPL.
    order_target(context.asset, 100)

    # Retrieve all open orders.
    open_orders = get_open_orders()

    # If there are any open orders.
    if open_orders:
        print(open_orders)
        # open_orders is a dictionary keyed by sid, with values that are lists of orders. Iterate over the dictionary
        for security, orders in open_orders.items():
            # Iterate over the orders and log the total open amount
            # for each order.
            for oo in orders:
                message = 'Open order for {amount} shares in {stock}'
                message = message.format(amount=oo.amount, stock=security)
                log.info(message)

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
        'start': pd.Timestamp('2020-01-01', tz='utc'),
        'end': pd.Timestamp('2020-06-01', tz='utc'),
    }


if __name__ == '__main__':
    from trading_calendars import get_calendar

    from pathlib import Path

    print('Running' if __name__ == '__main__' else 'Importing', Path(__file__).resolve())

    from zipline_extensions_cn.utils.run_algo import run_algorithm

    import pandas as pd

    calendar = get_calendar("XSHG")
    start = pd.Timestamp('2020-01-01', tz='utc')
    end = pd.Timestamp('2020-06-01', tz='utc')
    run_algorithm(
        start=start,
        end=end,
        initialize=initialize,
        capital_base= 1000000,
        analyze=analyze,
        bundle='mydb',
        trading_calendar=calendar,
    )
