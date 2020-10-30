import sqlalchemy
import pandas as pd
import numpy as np
import tushare as ts

# 连接数据库
engine_ashare = sqlalchemy.create_engine(
    'mysql+mysqldb://DBMan:Mhdb;1903@192.168.2.73/AShareData?charset=utf8')


def get_atoms(atoms, report_date, engine=engine_ashare):
    df_merge = None

    for atom, atom_tbl in atoms.items():
        sql = "SELECT ts_code, end_date, report_type,  \
              %s FROM AShareData.%s WHERE comp_type = 1 and end_date = '%s'" % (
            atom, atom_tbl, report_date)
        print(sql)

        df_atom = pd.read_sql_query(
            sql,
            engine_ashare,
        )
        df_atom = df_atom.loc[(df_atom.report_type == 1) |
                              (df_atom.report_type == 5)]
        df_atom.drop_duplicates(['ts_code', 'end_date', 'report_type'],
                                inplace=True)
        df_atom.drop_duplicates(['ts_code', 'end_date'],
                                keep='last',
                                inplace=True)

        df_atom = df_atom.drop(['end_date', 'report_type'], axis=1)

        if df_merge is None:
            df_merge = df_atom
        else:
            df_merge = pd.merge(df_merge, df_atom, how="inner", on=["ts_code"])

    return df_merge.set_index(['ts_code'])


def get_delta_atoms(atoms, report_date, engine=engine_ashare):
    df_merge = None
    pre_date = pd.to_datetime(report_date) - pd.offsets.DateOffset(years=1)

    for atom, atom_tbl in atoms.items():
        sql = "SELECT ts_code, end_date, report_type,  \
              %s FROM AShareData.%s WHERE comp_type = 1 and \
<<<<<<< HEAD
              (end_date = '%s' or end_date = '%s')" % (atom, atom_tbl,
                                                       report_date, pre_date)
=======
              (end_date = '%s' or end_date = '%s')" % (atom, atom_tbl, report_date, pre_date)
>>>>>>> origin/master
        print(sql)

        df_atom = pd.read_sql_query(
            sql,
            engine_ashare,
        )
<<<<<<< HEAD
        df_atom = df_atom.loc[(df_atom.report_type == 1) |
                              (df_atom.report_type == 5)]
        df_atom.drop_duplicates(['ts_code', 'end_date', 'report_type'],
                                inplace=True)
        df_atom.drop_duplicates(['ts_code', 'end_date'],
                                keep='last',
                                inplace=True)
=======
        df_atom = df_atom.loc[(df_atom.report_type == 1) | (df_atom.report_type == 5)]
        df_atom.drop_duplicates(['ts_code', 'end_date', 'report_type'], inplace=True)
        df_atom.drop_duplicates(['ts_code', 'end_date'], keep='last', inplace=True)
>>>>>>> origin/master
        df_atom = df_atom.drop(['report_type'], axis=1)

        if df_merge is None:
            df_merge = df_atom
        else:
<<<<<<< HEAD
            df_merge = pd.merge(df_merge,
                                df_atom,
                                how="inner",
                                on=["ts_code", "end_date"])

    df_merge = df_merge.set_index(['ts_code', 'end_date'])
    df_delta = df_merge.xs(report_date, level=1) - df_merge.xs(pre_date,
                                                               level=1)
=======
            df_merge = pd.merge(df_merge, df_atom, how="inner", on=["ts_code", "end_date"])

    df_merge = df_merge.set_index(['ts_code', 'end_date'])
    df_delta = df_merge.xs(report_date, level=1) - df_merge.xs(pre_date, level=1)
>>>>>>> origin/master

    return df_delta


def tata(report_date):
    delta_atoms = {
        'total_cur_assets': 'FinancialBalancesheet',  # '流动资产合计',
        'money_cap': 'FinancialBalancesheet',  # 货币资金
        'total_cur_liab': 'FinancialBalancesheet',  # 流动负债合计
        'non_cur_liab_due_1y': 'FinancialBalancesheet',  # 一年内到期的非流动负债
        'taxes_payable': 'FinancialBalancesheet',  # 应交税费
    }

    df = get_delta_atoms(delta_atoms, report_date)

    atoms = {
        'depr_fa_coga_dpba': 'FinancialCashflow',  # 固定资产折旧、油气资产折耗、生产性生物资产折旧
        'total_assets': 'FinancialBalancesheet',  # 资产总计
    }
    df = df.join(get_atoms(atoms, report_date))

    return (df.total_cur_assets - df.money_cap -
<<<<<<< HEAD
            (df.total_cur_liab - df.non_cur_liab_due_1y - df.taxes_payable) -
            df.depr_fa_coga_dpba) / df.total_assets
=======
            (df.total_cur_liab - df.non_cur_liab_due_1y - df.taxes_payable)
            - df.depr_fa_coga_dpba) / df.total_assets
>>>>>>> origin/master


def ch_cs(report_date):
    delta_atoms = {
        'accounts_receiv': 'FinancialBalancesheet',  # '应收账款',
    }

    df = get_delta_atoms(delta_atoms, report_date)

    atoms = {
        'total_revenue': 'FinancialIncome',  # 营业收入
    }
    df = df.join(get_atoms(atoms, report_date))

    return (df.total_revenue - df.accounts_receiv) / df.total_revenue


def otherc(report_date):
    atoms = {
        'oth_receiv': 'FinancialBalancesheet',  # 其他应收款
        'total_assets': 'FinancialBalancesheet',  # 资产总计
    }
    df = get_atoms(atoms, report_date)

    return df.oth_receiv / df.total_assets


