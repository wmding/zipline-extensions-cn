==================
A股本地化修改过程
==================

.. contents::
   :depth: 2
   :local:
   :backlinks: none

开发安装
=========

目前最新的 *zipline* 版本是 1.3.0, 通过 `pip/conda` 安装的就是这个版本.
但是, 在 *github* 上对最新版本的更新内容已经很多, 因此我们计划根据 *github* 最新开源的
代码进行继续开发.
开发环境搭建步骤分为以下几个部分:

#. 下载 *github* 代码, 可以用命令行 ``git clone``, 也可以直接下载压缩包, 然后解压缩.
   后者速度快一些.
#. 直接执行安装脚本 ``etc/dev_install``. 该脚本首先根据 ``requirements*`` 安装依赖的包, 最后
   执行 ``pip install .`` 安装 ``zipline``. 对于依赖包安装时有可能会出错, 主要原因是版本的
   问题, 需要手动进行解决. 目前遇到过的问题包括:

    #. ``bcolz`` 版本 1.12.1 安装总是编译失败, 改回旧版本 0.21.1 后没问题.
    #. ``sphinx`` 相关的包没有安装



交易日历
=========

在最新版本的 *trading_calendar* 包中有定义A股日历的方法, 调用参数为 ``XSHG``.

.. code-block:: python

    from trading_calendars import get_calendar
    trading_calendar = get_calendar('XSHG')


该日历获取方法目前发现两个问题:

#. 日线日历是通过手动排除假期的方法创建的, 最近因新冠疫情的原因导致的非正常假期, 没有得到及时更新.
#. 分钟日历序列中没有排除午休时间, 在开源项目 `rainx <https://github.com/rainx/cn_stock_holidays>`_ 中
   中有更详细的A股日历的构建方法, 以后可以参考.

值得注意的是在算法模拟生成时钟时, 会设置一些固定时间,
比如在algorithm.py文件的514行处:

.. code-block:: python

    before_trading_start_minutes = days_at_time(
        self.sim_params.sessions,
        time(8, 45),
        "Asia/Shanghai"
    )

原来的默认时区为 ``US/Eastern``, 会对 ``before_trading`` 产生影响.

基准数据加载
=================

最初的基准数据是直接通过 ``load_market_data`` 方法实现的, 我们曾修改了该方法中的数据获取方法.
根据最新的 *github* 代码, 基准获取方法做出了改变. 增加了一个基准类 ``BenchmarkSpec``.

- 通过 *CLI* 指定基准代码/ID/文件/不用基准判断.
- 在 :func:`~zipline.run_algorithm` 的输入参数中, 传入基准数据.
  默认代码传入基准数据是必须的, 可以略作修改.

.. code-block:: python

    if benchmark_returns is not None:
        benchmark_spec = BenchmarkSpec.from_returns(benchmark_returns)
    else:
        benchmark_spec = BenchmarkSpec(None, None, None, None, True)


自定义bundle
=============


仿照转换 *quandl* 数据的过程, 我们创建了连接本地搭建的 *MySQL* 数据库的模块 :func:`~zipline.data.bundles.mydb.mydb_bundle`.
通过命令行就可以实现对数据的转换

.. code-block:: bash

    $ zipline ingest -b mydb

调用该模块时对相关的 `Writer` 做了修改.
对该模块的注册是在 ``~/.zipline/extension.py`` 中完成:

.. code-block:: python

    #
    from zipline.data.bundles import register
    #
    from zipline.data.bundles.mydb import mydb_bundle

    register(
        'mydb',
        mydb_bundle,
        calendar_name='XSHG'
    )

在利用该模块产生 *bundle* 过程中, 我们做了下面的修改.

开始调试
------------

调试过程是利用 *pycharm* 设置断点进行的, 运行代码为:

