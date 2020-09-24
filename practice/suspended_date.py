from zipline_extensions_cn.data import bundles as bundles_module
import os
import pandas as pd
from zipline.utils.run_algo import load_extensions
from pandas import read_sql_query
from sqlalchemy import create_engine

engine = create_engine('mysql+mysqldb://DBMan:Mhdb;1903@192.168.2.73/AShareData?charset=utf8')
engine_factors = create_engine('mysql+mysqldb://DBMan:Mhdb;1903@192.168.2.73/FactorLibrary?charset=utf8')


# Load extensions.py; this allows you access to custom bundles
# load_extensions(
#     default=True,
#     extensions=[],
#     strict=True,
#     environ=os.environ,
# )

#
# sql_dailyquotes = "select code, trading_date, open, high, low, close, volume, up_limit, down_limit " \
#                   "from DailyQuotes where trading_date >= '2020-01-01'"
# df_dailyquotes = read_sql_query(
#     sql_dailyquotes,
#     engine,
#     # index_col=['trading_date', 'code'],
#     parse_dates=['trading_date'],
#     # chunksize=500,
# )

factor = 'ipo_date_test'

sql_fundamentals = "select ts_code,  f_ann_date, value_factor  from {0}".format(factor)

df_fundamentals = read_sql_query(
    sql_fundamentals,
    engine_factors,
    # index_col=['trading_date', 'code'],
    parse_dates=['f_ann_date'],
    # chunksize=500,
)

factor = 'IndustryId'

sql_fundamentals = "select ts_code,  f_ann_date, value_factor  from {0}".format(factor)

df_fundamentals = read_sql_query(
    sql_fundamentals,
    engine_factors,
    # index_col=['trading_date', 'code'],
    parse_dates=['f_ann_date'],
    # chunksize=500,
)

df_fundamentals.value_factor = df_fundamentals.value_factor.astype('int64')

df_fundamentals.to_sql('industry_id', engine_factors, if_exists='replace')