from zipline.utils.numpy_utils import float64_dtype, categorical_dtype

from zipline.pipeline.domain import CN_EQUITIES
from zipline.pipeline.data.dataset import Column, DataSet


class EquityPricing(DataSet):
    """
    :class:`~zipline.pipeline.data.DataSet` containing daily trading prices and
    volumes.
    """
    open = Column(float64_dtype, currency_aware=True)
    high = Column(float64_dtype, currency_aware=True)
    low = Column(float64_dtype, currency_aware=True)
    close = Column(float64_dtype, currency_aware=True)
    up_limit = Column(float64_dtype, currency_aware=True)
    volume = Column(float64_dtype)
    currency = Column(categorical_dtype)


CNEquityPricing = EquityPricing.specialize(CN_EQUITIES)
