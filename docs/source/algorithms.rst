=========
策略算法
=========

*策略算法* 指的是利用 :ref:`algo_api` 中的接口函数构建的策略代码,
主要目的是模拟真实的交易环境进行历史数据回测. 与 *pipeline* 相比,
*策略算法* 更倾向于定义订单逻辑以及投资组合构建, 是时间线上的纵向分析;
*pipeline* 更倾向于获取数据然后构建 *因子*, 是时间线上的横向/横截面分析.
在 *策略算法* 中可以通过 ``attach_pipline`` 调用 *pipeline* 构造的因子,
然后进行下单或投资组合构建.

基本结构
------------

从代码结构上看, 基本函数一般为:

.. code-block:: python

    from zipline.api import order, record, symbol

    def initialize(context)
        pass

    def handle_data(context, data):
        order(symbol('AAPL'), 10)
        record(AAPL=data.current(symbol('AAPL'), 'price'))

    def before_trading_start(context, data):
        pass

    def analyze(context, perf):
        pass

其中:

- `initialize` 函数为初始函数, 必须存在的函数. 该函数只在策略算法开始时运行一次,
  一般包括初始状态设置(比如全局变量, 滑点模型, 佣金模型等), 获取 *pipeline*, 运行 *scheduling* 函数等.
- `context` 是 *AlgorithmContext* 对象组成的字典, 用来在 `intialize`, `handle_data`, `before_trading_start`
  以及各种 `schedule_function` 函数中传递数据.
- `data` 参数是 ``BarData``.
- `handle_data` 按照交易频率运行, 是策略内容的核心. 对于分钟线策略, 每分钟运行会导致算法运算速度慢, 所以通常会用 `schedule_function`
  替代, 该函数和 `schedule_function` 两者必须存在一种.
- `before_trading_start` 是在每日开盘前运行一次的函数, 通常用来处理因 *pipeline* 数据
  带来的每日计算. 运行分钟线策略时, 计算 *pipeline* 数据会导致速度变慢, 因此可以把日线数据生成的 *pipeline* 的进一步计算放在该函数中.
- `analyze` 是分析 *策略算法* 结果的函数


从内容上看, *策略算法* 一般分以下几个部分:

#. :ref:`策略初始化设置 <algo_initial>`.
#. :ref:`algo_data_using`
#. :ref:`基于行情数据的运算, 对投资组合通过买/卖作出调整.<algo_rebalance>`
#. 信息输出与作图.

.. _algo_initial:

策略初始化
------------

策略算法的初始化一般包括:

- 全局变量设置: 利用 `context` 传递变量
- :ref:`注册pipeline <algo_initial_pipeline>`
- :ref:`调用schedule_function <algo_intial_schedule>`
- :ref:`algo_initial_commission`

.. _algo_initial_pipeline:

attach pipline
````````````````

在 *策略算法* 中利用 ``attach_pipline`` 对 *pipeline* 进行注册.

.. code-block:: python

    from zipline.algorithm import attach_pipeline, pipeline_output
    from zipline.pipeline import Pipeline

    def make_pipeline():
        # Instantiates an empty Pipeline.
        return Pipeline()

    def initialize(context):
        # Creates a reference to the empty Pipeline.
        pipe = make_pipeline()
        # Registers the empty Pipeline under the name 'my_pipeline'.
        attach_pipeline(pipe, name='my_pipeline')

*pipeline* 的计算并不是每日进行, 而是按照 *chunk* 运算.
在回测开始时, *pipeline* 执行的块区间为一周, 一周的回测结束后, 重新获取预计算的 *pipeline*, 块区间变为6个月.

.. note::

    每个 *pipeline* 计算块有10分钟限制, 超过运行时间, 会通过 `PipelineTimeout` 报错,
    另外开始执行的块区间设置为一周的原因是为迅速检测回测算法会不会产生错误.

.. _algo_intial_schedule:

