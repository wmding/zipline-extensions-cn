============
安装使用
============

安装使用过程与 *zipline* 类似

安装
======

创建环境
----------

首先安装 *anaconda*, 然后创建 *conda*  环境, *zipline* 只支持 *python2.7* 和 *python3.5*,
最新的版本 *zipline 1.4.0* 开始能够支持  *python 3.6*.

.. code-block:: bash

    $ conda create -n zipline python=3.5 # 创建环境
    $ conda env remove -n zipline # 删除
    $ conda env list # 查看环境
    $ conda activate zipline # 激活环境
    $ conda deactivate zipline # 退出环境

在 *conda* 环境能, 如果下载比较慢, 可以更改镜像源, 比如改为清华镜像:

.. code-block:: bash

    # 配置清华conda镜像
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple


zipline
----------

扩展内容是在 *zipline* 的基础上进行的, 首先需要安装 *zipline*.
*zipline* 源码获得的方式有两种:

- *github* 下载最新代码 ``git clone xxx`` 到本地.
- 下载最新的 *Release* 版本 *zipline 1.4.0* 的 *xxx.tar.gz* 压缩包, 利用命令 ``tar -zxvf xxx`` 解压缩到本地.

安装方法比较简单, 在源码的根目录直接运行安装脚本 ``etc/dev_install`` 即可:

.. note::

    在安装过程中会遇到一些安装包版本的问题:

    - *bcolz 1.2.1* 版本总是安装失败, 可以尝试改回旧版本 *bcolz 0.12.1*

另外也可以直接按照 *zipline 1.4.0* 的安装方式进行安装.


安装成功后, 可以直接执行命令 ``zipline --help`` 进行测试, 没有报错说明安装成功.

下面是编译环境时旧命令, 可以参考执行

.. code-block:: bash

    $ sudo apt-get install build-essential
    $ ./etc/ordered_pip.sh ./etc/requirements.txt
    $ pip install -r ./etc/requirements_dev.txt
    $ pip install -r ./etc/requirements_blaze.txt
    # 对C扩展代码进行编译
    $ python setup.py build_ext --inplace
    # 如果需要执行命令行操作
    $ python setup.py install


zipline_extensions_cn
------------------------

接下来安装我们编写的扩展包 *zipline_extensions_cn*, 在源码的根目录执行

.. code-block:: bash

    pip install .

这个过程需要安装一些其他的模块:

- mysqlclient: 连接本地数据库.
- alphalens: 运行 *alphalens* 工具包, 评估 *pipeline* 因子.
- pyfolio: 检验回测结果.
- sphinx: 文档编写系统
- sphinx_rtd_theme: *sphinx* 的主题模式.

安装完成后, 运行命令 ``zipline_cn --help`` 测试.

数据
--------

在正式使用 *zipline* 或者 *zipline_extensions_cn* 之前需要确保有 *zipline* 格式的数据 *bundle* 存在.
数据下载后默认存放在 ``~/.zipline/data`` 目录下. 在扩展模块中, 数据来源是我们自己搭建的本地 *MySql* 数据库,
生成的 *bundle* 名称为 *mydb*, 生成方式为:

.. code-block:: python

    zipline_cn ingest -b mydb

使用
=====

目前, 使用该扩展包的方式有三种, 它们的核心都是调用 ``zipline_extensions_cn.utils.run_algo.run_algorithm``.

终端运行
----------

通过调用 ``click`` 模块, 可以生成终端命令 ``zipline_cn``, 该命令运行策略的方式与 ``zipline`` 是相同的,
比如在终端执行某个策略文件 ``zipline_extensions_cn.examples.algorithm_basic``:

.. code-block:: bash

     zipline_cn run -f zipline_extensions_cn/examples/algorithm_basic.py -s 2019-1-31 -e 2020-1-31

``zipline_cn run --help`` 可以查看更多的参数, 以及参数默认值. 策略文件中需要包含必须的策略框架.


文件运行
---------

在用 *pycharm* 调试时, 经常需要对某个文件打断点进行 *debug*. 运行文件的写法为:

.. code-block:: python

    from zipline_extensions_cn.utils.run_algo import run_algorithm

    import pandas as pd

    start = pd.Timestamp('2019-7-15', tz='utc')
    end = pd.Timestamp('2019-7-25', tz='utc')
    run_algorithm(
        start=start,
        end=end,
        initialize=initialize,
        analyze=analyze,
    )

其中, ``initialize`` 函数与 ``analyze`` 需要提前定义好, 或者从策略文件进行读取.

notebook 运行
---------------

目前在 *notebook* 运行回测的方法与运行文件的代码是一样的, 在 *zipline* 框架下会用到 ``zipline_magic`` 的方法,
不过实际作用是一样的, 只是 ``zipline_magic`` 更类似于终端命令.

在 *jupyterhub* 中增加环境的方法:

- 激活环境 ``conda activate xxx``
- 安装 *ipykernel*, ``conda install ipykernel``
- 执行 ``python -m ipykernel install --user --name 环境名称 --display-name "在jupyter中显示的环境名称"``
- 退出环境后, 执行 ``jupyterhub > jupyterhub.log &``

