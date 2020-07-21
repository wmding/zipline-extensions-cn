# import tushare as ts
# ts.set_token('915388f0f6dee2dedd2e89fda731183dceae8e3651bd12d024796f9a')
# pro = ts.pro_api()

import pandas as pd
import numpy as np
from logbook import Logger
from pandas import read_sql_query
from sqlalchemy import create_engine
from six import iteritems

engine = create_engine('mysql+mysqldb://DBMan:Mhdb;1903@192.168.2.73/AShareData?charset=utf8')

sql_dailyquotes = "select code, trading_date from DailyQuotes where volume is null or volume = 0"

df_dailyquotes = read_sql_query(
    sql_dailyquotes,
    engine,
    # index_col=['trading_date', 'code'],
    parse_dates=['trading_date'],
    # chunksize=500,
)

df_dailyquotes['value'] = 1