Schedule 功能
```````````````

利用 ``schedule_function`` 接口函数, 可以定时执行某种方法. 该函数只能在 ``initialize`` 函数中设置.
比如下面代码中, 定时函数 ``myfunc`` 在每日开盘后1分钟执行.


.. code-block:: python

    import quantopian.algorithm as algo

    def initialize(context):
        algo.schedule_function(
            func=myfunc,
            date_rule=algo.date_rules.every_day(),
            time_rule=algo.time_rules.market_open(minutes=1),
            calendar=algo.calendars.US_EQUITIES
        )

如果有多个定时器设置的时间相同, 会按照定义的先后执行, 也就是说不是异步执行.
另外定时函数的参数必须为: `context` 和 `data`.

.. note::

    定时函数与 ``handle_data`` 函数共同拥有50秒限制, 意思是如果两者同一分钟开始运行, 它们运行时间之和不能超过50秒,
    否则会通过 ``TimeoutException`` 报错.

.. _algo_initial_commission:

滑点和佣金模型
```````````````

为了真实模拟交易过程, 交易成本是必须考虑的. 在 *zipline* 中交易成本包括滑点和佣金.

滑点的影响通过设置滑点模型进行计算, 在初始化函数中可以通过 `set_slippage` 进行设置.
*zipline* 中内置的滑点模型包括:

- FixedBasisPointsSlippage (default)
- VolumeShareSlippage
- FixedSlippage

.. code-block:: python

        context.set_slippage(slippage.VolumeShareSlippage())

佣金的计算通过分为 `PerShare` 和 `PerTrade`, 与滑点类似, 可以在初始化函数中设置:

.. code-block:: python

    context.set_commission(commission.PerShare(cost=.0075, min_trade_cost=1.0))


.. _algo_data_using:

数据调用
--------------

在 *策略算法* 中调用数据的方式有两种:

#. ``BarData``
#. 通过 *pipeline* 获取每日的因子数据

pipeline 数据
```````````````
每日的 *pipeline* 数据可以通过 `pipeline_output` 获得, 如果计算量大可以在 `before_trading_start` 中进行预计算.

.. code-block:: python

    def my_scheduled_function(context, data):
        # Access results using the name passed to attach_pipeline.
        pipeline_results_today = pipeline_output('my_pipeline')

*pipeline* 的设计一般在 *Research* 模块完成, 但在 *策略算法* 中得到的 ``pd.DataFrame`` 有所不同.
在 *Research* 模块中 *pipeline* 数据为双重索引(日期和证券代码), 在 *策略算法* 中的数据索引为单索引(证券代码).

BarData
``````````
`BarData` 是用来调用行情数据的类.
一般来说, 调用数据最好在 *pipeline* 中完成, 因为它运行比较快, 但如果想调用分钟行情就只能用 `BarData` 的方式.
利用 `BarData` 的各种方法, 可以实现下面几个需求:

#. 调用当前分钟的行情数据(开高低收成交量)
#. 获取历史行情数据
#. 检查最新报价行情数据


.. _algo_rebalance:

构建投资组合
------------
*策略算法* 的核心是为了设计一个投资组合, 使得该组合在每个时点上都是 *最好* 的.
从过程上看, 实际就是设计定时器的定时函数, 参数应为: `context` 和 `data`.
对投资组合的调整一般先是查看当前组合, 然后执行下单操作.

投资组合
`````````
每个 *策略算法* 都会有一个投资组合, 利用 `Portfolio` 类进行描述, 可以通过 ``context.portfolio`` 调用.
 `Portfolio` 有很多属性, 比如 `context.portfolio.positions` 查看当前持有的仓位,
`context.portfolio.cash` 查看当前投资组合的现金.

下单
`````
在 :ref:`algo_api` 接口中有众多的手动下单的方法, 比较常用的是 `order_target_percent()`, 值得注意的是:

- 如果 `open_orders` 队列的订单当天没有完成, 会被取消.
- 默认的可以利用的资金是没有限制的, 可能产生负现金的情况. 因此最好在算法中利用 ``context.portfolio`` 进行提前判断.


常见问题
`````````

- 证券的交易状态. *pipeline* 包含的证券需要确保都是可以交易的, 如果是手动定义证券名称, 需要利用 ``can_trade`` 判断交易状态.
- 过期价格. 可以通过 ``is_stale`` 判断价格是否是最近一分钟的价格.
- 未完成订单. 如果订单当天未完成, 会被取消.

日志与画图
-----------

