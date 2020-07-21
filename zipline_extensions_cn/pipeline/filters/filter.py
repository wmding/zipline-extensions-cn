"""
filter.py
"""

from numpy import (
    any as np_any,
    float64,
    nan,
    nanpercentile,
    uint8,
)

from zipline.lib.labelarray import LabelArray
from zipline.lib.rank import is_missing, grouped_masked_is_maximal

from zipline.pipeline.mixins import (
    CustomTermMixin,
    IfElseMixin,
    LatestMixin,
    PositiveWindowLengthMixin,
    RestrictedDTypeMixin,
    SingleInputMixin,
    StandardOutputs,
)

from zipline.pipeline.filters import CustomFilter, Filter


class AllPresent(CustomFilter, SingleInputMixin, StandardOutputs):
    """Pipeline filter indicating input term has data for a given window.
    """

    def _validate(self):

        if isinstance(self.inputs[0], Filter):
            raise TypeError(
                "Input to filter `AllPresent` cannot be a Filter."
            )

        return super(AllPresent, self)._validate()

    def compute(self, today, assets, out, value):
        if isinstance(value, LabelArray):
            out[:] = ~np_any(value.is_missing(), axis=0)
        else:
            out[:] = ~np_any(
                is_missing(value, self.inputs[0].missing_value),
                axis=0,
            )