.. code-block:: python

    from zipline.data import bundles as bundles_module
    import os
    import pandas as pd
    from zipline.utils.run_algo import load_extensions


    def ingest(bundle, assets_version, show_progress):
        """Ingest the data for the given bundle.
        """
        bundles_module.ingest(
            bundle,
            os.environ,
            pd.Timestamp.utcnow(),
            assets_version,
            show_progress,
        )
    load_extensions(True, (), True, os.environ)

    ingest(bundle="mydb",
           assets_version=[7],
           show_progress=True)

其中, :func:`~zipline.data.bundles.ingest` 函数需要作修改,
添加财务数据的 ``writer``, 该内容在后面会详细记录.

公司元数据
------------
如果传入的数据足够规范, *zipline* 内部不需要进行修改,
规范的公司元数据包括:

- 公司相关数据, 包括: 公司股票代码, 数据的起止时间, 自动截至时间(数据结束时间加一天).
- 公司所在交易所信息, 包括:交易所全称, 交易所简称, 国家代码(ISO 3166 alpha-2).

这些数据的读取和转换详见 :func:`~zipline.assets.AssetDBWriter.write`.

日线行情数据
--------------
日线数据的格式在 *zipline* 内部也是固定的, 默认字段为 *OHLCV* 以及公司代码和日期.
对于A股, 为了方便判断, 我们在日线数据里加入了涨跌停价格. 这样一来, 需要对
:class:`~zipline.data.bcolz_daily_bars.BcolzDailyBarWriter` 做一点修改,
在固定列名中加入新添加的字段.

.. code-block:: python

    OHLC = frozenset(['open', 'high', 'low', 'close', 'up_limit', 'down_limit'])
    US_EQUITY_PRICING_BCOLZ_COLUMNS = (
        'open', 'high', 'low', 'close', 'up_limit', 'down_limit', 'volume', 'day', 'id'
    )

分红数据
--------
分红数据是通过 :class:`~zipline.data.adjustments.SQLiteAdjustmentWriter`
进行转换的, 可以转换的数据从其方法 :func:`~zipline.data.adjustments.SQLiteAdjustmentWriter.write`
可以看出, 包括:

- splits: 送股数据
- dividend: 分红数据
- mergers: 合并数据

对于A股数据, 我们只用到前两种分红复权数据, 配股数据通过转换叠加到了分红数据上.

财务数据
----------

财务数据的处理过程, 在原始的 *zipline* 中是不存在的, 我们尝试了很多方式,
最终决定参照 :class:`~zipline.data.adjustments.SQLiteAdjustmentWriter` 的写法,
编写 :class:`~zipline.data.fundamentals.SQLiteFundamentalsWriter`.
这样做的原因主要是为了方便 *pipeline* 处理.
网上相关开源资源有:

1. `kanghua309 <https://zhuanlan.zhihu.com/p/29850946>`_ :
    根据 *pipeline* 中的 ``CustomFactor`` 类构建新的 *Factor*,
    在对这个新的因子定义 ``compute`` 方法时引入 *tushare* 下载的财务数据.
    这种方式思路很简洁, 但是使用起来也许不方便.

#. `bartosh/zipline <https://github.com/bartosh/zipline/commits/fundamentals>`_:
    从csv导入数据, 数据只有三列, ``sid/date/value``.

我们采取了第二种方案, 目前有的因子为

- ipo_date
- delist_date
- ROEAVE3
- total_share_0QE

为处理财务数据, 需要对 :func:`~zipline.data.bundles.ingest` 做修改,
添加:

.. code-block:: python

    fundamentals_db_writer = stack.enter_context(
        SQLiteFundamentalsWriter(
            wd.getpath(*fundamentals_db_relative(
                name, timestr, environ=environ)),
            overwrite=True,
        )
    )

其中路径函数定义在外面:

.. code-block:: python

    def fundamentals_db_relative(bundle_name, timestr, environ=None):
        return bundle_name, timestr, 'fundamentals.sqlite'

