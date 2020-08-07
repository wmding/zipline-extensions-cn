from zipline.pipeline import CustomFactor
from .basic import Returns
from zipline_extensions_cn.pipeline.data import CNEquityPricing, CNFinancialData

import pandas as pd
import numpy as np
from scipy import stats


class Alpha1(CustomFactor):
    """
    (rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5)

    """
    inputs = [CNEquityPricing.close, Returns(window_length=2)]
    window_length = 20

    def compute(self, today, assets, out, close, returns):
        v000 = np.empty((5, out.shape[0]))
        for i0 in range(1, 6):
            v000000 = returns[-i0]
            v000001 = np.full(out.shape[0], 0.0)
            v00000 = v000000 < v000001
            v000010 = np.empty((20, out.shape[0]))
            for i1 in range(1, 21):
                v000010[-i1] = returns[-i1]
            v00001 = np.std(v000010, axis=0)
            v00002 = close[-i0]
            v0000lgcl = np.empty(out.shape[0])
            v0000lgcl[v00000] = v00001[v00000]
            v0000lgcl[~v00000] = v00002[~v00000]
            v0000 = v0000lgcl
            v0001 = np.full(out.shape[0], 2.0)
            v000[-i0] = np.power(v0000, v0001)
        v00 = np.argmax(v000, axis=0)
        rank = stats.rankdata(v00)
        offset = np.full(out.shape[0], 0.5)
        out[:] = rank - offset