def loss(report_date):
    atoms = {
        'n_income_attr_p': 'FinancialIncome',  # 净利润(不含少数股东损益)
    }
    df = get_atoms(atoms, report_date)
    return df.n_income_attr_p < 0


def SD_VOL(report_date):
    pre_date = pd.to_datetime(report_date) - pd.offsets.DateOffset(years=1)

    sql = "SELECT trading_date, code, close, volume, market_value,circulation_market_value  \
<<<<<<< HEAD
          FROM AShareData.DailyQuotes WHERE trading_date > '%s' and trading_date <= '%s'" % (
        pre_date, report_date)

    df = pd.read_sql_query(sql,
                           engine_ashare,
                           index_col=['code', 'trading_date'])

    close_m = df.close.groupby(
        [pd.Grouper(level='code'),
         pd.Grouper(level='trading_date', freq='M')]).last()
    market_m = df.circulation_market_value.groupby(
        [pd.Grouper(level='code'),
         pd.Grouper(level='trading_date', freq='M')]).last()
    volume_m = df.volume.groupby(
        [pd.Grouper(level='code'),
         pd.Grouper(level='trading_date', freq='M')]).sum()
=======
          FROM AShareData.DailyQuotes WHERE trading_date > '%s' and trading_date <= '%s'" % (pre_date, report_date)

    df = pd.read_sql_query(
        sql,
        engine_ashare,
        index_col=['code', 'trading_date']
    )

    close_m = df.close.groupby([pd.Grouper(level='code'),
                                pd.Grouper(level='trading_date', freq='M')]
                               ).last()
    market_m = df.circulation_market_value.groupby([pd.Grouper(level='code'),
                                                    pd.Grouper(level='trading_date', freq='M')]
                                                   ).last()
    volume_m = df.volume.groupby([pd.Grouper(level='code'),
                                  pd.Grouper(level='trading_date', freq='M')]
                                 ).sum()
>>>>>>> origin/master

    turn_over_m = volume_m / (market_m / close_m)

    return turn_over_m.groupby(pd.Grouper(level=0)).std()


def stkcyc(report_date):
    ts.set_token('915388f0f6dee2dedd2e89fda731183dceae8e3651bd12d024796f9a')

    pre_date = pd.to_datetime(report_date) - pd.offsets.DateOffset(years=1)
    pre_date = pre_date.strftime('%Y-%m-%d')

    last_date = pd.to_datetime(report_date) + pd.offsets.DateOffset(years=1)
    last_date = last_date.strftime('%Y-%m-%d')
    pro = ts.pro_api()
<<<<<<< HEAD
    df = pro.index_monthly(ts_code='000001.SH',
                           start_date=pre_date,
                           end_date=last_date,
=======
    df = pro.index_monthly(ts_code='000001.SH', start_date=pre_date, end_date=last_date,
>>>>>>> origin/master
                           fields='ts_code,trade_date,close')

    annual_income = df.close[0] / df.close[12]

    return annual_income < 1


def issue(report_date):
    atoms = {
        'total_assets': 'FinancialBalancesheet',  # 资产总计
    }

    df = get_delta_atoms(atoms, report_date)
<<<<<<< HEAD
    df.rename(columns={'total_assets': 'delta_total_assets'}, inplace=True)
=======
    df.rename(
        columns={
            'total_assets': 'delta_total_assets'
        },
        inplace=True
    )
>>>>>>> origin/master

    df = df.join(get_atoms(atoms, report_date))

    return df.delta_total_assets / df.total_assets > 0.8


h5index2019 = pd.read_csv('practice/h5index2019.csv')
<<<<<<< HEAD
h5index2019.value = (h5index2019.value / 100)**2
=======
h5index2019.value = (h5index2019.value / 100) ** 2
>>>>>>> origin/master
h5index2019.columns = ['code', 'h5index2019']
df = h5index2019.set_index(['code'])

institu2019 = pd.read_csv('practice/institu2019.csv')
institu2019.value = institu2019.value / 100
institu2019.columns = ['code', 'institu2019']
institu2019 = institu2019.set_index(['code'])

df = df.join(institu2019)

tata2019 = tata('2019-12-31')
tata2019.name = 'tata2019'
df = df.join(tata2019)

ch_cs2019 = ch_cs('2019-12-31')
ch_cs2019.name = 'ch_cs2019'
df = df.join(ch_cs2019)

otherc2019 = otherc('2019-12-31')
otherc2019.name = 'otherc2019'
df = df.join(otherc2019)

loss2019 = loss('2019-12-31').astype(int)
loss2019.name = 'loss2019'
df = df.join(loss2019)

issue2019 = issue('2019-12-31').astype(int)
issue2019.name = 'issue2019'
df = df.join(issue2019)

sd_vol2019 = SD_VOL('2019-12-31')
sd_vol2019.name = 'sd_vol2019'
df = df.join(sd_vol2019)

stkcyc2019 = issue('2019-12-31').astype(int)
stkcyc2019.name = 'stkcyc2019'
df = df.join(stkcyc2019)

df = df.dropna()

cscore = -0.983 - 2.261*df.tata2019 - 2.495*df.ch_cs2019 + 5.075*df.otherc2019 + \
         0.797*df.loss2019 - 0.059*df.sd_vol2019 - 3.198*df.h5index2019 - \
<<<<<<< HEAD
         4.298*df.institu2019 + 0.888*df.issue2019 + 1.184*df.stkcyc2019

print(cscore)
=======
         4.298*df.institu2019 + 0.888*df.issue2019 + 1.184*df.stkcyc2019
>>>>>>> origin/master