另外, ``bundle.ingest`` 需要添加参数 ``fundamentals_db_writer``.
在 :func:`zipline.data.bundles.load` 中需要添加
:class:`~zipline.data.fundamentals.SQLiteFundamentalsReader` 的入口,
同时对命名元组 ``BundleData`` 重新定义:

.. code-block:: python

    BundleData = namedtuple(
        'BundleData',
        'asset_finder equity_minute_bar_reader equity_daily_bar_reader '
        'adjustment_reader fundamental_reader',
    )


数据读取
=========

数据读取通过 :func:`zipline.data.bundles.load` 加载返回 ``BundleData``, 加载过程为:

>>> from zipline.data import bundles
>>> import os
>>> from zipline.utils.run_algo import load_extensions
>>> load_extensions(True, (), True, os.environ)
>>> bundle_data = bundles.load('mydb')
>>> bundle_data
BundleData(asset_finder=<zipline.assets.assets.AssetFinder object at 0x7f12d44f5be0>, equity_minute_bar_reader=<zipline.data.minute_bars.BcolzMinuteBarReader object at 0x7f12a0f8dc18>, equity_daily_bar_reader=<zipline.data.bcolz_daily_bars.BcolzDailyBarReader object at 0x7f12a3361048>, adjustment_reader=<zipline.data.adjustments.SQLiteAdjustmentReader object at 0x7f12d4fc1898>, fundamental_reader=<zipline.data.fundamentals.SQLiteFundamentalsReader object at 0x7f12d4fc1470>)

公司元数据利用 :class:`~zipline.assets.AssetFinder` 获取,
比如获取公司证券代码:

>>> bundle_data.asset_finder.lookup_symbol('000001.SZ', None)
Equity(0 [000001.SZ])
>>> bundle_data.asset_finder.lookup_symbols(['000001.SZ',], None)
[Equity(0 [000001.SZ])]

获取交易所信息:

>>> bundle_data.asset_finder.exchange_info
{'mydatabase': ExchangeInfo('mydatabase', 'mydb', 'CN')}

日线行情数据利用 :class:`~zipline.data.bcolz_daily_bars.BcolzDailyBarReader` 获取,
比如利用 :func:`~zipline.data.bcolz_daily_bars.BcolzDailyBarReader.get_value`
获取某日的收盘价:

>>> bundle_data.equity_daily_bar_reader.get_value(0, '2020-06-01', 'close')
13.32

利用 :func:`~zipline.data.bcolz_daily_bars.BcolzDailyBarReader.load_raw_arrays`
获取原始价格序列:

>>> bundle_data.equity_daily_bar_reader.load_raw_arrays(['close'], '2004-04-08', '2020-06-01', [0])
[array([[ 10.39],
        [ 10.24],
        [ 10.28],
        ...,
        [ 13.07],
        [ 13.  ],
        [ 13.32]])]

分红复权数据利用 :class:`~zipline.data.adjustments.SQLiteAdjustmentReader` 获取,
比如利用 :func:`~zipline.data.adjustments.SQLiteAdjustmentReader.get_adjustments_for_sid`
获取分红数据:

>>> bundle_data.adjustment_reader.get_adjustments_for_sid('splits', 0)
[[Timestamp('1991-05-02 00:00:00+0000', tz='UTC'), 0.7142857142857143],
 [Timestamp('1992-03-23 00:00:00+0000', tz='UTC'), 0.6666666666666666],
 [Timestamp('1993-05-24 00:00:00+0000', tz='UTC'), 0.5405405405405405],
 [Timestamp('1994-07-11 00:00:00+0000', tz='UTC'), 0.6666666666666666],
 [Timestamp('1995-09-25 00:00:00+0000', tz='UTC'), 0.8333333333333334],
 [Timestamp('1996-05-27 00:00:00+0000', tz='UTC'), 0.5],
 [Timestamp('1997-08-25 00:00:00+0000', tz='UTC'), 0.6666666666666666],
 [Timestamp('2007-06-20 00:00:00+0000', tz='UTC'), 0.9090909090909091],
 [Timestamp('2008-10-31 00:00:00+0000', tz='UTC'), 0.7692307692307692],
 [Timestamp('2013-06-20 00:00:00+0000', tz='UTC'), 0.625],
 [Timestamp('2014-06-12 00:00:00+0000', tz='UTC'), 0.8333333333333334],
 [Timestamp('2015-04-13 00:00:00+0000', tz='UTC'), 0.8333333333333334],
 [Timestamp('2016-06-16 00:00:00+0000', tz='UTC'), 0.8333333333333334]]

