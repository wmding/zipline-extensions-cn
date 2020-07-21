from zipline.utils.numpy_utils import float64_dtype

from zipline.pipeline.domain import CN_EQUITIES
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


CNFinancialData = FundamentalsDataSet.specialize(CN_EQUITIES)
