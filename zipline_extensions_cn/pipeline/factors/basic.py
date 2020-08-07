"""Simple common factors.
"""
from numbers import Number
from numpy import (
    arange,
    average,
    clip,
    copyto,
    exp,
    fmax,
    full,
    isnan,
    log,
    NINF,
    sqrt,
    sum as np_sum,
    unique,
)

from zipline_extensions_cn.pipeline.data import CNEquityPricing


from zipline.pipeline import CustomFactor


class Returns(CustomFactor):
    """
    Calculates the percent change in close price over the given window_length.

    **Default Inputs**: [EquityPricing.close]
    """
    inputs = [CNEquityPricing.close]
    window_safe = True

    def _validate(self):
        super(Returns, self)._validate()
        if self.window_length < 2:
            raise ValueError(
                "'Returns' expected a window length of at least 2, but was "
                "given {window_length}. For daily returns, use a window "
                "length of 2.".format(window_length=self.window_length)
            )

    def compute(self, today, assets, out, close):
        out[:] = (close[-1] - close[0]) / close[0]
