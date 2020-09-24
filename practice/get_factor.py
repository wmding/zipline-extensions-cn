import sqlalchemy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

table_name = [
    'test_ROE',
    'Current',
    'DebtToAssets',
    'GrossProfitMargin',
    'InventoryTurn',
    'Quick',
    'EBITToInterest',
    'NetProfitCashCover',
    'OcfToInterest',
    'SalesCashCover',

]
engine_factor_simple = sqlalchemy.create_engine(
    'mysql+mysqldb://DBMan:Mhdb;1903@192.168.2.73/FactorLibrarySimple?charset=utf8')

df_merge = None

for itbl in table_name:
    print(itbl)
    df_tmp = pd.read_sql_table(table_name=itbl, con=engine_factor_simple)
    df_tmp.rename(columns={'value_factor': itbl}, inplace=True)

    if df_merge is None:
        df_merge = df_tmp
    else:
        df_merge = pd.merge(df_merge, df_tmp, how="inner", on=["ts_code", "end_date"])

a = df_merge.set_index(['ts_code', 'end_date'])

b = []
for i in range(len(a)):
    c = a.index[i][1] + pd.offsets.DateOffset(years=1)
    d = (a.index[i][0], c)
    if d in a.index:
        b.append(a.test_ROE.xs(d))
    else:
        b.append(np.nan)

a['next_ROE']=b

#
# f = plt.figure(figsize=(19, 15))
# plt.matshow(a.corr(), fignum=f.number)
# plt.xticks(range(a.shape[1]), a.columns, fontsize=14, rotation=45)
# plt.yticks(range(a.shape[1]), a.columns, fontsize=14)
# cb = plt.colorbar()
# cb.ax.tick_params(labelsize=14)
# plt.title('Correlation Matrix', fontsize=16);
#
# a.corr().style.background_gradient(cmap='coolwarm')


def plot_corr(df):

    f = plt.figure(figsize=(19, 15))
    plt.matshow(df.corr(), fignum=f.number)
    plt.xticks(range(df.shape[1]), df.columns, fontsize=14, rotation=45)
    plt.yticks(range(df.shape[1]), df.columns, fontsize=14)
    cb = plt.colorbar()
    cb.ax.tick_params(labelsize=14)
    plt.title('Correlation Matrix', fontsize=16);

plot_corr(a)


