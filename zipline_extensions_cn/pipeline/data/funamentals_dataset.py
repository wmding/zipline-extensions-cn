from zipline.utils.numpy_utils import float64_dtype, datetime64ns_dtype, datetime, object_dtype
from numpy import int64
from numpy import datetime_as_string
from zipline_extensions_cn.pipeline.domain import AShare_EQUITIES
from zipline.pipeline.data.dataset import Column, DataSet


class FundamentalsDataSet(DataSet):
    """
    :class:`~zipline.pipeline.data.DataSet` containing daily trading prices and
    volumes.
    """
    ROEAVE3 = Column(float64_dtype)
    total_share_0QE = Column(float64_dtype)
    ipo_date = Column(float64_dtype)
    delist_date = Column(float64_dtype)
    IndustryId = Column(float64_dtype)
    ipo_date_test = Column(datetime)
    industry_id = Column(object_dtype)


CNFinancialData = FundamentalsDataSet.specialize(AShare_EQUITIES)
