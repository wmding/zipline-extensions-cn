=============
pyfolio
=============

*pyfolio* 是对 *zipline* 算法回测后的结果进行指标分析的工具, 它的核心是输出一个 *tear sheet*,
概括交易策略在某个时间段的表现.

首先, 从回测结果中分离出 *收益*, *仓位*, *交易* 数据:

>>> import pyfolio as pf
>>> returns, positions, transactions = pf.utils.extract_rets_pos_txn_from_zipline(perf)

根据这些数据可以得到一个简单的 *tear sheet*.

>>> pf.create_simple_tear_sheet(returns, positions, transactions,)

也可以看详细的 *tear sheet*:

>>> py.create_full_tear_sheet(perf.returns)
