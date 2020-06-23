import click
import os
import sys
import warnings

try:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import TerminalFormatter

    PYGMENTS = True
except ImportError:
    PYGMENTS = False
import logbook
import pandas as pd
import six
from toolz import concatv
from trading_calendars import get_calendar

from zipline_extensions_cn.data import bundles
from zipline.data.benchmarks import get_benchmark_returns_from_file
from zipline.data.data_portal import DataPortal
from zipline.finance import metrics
from zipline.finance.trading import SimulationParameters
from zipline.pipeline.data import USEquityPricing
from zipline.pipeline.loaders import USEquityPricingLoader

import zipline.utils.paths as pth
from zipline.extensions import load
from zipline.errors import SymbolNotFound
from zipline_extensions_cn.algorithm import CNTradingAlgorithm
from zipline.finance.blotter import Blotter

log = logbook.Logger(__name__)
from zipline.utils.run_algo import BenchmarkSpec, load_extensions

log = logbook.Logger(__name__)

class _RunAlgoError(click.ClickException, ValueError):
    """Signal an error that should have a different message if invoked from
    the cli.

    Parameters
    ----------
    pyfunc_msg : str
        The message that will be shown when called as a python function.
    cmdline_msg : str, optional
        The message that will be shown on the command line. If not provided,
        this will be the same as ``pyfunc_msg`
    """
    exit_code = 1

    def __init__(self, pyfunc_msg, cmdline_msg=None):
        if cmdline_msg is None:
            cmdline_msg = pyfunc_msg

        super(_RunAlgoError, self).__init__(cmdline_msg)
        self.pyfunc_msg = pyfunc_msg

    def __str__(self):
        return self.pyfunc_msg


def _run(handle_data,
         initialize,
         before_trading_start,
         analyze,
         algofile,
         algotext,
         defines,
         data_frequency,
         capital_base,
         bundle,
         bundle_timestamp,
         start,
         end,
         output,
         trading_calendar,
         print_algo,
         metrics_set,
         local_namespace,
         environ,
         blotter,
         benchmark_spec):
    """运行交易策略算法回测

    会被 ``cli`` 和 :func:`zipline.run_algo` 调用.
    """

    bundle_data = bundles.load(
        bundle,
        environ,
        bundle_timestamp,
    )

    if trading_calendar is None:
        trading_calendar = get_calendar('XSHG')

    # date parameter validation
    if trading_calendar.session_distance(start, end) < 1:
        raise _RunAlgoError(
            'There are no trading days between %s and %s' % (
                start.date(),
                end.date(),
            ),
        )

    benchmark_sid, benchmark_returns = benchmark_spec.resolve(
        asset_finder=bundle_data.asset_finder,
        start_date=start,
        end_date=end,
    )

    if algotext is not None:
        if local_namespace:
            ip = get_ipython()  # noqa
            namespace = ip.user_ns
        else:
            namespace = {}

        for assign in defines:
            try:
                name, value = assign.split('=', 2)
            except ValueError:
                raise ValueError(
                    'invalid define %r, should be of the form name=value' %
                    assign,
                )
            try:
                # evaluate in the same namespace so names may refer to
                # eachother
                namespace[name] = eval(value, namespace)
            except Exception as e:
                raise ValueError(
                    'failed to execute definition for name %r: %s' % (name, e),
                )
    elif defines:
        raise _RunAlgoError(
            'cannot pass define without `algotext`',
            "cannot pass '-D' / '--define' without '-t' / '--algotext'",
        )
    else:
        namespace = {}
        if algofile is not None:
            algotext = algofile.read()

    if print_algo:
        if PYGMENTS:
            highlight(
                algotext,
                PythonLexer(),
                TerminalFormatter(),
                outfile=sys.stdout,
            )
        else:
            click.echo(algotext)

    first_trading_day = \
        bundle_data.equity_minute_bar_reader.first_trading_day

    data = DataPortal(
        bundle_data.asset_finder,
        trading_calendar=trading_calendar,
        first_trading_day=first_trading_day,
        equity_minute_reader=bundle_data.equity_minute_bar_reader,
        equity_daily_reader=bundle_data.equity_daily_bar_reader,
        adjustment_reader=bundle_data.adjustment_reader,
    )

    pipeline_loader = USEquityPricingLoader.without_fx(
        bundle_data.equity_daily_bar_reader,
        bundle_data.adjustment_reader,
    )

    def choose_loader(column):
        if column in USEquityPricing.columns:
            return pipeline_loader
        raise ValueError(
            "No PipelineLoader registered for column %s." % column
        )

    if isinstance(metrics_set, six.string_types):
        try:
            metrics_set = metrics.load(metrics_set)
        except ValueError as e:
            raise _RunAlgoError(str(e))

    if isinstance(blotter, six.string_types):
        try:
            blotter = load(Blotter, blotter)
        except ValueError as e:
            raise _RunAlgoError(str(e))

    perf = CNTradingAlgorithm(
        namespace=namespace,
        data_portal=data,
        get_pipeline_loader=choose_loader,
        trading_calendar=trading_calendar,
        sim_params=SimulationParameters(
            start_session=start,
            end_session=end,
            trading_calendar=trading_calendar,
            capital_base=capital_base,
            data_frequency=data_frequency,
        ),
        metrics_set=metrics_set,
        blotter=blotter,
        benchmark_returns=benchmark_returns,
        benchmark_sid=benchmark_sid,
        **{
            'initialize': initialize,
            'handle_data': handle_data,
            'before_trading_start': before_trading_start,
            'analyze': analyze,
        } if algotext is None else {
            'algo_filename': getattr(algofile, 'name', '<algorithm>'),
            'script': algotext,
        }
    ).run()

    if output == '-':
        click.echo(str(perf))
    elif output != os.devnull:  # make the zipline magic not write any data
        perf.to_pickle(output)

    return perf


