from . import core as bundles
import pandas as pd
import numpy as np
from logbook import Logger
from pandas import read_sql_query
from sqlalchemy import create_engine
from six import iteritems

log = Logger(__name__)

engine = create_engine('mysql+mysqldb://DBMan:Mhdb;1903@192.168.2.73/AShareData?charset=utf8')
engine_factors = create_engine('mysql+mysqldb://DBMan:Mhdb;1903@192.168.2.73/FactorLibrary?charset=utf8')


def gen_asset_metadata_origin(data, show_progress):
    if show_progress:
        log.info('Generating asset metadata.')

    data = data.rename(
        columns={
            'code': 'symbol',
            'trading_date': 'date',
        },
    )

    data = data.groupby(
        by='symbol'
    ).agg(
        {'date': [np.min, np.max]}
    )
    data.reset_index(inplace=True)
    data['start_date'] = data.date.amin
    data['end_date'] = data.date.amax
    del data['date']
    data.columns = data.columns.get_level_values(0)

    data['exchange'] = 'mydb'
    data['auto_close_date'] = data['end_date'].values + pd.Timedelta(days=1)
    return data


def gen_asset_metadata(data, show_progress):
    if show_progress:
        log.info('Generating asset metadata.')

    data = data.rename(
        columns={
            'code': 'symbol',
        },
    )

    data.columns = data.columns.get_level_values(0)

    data['exchange'] = 'mydatabase'  # full exchange name
    data['auto_close_date'] = data['end_date'].values + pd.Timedelta(days=1)
    return data


def parse_splits(data, show_progress):
    if show_progress:
        log.info('Parsing split data.')

    data['split_ratio'] = 1.0 / data.split_ratio
    data.rename(
        columns={
            'split_ratio': 'ratio',
            'date': 'effective_date',
        },
        inplace=True,
        copy=False,
    )
    return data


def parse_dividends(data, show_progress):
    if show_progress:
        log.info('Parsing dividend data.')

    data['record_date'] = data['declared_date'] = data['pay_date'] = pd.NaT
    data.rename(
        columns={
            'ex_dividend': 'amount',
            'date': 'ex_date',
        },
        inplace=True,
        copy=False,
    )
    return data


def parse_pricing_and_vol(data,
                          sessions,
                          symbol_map):
    for asset_id, symbol in iteritems(symbol_map):
        asset_data = data.xs(
            symbol,
            level=1
        ).reindex(
            sessions.tz_localize(None)
        ).fillna(0.0)
        yield asset_id, asset_data