利用 :func:`~zipline.data.adjustments.SQLiteAdjustmentReader.load_pricing_adjustments`
获取总的分红复权数据时, 返回总为空, 需要进一步研究原因.

对于财务因子数据是通过 :class:`~zipline.data.fundamentals.SQLiteFundamentalsReader`
获取, 比如通过 :func:`~zipline.data.fundamentals.SQLiteFundamentalsReader.read`
获取某个因子的数据:

>>> dates = pd.date_range('2012-01-01', '2012-02-22', freq='10D', tz='UTC')
>>> bundle_data.fundamental_reader.read('ROEAVE3', dates, [0])
                                  0
2012-01-01 00:00:00+00:00  0.153958
2012-01-11 00:00:00+00:00  0.153958
2012-01-21 00:00:00+00:00  0.153958
2012-01-31 00:00:00+00:00  0.153958
2012-02-10 00:00:00+00:00  0.153958
2012-02-20 00:00:00+00:00  0.153958

*pipeline* 读取
------------------

*zipline* 通过 :class:`~zipline.pipeline.Pipeline` 进行横向数据的计算， 加载方式是通过
:mod:`~zipline.pipeline.loaders.equity_pricing_loader` 进行加载。
下面简单描述 *pipeline* 处理数据的过程：

首先加载 *bundle_data* 与日历

.. code-block:: python

    from zipline.data import bundles
    import os
    import pandas as pd
    from zipline.utils.run_algo import load_extensions
    from trading_calendars import get_calendar
    load_extensions(True, (), True, os.environ)
    bundle_data = bundles.load('mydb')
    trading_calendar = get_calendar('XSHG')

初始化 :class:`~zipline.pipeline.engine.SimplePipelineEngine`, 此时需要分别根据 *USEquityPricingLoader*
与 *USEquityPricing*, 分别添加 *CNEquityPricingLoader* 与 *CNEquityPricing*.

.. code-block:: python

    from zipline.pipeline.loaders import CNEquityPricingLoader
    from zipline.pipeline.data import CNEquityPricing
    from zipline.pipeline.engine import SimplePipelineEngine
    import zipline.pipeline.domain as domain

    pipeline_loader = CNEquityPricingLoader.without_fx(
        bundle_data.equity_daily_bar_reader,
        bundle_data.adjustment_reader,
    )

    def choose_loader(column):
        if column in CNEquityPricing.columns:
            return pipeline_loader
        raise ValueError(
            "No PipelineLoader registered for column %s." % column
        )

    def default_pipeline_domain(calendar):
        """
        Get a default pipeline domain for algorithms running on ``calendar``.

        This will be used to infer a domain for pipelines that only use generic
        datasets when running in the context of a TradingAlgorithm.
        """
        return _DEFAULT_DOMAINS.get(calendar.name, domain.GENERIC)


    _DEFAULT_DOMAINS = {d.calendar_name: d for d in domain.BUILT_IN_DOMAINS}

    engine = SimplePipelineEngine(
        get_loader=choose_loader,
        asset_finder=bundle_data.asset_finder,
        default_domain=default_pipeline_domain(trading_calendar),

    )

定义 *pipeline*， 通过 *engine* 获取横截面数据