def run_algorithm(start,
                  end,
                  initialize,
                  capital_base=5e+6,
                  handle_data=None,
                  before_trading_start=None,
                  analyze=None,
                  data_frequency='daily',
                  bundle='mydb',
                  bundle_timestamp=None,
                  trading_calendar=None,
                  metrics_set='default',
                  benchmark_returns=None,
                  default_extension=True,
                  extensions=(),
                  strict_extensions=True,
                  environ=os.environ,
                  blotter='default'):
    """
    运行交易策略算法.

    Parameters
    ----------
    start : datetime
        回测的开始时间.
    end : datetime
        回测的结束时间.
    initialize : callable[context -> None]
        策略算法的初始化函数, 每个回测开始前只运行一次, 用来设置策略算法的全局变量.
    capital_base : float
        回测的初始资金.
    handle_data : callable[(context, BarData) -> None], optional
        策略算法处理行情/执行下单操作的函数, 按照设置的策略频率执行.
    before_trading_start : callable[(context, BarData) -> None], optional
        每个交易日开盘前执行的函数(在第一天的初始化函数结束后执行)
    analyze : callable[(context, pd.DataFrame) -> None], optional
        在回测结束以后执行的分析函数. 传入参数为 ``context`` 和回测结果数据.
    data_frequency : {'daily', 'minute'}, optional
        策略的执行频率.
    bundle : str, optional
        *zipline* 专用的数据格式组成的数据包.
    bundle_timestamp : datetime, optional
        数据包的时间戳, 用来区分不同时间点的数据.
    trading_calendar : TradingCalendar, optional
        回测用的交易日历.
    metrics_set : iterable[Metric] or str, optional
        记录的回测性能指标集, :func:`zipline.finance.metrics.load` 根据名称调用.
    default_extension : bool, optional
        Should the default zipline extension be loaded. This is found at
        ``$ZIPLINE_ROOT/extension.py``
    extensions : iterable[str], optional
        The names of any other extensions to load. Each element may either be
        a dotted module path like ``a.b.c`` or a path to a python file ending
        in ``.py`` like ``a/b/c.py``.
    strict_extensions : bool, optional
        Should the run fail if any extensions fail to load. If this is false,
        a warning will be raised instead.
    environ : mapping[str -> str], optional
        The os environment to use. Many extensions use this to get parameters.
        This defaults to ``os.environ``.
    blotter : str or zipline.finance.blotter.Blotter, optional
        交易信息记录类, 调用前需要用 ``zipline.extensions.register`` 先注册.
        默认为 :class:`zipline.finance.blotter.SimulationBlotter`, 永远不会取消订单.

    Returns
    -------
    perf : pd.DataFrame
        交易策略的每日回测结果.

    See Also
    --------
    zipline.data.bundles.bundles : 可用的数据包.
    """
    load_extensions(default_extension, extensions, strict_extensions, environ)

    if benchmark_returns is not None:
        benchmark_spec = BenchmarkSpec.from_returns(benchmark_returns)
    else:
        benchmark_spec = BenchmarkSpec(None, None, None, None, True)

    return _run(
        handle_data=handle_data,
        initialize=initialize,
        before_trading_start=before_trading_start,
        analyze=analyze,
        algofile=None,
        algotext=None,
        defines=(),
        data_frequency=data_frequency,
        capital_base=capital_base,
        bundle=bundle,
        bundle_timestamp=bundle_timestamp,
        start=start,
        end=end,
        output=os.devnull,
        trading_calendar=trading_calendar,
        print_algo=False,
        metrics_set=metrics_set,
        local_namespace=False,
        environ=environ,
        blotter=blotter,
        benchmark_spec=benchmark_spec,
    )
