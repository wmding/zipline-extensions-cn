.. _contents:

=========
总目录
=========

*zipline* 是一种用 *python* 编写的历史数据回测框架, 可以实现股票/期货的回测, 支持分钟/日线数据.
提到 *zipline* 就不得不提 `quantopian <https://www.quantopian.com/home>`_.
*quantopian* 是在线的证券量化平台, 文档系统非常完善,
国内的很多量化平台在模式上与它大同小异.
*zipline* 是 *quantopian* 的回测引擎, 主要完成历史数据回测, 只是由于 *zipline* 是开源的, 所以在功能上也许会有所削减.
关于 *zipline* 的介绍可见 `zipline文档 <https://www.zipline.io>`_.


*zipline* 对于中国股市数据的支持是有限制的, 需要做一些修改才能方便使用.
我们最初对 *zipline* 的改进是直接对 *zipline* 的 *github* 源码进行更改,
但发现每隔一段时间, *github* 上的源码会有比较大的更新, 每次更新后,
我们都需要再对源代码更新一遍. 为了减少这种重复性工作, 我们决定做一个扩展模块 *zipline-extensions-cn*
该模块的主要目的是对 *zipline* 做再次封装, 使其满足我们分析中国市场数据的需求.
目前, 该扩展模块基本完成, 内容也许比较粗糙, 后续可以留出时间去做改进.

该文档计划分为以下几个部分:

安装使用
=========

.. toctree::
   :maxdepth: 2

   install


扩展内容
=============

.. toctree::
   :maxdepth: 2

   ashare

功能模块
==========

.. toctree::
   :maxdepth: 2

   pipeline
   alphalens
   algorithms

知识储备
============

.. toctree::
   :maxdepth: 2

   statistics/index