.. code-block:: python

    from zipline.pipeline import Pipeline
    from zipline.pipeline.factors import DailyReturns
    from zipline.pipeline.filters import StaticAssets
    from zipline.pipeline.domain import CN_EQUITIES

    stocks_of_interest = bundle_data.asset_finder.lookup_symbols(['000001.SZ',], None)

    universe = StaticAssets(stocks_of_interest)

    daily_returns = DailyReturns()


    pipe = Pipeline(
        columns={
            'daily_returns': daily_returns,
        },
        screen=universe,
        domain=CN_EQUITIES,
    )

    pipe_out = engine.run_pipeline(
                pipe,
                pd.Timestamp('2004-04-08', tz='utc'),
                pd.Timestamp('2004-04-21', tz='utc')
            )

最终结果为：

>>> pipe_out
                                                 daily_returns
2004-04-08 00:00:00+00:00 Equity(0 [000001.SZ])      -0.013146
2004-04-09 00:00:00+00:00 Equity(0 [000001.SZ])      -0.011418
2004-04-12 00:00:00+00:00 Equity(0 [000001.SZ])      -0.014437
2004-04-13 00:00:00+00:00 Equity(0 [000001.SZ])       0.003906
2004-04-14 00:00:00+00:00 Equity(0 [000001.SZ])      -0.036965
2004-04-15 00:00:00+00:00 Equity(0 [000001.SZ])      -0.028283
2004-04-16 00:00:00+00:00 Equity(0 [000001.SZ])       0.017672
2004-04-19 00:00:00+00:00 Equity(0 [000001.SZ])      -0.004086
2004-04-20 00:00:00+00:00 Equity(0 [000001.SZ])      -0.041026
2004-04-21 00:00:00+00:00 Equity(0 [000001.SZ])       0.003209

*pipeline* 读取财务数据的方式与上面类似, 需要额外添加 *FundamentalsLoader* 与 *CNFinancialData*。
调用时， ``choose_loader`` 函数需要更改：

.. code-block:: python

    from zipline.pipeline.loaders import FundamentalsLoader
    from zipline.pipeline.data import CNFinancialData
    from zipline.pipeline.loaders import CNEquityPricingLoader
    from zipline.pipeline.data import CNEquityPricing
    from zipline.pipeline.engine import SimplePipelineEngine
    import zipline.pipeline.domain as domain

    pipeline_loader = CNEquityPricingLoader.without_fx(
        bundle_data.equity_daily_bar_reader,
        bundle_data.adjustment_reader,
    )

    fundamentals_loader = FundamentalsLoader(
        bundle_data.fundamental_reader
    )

    def choose_loader(column):
        if column in CNEquityPricing.columns:
            return pipeline_loader
        else:
            if column in CNFinancialData.columns:
                return fundamentals_loader
        raise ValueError(
            "No PipelineLoader registered for column %s." % column
        )

    def default_pipeline_domain(calendar):
        """
        Get a default pipeline domain for algorithms running on ``calendar``.

        This will be used to infer a domain for pipelines that only use generic
        datasets when running in the context of a TradingAlgorithm.
        """
        return _DEFAULT_DOMAINS.get(calendar.name, domain.GENERIC)


    _DEFAULT_DOMAINS = {d.calendar_name: d for d in domain.BUILT_IN_DOMAINS}

    engine = SimplePipelineEngine(
        get_loader=choose_loader,
        asset_finder=bundle_data.asset_finder,
        default_domain=default_pipeline_domain(trading_calendar),

    )

    from zipline.pipeline import Pipeline
    from zipline.pipeline.filters import StaticAssets
    from zipline.pipeline.domain import CN_EQUITIES

    stocks_of_interest = bundle_data.asset_finder.lookup_symbols(['000001.SZ',], None)

    universe = StaticAssets(stocks_of_interest)

    market_value = CNFinancialData.total_share_0QE.latest * CNEquityPricing.close.latest

    pipe = Pipeline(
        columns={
            'market_value': market_value,
        },
        screen=universe,
        domain=CN_EQUITIES,
    )

    pipe_out = engine.run_pipeline(
                pipe,
                pd.Timestamp('2004-04-08', tz='utc'),
                pd.Timestamp('2004-04-21', tz='utc')
            )

