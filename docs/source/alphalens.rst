==============
alphalens
==============

*alphalens* 是快速测试 *pipeline* 因子好坏的工具库, 它的好处在于快速, 图形化, 易理解.
它可以让我们在做真实回测之前, 对因子有一个大概的认识.

提供标准化数据
===============

*alphalens* 需要的数据包括因子数据以及价格数据, 因子数据可以通过 *pipeline* 生成,
价格数据可以通过 ``get_pricing`` 函数获得:

.. code-block:: python

    pricing_data = get_pricing(
      tickers=results.index.levels[1], # Finds all assets that appear at least once in "factor_data"
      start_date=start_date,
      end_date=end_date, # must be after run_pipeline()'s end date. Explained more in lesson 4
      field='close' # Generally, you should use open pricing. Explained more in lesson 4
    )

数据在使用前需要再加工, 加工函数为 ``alphalens.utils.get_clean_factor_and_forward_returns``,
该函数有多个默认值参数:

.. code-block:: python

    def get_clean_factor_and_forward_returns(factor,
                                             prices,
                                             groupby=None,
                                             binning_by_group=False,
                                             quantiles=5,
                                             bins=None,
                                             periods=(1, 5, 10),
                                             filter_zscore=20,
                                             groupby_labels=None,
                                             max_loss=0.35,
                                             zero_aware=False,
                                             cumulative_returns=True):


经过处理后得到的数据包含的列为:

- 未来收益, 其未来天数设置默认为(1,5,10)天.
- 因子值
- 因子值分位数, 默认为5


tear sheets
=============

*tear sheet* 大体指的是摘要意思, 类似个人的一页简历, 描述了因子的一些表现指标, 包括:

- 预测能力
- 收益情况
- 换手率情况
- 分类分析

获取总览的函数为 ``alphalens.tears.create_full_tear_sheet`` 以及 ``alphalens.tears.create_summary_tear_sheet``

预测能力
------------

因子预测能力用信息系数 *IC* 表示,  它是用来衡量因子预测好坏的系数, 公式为:

.. math::

    \begin{aligned}
        &\text{IC} = (2 \times \text{Proportion Correct}) - 1 \\
        &\textbf{其中:} \\
        &\text{Proportion Correct} = \text{预测正确的比率} \\
    \end{aligned}

预测正确的比例通过因子值与未来收益的 *Spearman Rank Correlation* 代表.

获取信息系数的函数为 ``alphalens.tears.create_information_tear_sheet``

收益情况
-----------
前面检验了因子的预测能力, 对于预测能力不错的因子, 我们想进一步检验具体的盈利能力,
可以通过 ``alphalens.tears.create_returns_tear_sheet`` 实现.
盈利的比较在不同分位, 不同时间内进行, 这里有一些概念性的问题需要注意.

- ``Mean period-wise returns`` : 指的是利用因子加权处理后的收益
- 聪明收益的单位: 表格展示的收益率值乘了10000, 并且以最小时间单位为基础收益率单位, 这么做是为了方便比较.

    .. note::

        对于同一个因子, 不同的时间区间 (1,5,10) 与 (2,5,10)进行对比发现, *10D* 时间区间
        所展示的 *wise return* 并不同. 这是因为第一种情况是以一天的收益率为单位, 第二种是以两天的收益率为单位.

- 各分位的累计收益图, 只会画 *1D* 的情况.
- *alpha-beta* 计算时, *beta* 是全市场的平均收益.
- 图标中 *top* 指的是最高分位, *bottom* 是第一分位.

换手率情况
-----------

利用 ``create_turnover_tear_sheet`` 函数可以查看每个分位在不同时间区间股票数的变化情况,
同时也可以计算每隔一个时间区间因子排名的变化情况. 原则上时间区间越长, 换手率越高, 排名的相关性越低.

分类计算
---------




