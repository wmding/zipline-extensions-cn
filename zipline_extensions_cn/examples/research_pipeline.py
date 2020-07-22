from zipline_extensions_cn.research import *

start_date = '2019-03-06'
end_date = '2020-03-19'

from zipline.pipeline import Pipeline
from zipline_extensions_cn.pipeline.data import CNFinancialData, CNEquityPricing

close = CNEquityPricing.close.latest
roeavg3 = CNFinancialData.total_share_0QE.latest


def make_pipeline():
    return Pipeline(
        columns={
            'close': close,
        },
    )


pipe = Pipeline(
    columns={
        'close': close,
        'roeavg3': roeavg3,
    },
)

run_pipeline(pipe, start_date, end_date)
