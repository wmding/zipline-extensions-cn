from sqlalchemy import create_engine
import pandas as pd
from pandas import read_sql_query

sql = '''SELECT * FROM AShareData.FinancialBalancesheet where report_type = 1 or report_type = 5;'''

engine = create_engine('mysql+mysqldb://DBMan:Mhdb;1903@192.168.2.73/AShareData?charset=utf8')

df_fundamentals = read_sql_query(
    sql,
    engine,
    # index_col=['trading_date', 'code'],
    parse_dates=['ann_date', 'f_ann_date', 'end_date'],
    # chunksize=500,
)
df = df_fundamentals.loc[(df_fundamentals.report_type == 1) | (df_fundamentals.report_type == 5)]
df.drop_duplicates(['ts_code', 'end_date', 'report_type'], inplace=True)
df.drop_duplicates(['ts_code', 'end_date'], keep='last', inplace=True)

df = df.loc[df.end_date.astype(str).str.contains('-12-31')]




date_diff = df.groupby('ts_code')['end_date'].agg('diff')

df.end_date.diff()

date_check = df.loc[date_diff > pd.Timedelta('370 days')]
