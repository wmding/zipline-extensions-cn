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

    # Import pipeline built-ins.
    from zipline.pipeline import Pipeline
    from zipline.pipeline.factors import SimpleMovingAverage

    # Import datasets.
    from zipline.pipeline.data import EquityPricing


    # Define factors.
    sma_10 = SimpleMovingAverage(inputs=[EquityPricing.close], window_length=10)
    sma_30 = SimpleMovingAverage(inputs=[EquityPricing.close], window_length=30)

    # Define a filter.
    prices_over_5 = (sma_10 > 5)

    # Instantiate pipeline with two columns corresponding to our two factors, and a
    # screen that filters the result down to assets where sma_10 > $5.
    pipe = Pipeline(
        columns={
            'sma_10': sma_10,
            'sma_30': sma_30,
        },
        screen=prices_over_5
    )