输出为:

>>> pipe_out
                                                 market_value
2004-04-08 00:00:00+00:00 Equity(0 [000001.SZ])           NaN
2004-04-09 00:00:00+00:00 Equity(0 [000001.SZ])           NaN
2004-04-12 00:00:00+00:00 Equity(0 [000001.SZ])           NaN
2004-04-13 00:00:00+00:00 Equity(0 [000001.SZ])           NaN
2004-04-14 00:00:00+00:00 Equity(0 [000001.SZ])           NaN
2004-04-15 00:00:00+00:00 Equity(0 [000001.SZ])  1.871881e+10
2004-04-16 00:00:00+00:00 Equity(0 [000001.SZ])  1.904960e+10
2004-04-19 00:00:00+00:00 Equity(0 [000001.SZ])  1.897177e+10
2004-04-20 00:00:00+00:00 Equity(0 [000001.SZ])  1.819344e+10
2004-04-21 00:00:00+00:00 Equity(0 [000001.SZ])  1.825181e+10

运行过程中 :func:`zipline.pipeline.loaders.frame.load_adjusted_array` 需要做些修改。


.. code-block:: python
    from zipline.pipeline import CustomFactor

    market_value = CNFinancialData.total_share_0QE.latest * CNEquityPricing.close.latest



Research模块
================

Quantopian的 `Research Platform <https://www.quantopian.com/tutorials/getting-started>`_,
提供了一些 zipline 所不支持的有用特性，
比如直接执行 ``run_pipline`` 计算给定时序上的多因子； ``get_pricing`` 获取给定股票的
*OHLCV* 信息.

搭建过程
----------

下面把Research环境移植到本地, 参考了项目 `alphatools <https://github.com/marketneutral/alphatools>`_.

- 创建 *research package*
- 创建 *ResearchEnvironment* 类, 参数为calendar, bundle名称
- 初始化时,导入bundle, 并读取bundle, 设置pipeline初始化

.. warning::

    在最初的代码, pipeline_loader是设置成了属性

    .. code-block:: python

        @property
        def pipeline_loader(self):
            return CNEquityPricingLoader(
                self.bundle_data.equity_daily_bar_reader,
                self.bundle_data.adjustment_reader,
            )



    这样处理在 **engine.py** 处683行处会遇到问题,
    ``pipeline_loader`` 被当做了某个字典的key值, 调用第二次时pipeline_loader的内存地址产生了变化,
    会产生KeyError. 将上述代码放到初始化函数中就没有问题了

    .. code-block:: python

        self.pipeline_loader = CNEquityPricingLoader(
            self.bundle_data.equity_daily_bar_reader,
            self.bundle_data.adjustment_reader,
        )

运行示例
--------------


>>> from zipline.research import ResearchEnvironment
>>> re = ResearchEnvironment()
>>> re.get_symbols(['000001.SZ'])
[Equity(0 [000001.SZ])]
>>> re.get_pricing('000001.SZ', '2013-02-18', '2013-02-20', 'close')
                           Equity(0 [000001.SZ])
2013-02-18 00:00:00+00:00                  20.90
2013-02-19 00:00:00+00:00                  20.81
2013-02-20 00:00:00+00:00                  20.30

*pipeline* 测试:

.. code-block:: python

    from zipline.pipeline import Pipeline
    from zipline.pipeline.factors import Returns

    def make_pipeline():

        returns = Returns(window_length=2)
        # sentiment = stocktwits.bull_minus_bear.latest
        # msg_volume = stocktwits.total_scanned_messages.latest

        return Pipeline(
            columns={
                'daily_returns': returns,
                # 'sentiment': sentiment,
                # 'msg_volume': msg_volume,
            },
        )

    re.run_pipeline(
        make_pipeline(),
        start_date='2013-02-18',
        end_date='2013-02-20',
    )

