# -*- coding: utf-8 -*-

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine, MetaData
from sqlalchemy import Table, Column, Date, Integer, String, ForeignKey

# 创建对象的基类:
Base = declarative_base()

# 连接数据库
# engine = create_engine('sqlite:///test.db', echo=True)
engine_test = create_engine('mysql+mysqldb://DBMan:Mhdb;1903@192.168.2.73/ZiplineTest?charset=utf8')

# 绑定引擎
Base.metadata = MetaData(engine_test)

# 定义表格
user_table = Table('user', Base.metadata,
                   Column('id', Integer, primary_key=True),
                   Column('name', String(50)),
                   Column('fullname', String(100)),
                   Column('english name', String(50)),
                   )

address_table = Table('address', Base.metadata,
                      Column('id', Integer, primary_key=True),
                      Column('user_id', None, ForeignKey('user.id')),
                      Column('email', String(128), nullable=False)
                      )

# Base.metadata.create_all()

user_table.create(bind=engine_test)
# address_table.create()


# 定义User对象:
class User(Base):
    # 表的名字:
    __tablename__ = 'user'

    # 表的结构:
    id = Column(String(20), primary_key=True)
    name = Column(String(20))


# 初始化数据库连接:
# engine = create_engine('mysql+mysqlconnector://DBMan:password@localhost:3306/test')
engine_test = create_engine('mysql+mysqldb://DBMan:Mhdb;1903@192.168.2.73/ZiplineTest?charset=utf8')

# 创建DBSession类型:
DBSession = sessionmaker(bind=engine_test)

# 创建session对象:
session = DBSession()
# 创建新User对象:
new_user = User(id='5', name='Bob')
# 添加到session:
session.add(new_user)
# 提交即保存到数据库:
session.commit()
# 关闭session:
session.close()

# 创建Session:
session = DBSession()
# 创建Query查询，filter是where条件，最后调用one()返回唯一行，如果调用all()则返回所有行:
user = session.query(User).filter(User.id == '5').one()
# 打印类型和对象的name属性:
print('type:', type(user))
print('name:', user.name)
# 关闭Session:
session.close()
