============
pipeline
============

*pipeline* 的中文翻译为 *管道*, 与 *tube* 是近义词, 通常用来描述传输流体的管道.
这个名字起的很形象, 只不过在 *zipline* 中, 传输的不是普通的流体, 而是数据流.
在 *zipline* 的 *pipeline* 模块中, 输入端为某个时点的历史数据, 也称为横截面数据,
输出端得到的就是该时间点我们想要的数据. 因此 *pipeline* 的实际作用可以理解为数据流清洗以及数据流再加工.

基本用法
=========

*pipeline* 的定义一般分三个部分:

#. 传入数据
#. 定义计算规则
#. 实例化 *Pipeline*

下面是一个简单的 *pipeline* 的定义:

.. code-block:: python

    from zipline_extensions_cn.research import *

    start_date = '2019-03-06'
    end_date = '2020-03-19'

    from zipline.pipeline import Pipeline
    from zipline_extensions_cn.pipeline.data import CNFinancialData, CNEquityPricing

    close = CNEquityPricing.close.latest
    roeavg3 = CNFinancialData.total_share_0QE.latest

    pipe = Pipeline(
        columns={
            'close': close,
                        'roeavg3':roeavg3
       },
    )

    out = run_pipeline(pipe, start_date, end_date)

数据
======

*pipeline* 中所用的数据与 *BarData* 不同, 首先通过列名定义出数据, 然后利用加载类进行加载.
数据类型是通过 ``DataSet`` 类进行定义, 比如:

.. code-block:: python

    class FundamentalsDataSet(DataSet):

        """
        :class:`~zipline.pipeline.data.DataSet` containing daily trading prices and
        volumes.
        """
        ROEAVE3 = Column(float64_dtype)
        total_share_0QE = Column(float64_dtype)
        ipo_date = Column(float64_dtype)
        delist_date = Column(float64_dtype)

其中 ``Column`` 是指 ``BoundColumns`` 类的对象, 用来动态地获取 ``DataSet`` 属性,
在 *pipeline* 中直接用到的数据实际上就是 ``Column``, 应该注意的是该类型并没有数据, 他只是指向数据.
他的基本调用方法为:

.. code-block:: python

    from zipline_extensions_cn.pipeline.data import CNFinancialData, CNEquityPricing
    close = CNEquityPricing.close

``close`` 指向了价格序列中的 ``close`` 列.
``Column`` 有不同的数据类型, 可以为 ``float64``, ``int64``, ``bool``, ``datetime64``, 以及 ``object``,
不同的类型决定了运算结果的类型, 比如做 ``Latest`` 运算时, 会根据 ``Column`` 的数据类型, 得到结果区分为因子(Factor),
过滤器(Filter)和分类器(Classifer)


因子(Factor)
==============

在 *pipeline* 中因子是指在某个时点对 ``Column`` 进行数值计算得到的结果, 计算方法传入参数有两个:
``inputs`` 是指 ``Column`` 名称, ``window_length`` 是指回溯计算的天数.
在 *zipline* 中有一些内置因子, 比如移动均线:

.. code-block:: python

    from zipline.pipeline.factors import SimpleMovingAverage

    mean_close_10 = SimpleMovingAverage(
        inputs=[CNEquityPricing.close],
        window_length=10
    )

    pipe = Pipeline(
        columns={
            '10_day_mean_close': mean_close_10
        }
    )

另外一种在 *pipeline* 中添加因子的方法为:

>>> my_pipe = Pipeline()
>>> f1 = SomeFactor(...)
>>> my_pipe.add(f1, 'f1')

一个最常用的因子方法为 ``Latest``, 该方法的使用与常规因子不同, 它相当于 ``Column`` 的一种属性.
如开始时介绍的那样:

>>> close = CNEquityPricing.close.latest

处理后即为因子, 可以在 *pipeline* 中直接使用.

因子之间是可以直接进行计算的. 比如利用不同区间的移动均线构造一个新因子, 可以这么做:

.. code-block:: python

    mean_close_10 = SimpleMovingAverage(
        inputs=[CNEquityPricing.close],
        window_length=10
    )
    mean_close_30 = SimpleMovingAverage(
        inputs=[CNEquityPricing.close],
        window_length=30
    )

    percent_difference = (mean_close_10 - mean_close_30) / mean_close_30


过滤器(Filters)
===============

过滤器的生成通常通过因子和分类器运算后得到, 数据类型为 ``bool``.
比如移动均线的例子:

.. code-block:: python

    mean_close_10 = SimpleMovingAverage(
        inputs=[CNEquityPricing.close],
        window_length=10
    )
    mean_close_30 = SimpleMovingAverage(
        inputs=[CNEquityPricing.close],
        window_length=30
    )
    mean_crossover_filter = mean_close_10 < mean_close_30

对于因子还有很多内置方法直接生成过滤器, 比如``Factor.top(n)``,  ``Factor.percentile_between(10, 20)``等等.

>>> last_close_price = CNEquityPricing.close.latest
>>> top_close_price_filter = last_close_price.top(200)

过滤器在使用时可以作为 *pipeline* 的 ``screen`` 参数, 多个 *Filter* 可以做逻辑运算:

.. code-block:: python

    mean_close_10 = SimpleMovingAverage(
        inputs=[CNEquityPricing.close],
        window_length=10
    )

    mean_close_10_quantile = mean_close_10.percentile_between(90, 100)

    mean_close_10_high = mean_close_10 > 40

    is_tradeable = mean_close_10_quantile & mean_close_10_high

    return Pipeline(
        columns={
            'mean_close_10': mean_close_10,
        },
        screen=is_tradeable
    )

过滤器的另一种用法是作为 ``mask`` 参数对因子或者过滤器进行筛选:

.. code-block:: python

    mean_close_30 = SimpleMovingAverage(
        inputs=[CNEquityPricing.close],
        window_length=30,
        mask = CNEquityPricing.close.latest > 40
    )

    mean_close_10 = SimpleMovingAverage(
        inputs=[CNEquityPricing.close],
        window_length=10
    )

    mean_close_10_high = mean_close_10.top(10, mask = CNEquityPricing.close.latest > 40)

    pipe = Pipeline(
        columns={
            'mean_close_30': mean_close_30,
            'mean_close_10_high':mean_close_10_high
        },
        screen = mean_close_30.notnull() and mean_close_10_high,
    )


分类器(Classifer)
==================

对因子的计算如果生成的是字符串或者整数标签时, 可以当作分类器使用, 比如行业数据:

.. code-block:: python

    from zipline.pipeline import  CustomClassifier
    import numpy as np

    class Sector(CustomClassifier):
        inputs = [CNFinancialData.IndustryId]
        window_length = 1
        dtype = np.int64
        missing_value = 9999

        def compute(self, today, assets, out, IndustryId):
            out[:] = (IndustryId/1000000).astype(int)

    sector = Sector()

    pipe = Pipeline(
            columns={
                'sector': sector,
            },
            screen = sector.eq(40),
        )

这里利用了 ``CustomClassifier`` 进行重新构造分类器.
分类器有多种方法可以生成过滤器, 上面的 ``eq(40)`` 是其中一种, 可以这么做的原因是
*Factor* 的 ``quantiles`` 方法实际上返回的就是分类器的子类 ``Quantiles``.