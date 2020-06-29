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
from zipline.finance import commission
from zipline_extensions_cn.finance.slippage import VolumeShareSlippage

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
    context.asset = symbol('601236.SH')

    # Explicitly set the commission/slippage to the "old" value until we can
    # rebuild example data.
    # github.com/quantopian/zipline/blob/master/tests/resources/
    # rebuild_example_data#L105
    context.set_commission(commission.PerShare(cost=.0075, min_trade_cost=1.0))
    context.set_slippage(VolumeShareSlippage())

    schedule_function(
        my_func,
        date_rules.every_day(),
        time_rules.market_open(minutes=15)
    )


def my_func(context, data):
    # Order 100 shares of AAPL.
    # order_target(context.asset, 1000)
    order(context.asset, 1000)
    # Retrieve all open orders.
    open_orders = get_open_orders()

    # If there are any open orders.
    if open_orders:
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
    ax1.set_ylabel('Portfolio value')
    ax2 = plt.subplot(212, sharex=ax1)
    results.AAPL.plot(ax=ax2)
    ax2.set_ylabel('price')

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
    )