@bundles.register(
    "mydb",
    calendar_name="AShare"
)
def mydb_bundle(environ,
                asset_db_writer,
                minute_bar_writer,
                daily_bar_writer,
                adjustment_writer,
                fundamentals_writer,
                calendar,
                start_session,
                end_session,
                cache,
                show_progress,
                output_dir):
    """
    从自己搭建的 *MySql* 服务器下载数据, 然后利用各种 *writers* 写成 *bundle*.

    Parameters
    ----------
    environ : mapping
        运行环境, 一般为 ``os.environ``
    asset_db_writer : AssetDBWriter
        公司元数据 *writer*,  包括 *symbol* 以及对应数据的起始日期.
    minute_bar_writer : BcolzMinuteBarWriter
        分钟数据 *writer*
    daily_bar_writer : BcolzDailyBarWriter
        分钟数据 *writer*, 包括 *open, high, low, close, volume* 字段, 转换成 *bcolz* 格式
    adjustment_writer : SQLiteAdjustmentWriter
      The adjustment db writer to write into.
    calendar : trading_calendars.TradingCalendar
      The trading calendar to ingest for.
    start_session : pd.Timestamp
      The first session of data to ingest.
    end_session : pd.Timestamp
      The last session of data to ingest.
    cache : DataFrameCache
      A mapping object to temporarily store dataframes.
      This should be used to cache intermediates in case the load
      fails. This will be automatically cleaned up after a
      successful load.
    show_progress : bool
      Show the progress for the current load where possible.

    See Also
    --------
    zipline.data.bundles.ingest
    """
    sql_metadata = "select code, max(trading_date) as end_date, min(trading_date) as start_date from " \
                   "DailyQuotes where trading_date >= '2018-01-01' group by code "
    df_metadata = read_sql_query(
        sql_metadata,
        engine,
        parse_dates=['start_date', 'end_date'],
    )

    asset_metadata = gen_asset_metadata(
        df_metadata,
        show_progress,
    )

    exchanges = pd.DataFrame({'exchange': ['mydatabase'],
                              'canonical_name': ['mydb'],
                              'country_code': ['CN']})
    log.info("mydb writing asset metadata")
    asset_db_writer.write(equities=asset_metadata, exchanges=exchanges)

    sql_dailyquotes = "select code, trading_date, open, high, low, close, volume, up_limit, down_limit " \
                      "from DailyQuotes where trading_date >= '2018-01-01'"
    log.info("mydb 正在下载日线数据")
    df_dailyquotes = read_sql_query(
        sql_dailyquotes,
        engine,
        # index_col=['trading_date', 'code'],
        parse_dates=['trading_date'],
        # chunksize=500,
    )
    df_dailyquotes.loc[df_dailyquotes.open.isnull().values == True, 'open'] = df_dailyquotes.close[
        df_dailyquotes.open.isnull().values == True]
    df_dailyquotes.loc[df_dailyquotes.high.isnull().values == True, 'high'] = df_dailyquotes.close[
        df_dailyquotes.high.isnull().values == True]
    df_dailyquotes.loc[df_dailyquotes.low.isnull().values == True, 'low'] = df_dailyquotes.close[
        df_dailyquotes.low.isnull().values == True]
    df_dailyquotes['volume'] = df_dailyquotes['volume'].fillna(0)
    # df_dailyquotes['volume'] = df_dailyquotes['volume'] / 100
    symbol_map = asset_metadata.symbol
    sessions = calendar.sessions_in_range(start_session, end_session)

    df_dailyquotes.set_index(['trading_date', 'code'], inplace=True)

    log.info("mydb 写入日线数据")

    daily_bar_writer.write(
        parse_pricing_and_vol(
            df_dailyquotes,
            sessions,
            symbol_map
        ),
        show_progress=show_progress
    )

    sql_dividend = "select code, ex_dividend_date, " \
                   "cash_payout_and_rights_issue, stock_split_ratio, stock_dividend_ratio " \
                   "from Dividend"
    log.info("mydb 正在下载分红数据")

    df_dividend = read_sql_query(
        sql_dividend,
        engine,
        parse_dates=['ex_dividend_date'],
    )

    df_dividend["split_ratio"] = 1 + df_dividend.stock_split_ratio + df_dividend.stock_dividend_ratio
    del df_dividend["stock_split_ratio"]
    del df_dividend["stock_dividend_ratio"]
    df_dividend = df_dividend.rename(
        columns={
            "code": "symbol",
            "ex_dividend_date": "date",
            "cash_payout_and_rights_issue": "ex_dividend",
        }
    )

    df_dividend = df_dividend[df_dividend.symbol.isin(symbol_map)]
    df_dividend['sid'] = [symbol_map[symbol_map == i].index[0] for i in df_dividend.symbol]

    log.info("mydb 写入分红数据")

    adjustment_writer.write(
        splits=parse_splits(
            df_dividend[[
                'sid',
                'date',
                'split_ratio',
            ]].loc[df_dividend.split_ratio != 1],
            show_progress=show_progress
        ),
        dividends=parse_dividends(
            df_dividend[[
                'sid',
                'date',
                'ex_dividend',
            ]].loc[df_dividend.ex_dividend != 0],
            show_progress=show_progress
        )
    )

    fundamental_factors = ['total_share_0QE', 'ipo_date', 'delist_date', 'IndustryId']

    fundamentals_loaded = pd.DataFrame()

    for factor in fundamental_factors:
        sql_fundamentals = "select ts_code,  f_ann_date, value_factor  from {0}".format(factor)

        log.info("mydb 正在下载财务数据 {}", factor)
        df_fundamentals = read_sql_query(
            sql_fundamentals,
            engine_factors,
            # index_col=['trading_date', 'code'],
            parse_dates=['f_ann_date'],
            # chunksize=500,
        )
        df_fundamentals = df_fundamentals[df_fundamentals.ts_code.isin(symbol_map)]
        df_fundamentals['sid'] = [symbol_map[symbol_map == i].index[0] for i in df_fundamentals.ts_code]
        del df_fundamentals['ts_code']
        df_fundamentals['name'] = factor
        df_fundamentals.rename(
            columns={
                'f_ann_date': 'date',
                'value_factor': 'value',
            },
            inplace=True
        )
        fundamentals_loaded = fundamentals_loaded.append(df_fundamentals)

    log.info("mydb 写入财务数据")

    fundamentals_writer.write(fundamentals=fundamentals_loaded)

    log.info("mydb 数据产生过程结束")
