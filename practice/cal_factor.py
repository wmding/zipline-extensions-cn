import re
from collections import defaultdict
import sqlalchemy
import pandas as pd

# 设置参数
factor_name_eng = "test_EP"
factor_name_cn = "EP当年"

factor_formula_origin = "fuc_neg({净利润(不含少数股东损益)} - {非经常性损益}) / fuc_neg({市值})"

# 负值就为None的函数
fuc_neg = lambda g: g if g > 0 else None
fuc_neg_30000000 = lambda g: g if g > 30000000 else None

# 连接数据库
engine_ashare = sqlalchemy.create_engine(
    'mysql+mysqldb://DBMan:Mhdb;1903@192.168.2.73/AShareData?charset=utf8')

engine_factor_simple = sqlalchemy.create_engine(
    'mysql+mysqldb://DBMan:Mhdb;1903@192.168.2.73/FactorLibrarySimple?charset=utf8')

# 生成原子
## 有几个原子
atom_num = factor_formula_origin.count("{")

## 生成正则表达式,用于匹配原子
regexp_atom = r"^"
for i in range(atom_num):
    regexp_atom = regexp_atom + r".*?({.+?})"
    if i == atom_num - 1:
        regexp_atom = regexp_atom + r".*$"

## 匹配原子名称,存成字典
m_atom = re.match(regexp_atom, factor_formula_origin)

## 把原子存成字典
atom_dict = defaultdict(list)  # 存储原子信息的字典
if m_atom:  # 如果发生匹配不上,就会出问题
    for i in range(atom_num):
        atom_origin = m_atom.group(i + 1)
        atom_total = atom_origin[1:-1]
        if atom_total not in atom_dict["cn_name"]:  # 只添加非重复的原子
            atom_dict["cn_name"].append(atom_total)
else:
    print("There's something wrong with factor_formula matching.")

# 生成DataFrame
## 根据原子的中文名,查询对应的数据表和字段名
df_description = pd.read_sql_table(table_name="Description", con=engine_ashare)

for i in range(len(atom_dict["cn_name"])):
    df_description_select = df_description[df_description["name"] == atom_dict["cn_name"][i]]
    if len(df_description_select) != 1:
        print("Atom_name is wrong,be careful!")
    atom_dict["table_name"].append("_" + df_description_select.iloc[0, 2])  # 2代表table_name,这里增加了"_",和AshareData的不同,以示区分
    atom_dict["field_name"].append(df_description_select.iloc[0, 0])  # 0代表field_name

## 生成要读的表和该表对应字段的字典
name_financial_dict = defaultdict(list)
name_financial_table = atom_dict["table_name"]
name_financial_table = list(set(name_financial_table))  # 去重
for i in range(len(name_financial_table)):  # 添加每个财务表需要下载的字段
    name_financial_field = []
    for j in range(len(atom_dict['cn_name'])):
        if atom_dict["table_name"][j] == name_financial_table[i]:
            name_financial_field.append(atom_dict["field_name"][j])
    name_financial_field = list(set(name_financial_field))  # 去重
    name_financial_dict[name_financial_table[i]] = name_financial_field

## 整理财务报表数据
for i in range(len(name_financial_dict)):
    table_name_from_dict = list(name_financial_dict.keys())[i]
    field_name = ["ts_code", "end_date"]
    field_name.extend(name_financial_dict[table_name_from_dict])
    df_tmp = pd.read_sql_table(table_name=table_name_from_dict,
                               con=engine_factor_simple,
                               columns=field_name)
    for name_i in name_financial_dict[table_name_from_dict]:
        field_financial_rename = table_name_from_dict + "_" + name_i
        df_tmp = df_tmp.rename(columns={name_i: field_financial_rename})
    if i == 0:
        df_merge = df_tmp
    else:
        df_merge = pd.merge(df_merge, df_tmp, how="inner",
                            on=["ts_code", "end_date"])  # 只有多张报表同时期的都在,才会保留下来该行

# 生成因子的计算公式,并计算
## 生成用于匹配的正则表达式,用于匹配计算符号
regexp_cal_symbol = r"^"
for i in range(atom_num):
    regexp_cal_symbol = regexp_cal_symbol + r"(.*?){.+?}"
    if i == atom_num - 1:
        regexp_cal_symbol = regexp_cal_symbol + r"(.*)$"

## 匹配计算符号
m_cal_symbol = re.match(regexp_cal_symbol, factor_formula_origin)

## 匹配原子名称(再匹配一次,因为上面只存了非重复的原子)
m_atom = re.match(regexp_atom, factor_formula_origin)

## 合并原子和计算符号,并生成有用的公式
str_cal_fuction = ''  # "lambda g:"
for i in range(atom_num):
    # i = 0
    atom_total_new = m_atom.group(i + 1)
    atom_total_new = atom_total_new[1:-1]
    atom_index = atom_dict["cn_name"].index(atom_total_new)
    atom_i = "g['" + \
             atom_dict["table_name"][atom_index] + "_" + \
             atom_dict["field_name"][atom_index] + \
             "']"
    str_cal_fuction = str_cal_fuction + m_cal_symbol.group(i + 1)
    str_cal_fuction = str_cal_fuction + atom_i
    if i == atom_num - 1:
        str_cal_fuction = str_cal_fuction + m_cal_symbol.group(i + 2)


# str_cal_fuction = "try:\n\t" + str_cal_fuction + "except BaseException:\n\tpass"

## 计算因子序列
def calculate_fuc(g, str_cal):
    try:
        tmp_value = eval(str_cal)
        return tmp_value
    except:
        return None


value_factor = df_merge.apply(calculate_fuc, axis=1, args=(str_cal_fuction,))
df_merge["value_factor"] = value_factor

# 写数据库
## 写因子描述表
df_factor_description = pd.DataFrame({
    "factor_name_eng": [factor_name_eng],
    "factor_name_cn": [factor_name_cn],
    "factor_formula_origin": [factor_formula_origin]
})
df_factor_description.to_sql("_FactorDescription", engine_factor_simple,
                             if_exists='append', index=False)

## 写因子表
df_factor = df_merge[["ts_code", "end_date", "value_factor"]]
df_factor.to_sql(factor_name_eng, engine_factor_simple,
                 if_exists='append', index=False)

# # 描述性统计
# import numpy as np
# from numpy import mean, median
#
# # 创建数组：
# percentiles = df_factor.dropna()["value_factor"]
# # 计算平均值，结果保留两位小数：
# a = round(mean(percentiles), 2)
# # 计算中位数：
# b = median(percentiles)
# # 计算百分位数（下四分位数）：
# c = np.percentile(percentiles, 25)
# # 计算百分位数（上四分位数）：
# d = np.percentile(percentiles, 75)
# print('平均数：%s ,中位数：%s ,下四分位数：%s, 上四分位数：%s . ' % (a, b, c, d))
#
# percentiles.describe()