输出为::
                                                        daily_returns
    2013-02-18 00:00:00+00:00 Equity(0 [000001.SZ])         -0.004796
                              Equity(1 [000002.SZ])          0.012626
                              Equity(3 [000004.SZ])          0.016411
                              Equity(4 [000005.SZ])          0.009615
                              Equity(5 [000006.SZ])          0.003565
                              Equity(6 [000007.SZ])          0.075339
                              Equity(7 [000008.SZ])          0.034146
                              Equity(8 [000009.SZ])         -0.003151
                              Equity(9 [000010.SZ])          0.000000
                              Equity(10 [000011.SZ])         0.008253
                              Equity(11 [000012.SZ])        -0.001174
                              Equity(13 [000014.SZ])         0.011482
                              Equity(15 [000016.SZ])         0.008523
                              Equity(16 [000017.SZ])         0.000000
                              Equity(17 [000018.SZ])        -0.002621
                              Equity(18 [000019.SZ])         0.008444
                              Equity(19 [000020.SZ])         0.007599
                              Equity(20 [000021.SZ])         0.006397
                              Equity(21 [000023.SZ])         0.005935
                              Equity(22 [000024.SZ])         0.001838
                              Equity(23 [000025.SZ])         0.003003
                              Equity(24 [000026.SZ])         0.009162
                              Equity(25 [000027.SZ])         0.001610
                              Equity(26 [000028.SZ])         0.028605
                              Equity(27 [000029.SZ])         0.000000
                              Equity(28 [000030.SZ])        -0.020925
                              Equity(29 [000031.SZ])         0.000000
                              Equity(30 [000032.SZ])         0.009535
                              Equity(31 [000033.SZ])         0.013216
                              Equity(32 [000034.SZ])         0.004739
                                                               ...
    2013-02-20 00:00:00+00:00 Equity(3294 [601908.SH])      -0.030612
                              Equity(3296 [601918.SH])      -0.046533
                              Equity(3297 [601919.SH])      -0.006961
                              Equity(3298 [601928.SH])      -0.041667
                              Equity(3299 [601929.SH])      -0.031039
                              Equity(3300 [601933.SH])      -0.006420
                              Equity(3301 [601939.SH])      -0.008197
                              Equity(3304 [601958.SH])      -0.029711
                              Equity(3305 [601965.SH])      -0.038803
                              Equity(3311 [601988.SH])      -0.009740
                              Equity(3312 [601989.SH])      -0.029685
                              Equity(3314 [601991.SH])      -0.016317
                              Equity(3315 [601992.SH])      -0.072165
                              Equity(3316 [601996.SH])       0.029372
                              Equity(3318 [601998.SH])      -0.014344
                              Equity(3319 [601999.SH])      -0.024353
                              Equity(3320 [603000.SH])      -0.027257
                              Equity(3321 [603001.SH])      -0.025581
                              Equity(3322 [603002.SH])      -0.007084
                              Equity(3323 [603003.SH])       0.035775
                              Equity(3327 [603008.SH])      -0.025665
                              Equity(3374 [603077.SH])      -0.024520
                              Equity(3404 [603123.SH])      -0.021566
                              Equity(3407 [603128.SH])      -0.025118
                              Equity(3422 [603167.SH])      -0.019567
                              Equity(3505 [603333.SH])       0.005445
                              Equity(3522 [603366.SH])      -0.030954
                              Equity(3540 [603399.SH])      -0.038658
                              Equity(3688 [603766.SH])      -0.032573
                              Equity(3811 [603993.SH])      -0.031665
    [7413 rows x 1 columns]

选择某支股票:

>>> data_output.xs(re.get_symbols('000001.SZ')[0], level=1)
                           daily_returns
2013-02-18 00:00:00+00:00      -0.004796
2013-02-19 00:00:00+00:00       0.007229
2013-02-20 00:00:00+00:00      -0.004306