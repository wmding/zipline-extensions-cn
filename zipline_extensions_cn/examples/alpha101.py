from zipline_extensions_cn.pipeline.data import CNEquityPricing, CNFinancialData
from zipline.pipeline import CustomFactor, Pipeline
from zipline.pipeline.factors import SimpleMovingAverage
from zipline_extensions_cn.pipeline.domain import AShare_EQUITIES

from zipline_extensions_cn.pipeline.factors import Alpha1

pipe = Pipeline()
pipe.add(Alpha1(), 'alpha1')

from zipline_extensions_cn.research import *

start_date = '2019-01-04'
end_date = '2020-06-01'
results = run_pipeline(pipe, start_date, end_date)

pricing_data = get_pricing(
    tickers=results.index.levels[1],  # Finds all assets that appear at least once in "factor_data"
    start_date=start_date,
    end_date=end_date,  # must be after run_pipeline()'s end date. Explained more in lesson 4
    field='close'  # Generally, you should use open pricing. Explained more in lesson 4
)
from alphalens.utils import get_clean_factor_and_forward_returns

merged_data = get_clean_factor_and_forward_returns(
    factor=results,
    prices=pricing_data,
    periods=(1, 2, 5),
    max_loss=0.6,
    quantiles=3,
)

from alphalens.tears import *

create_full_tear_sheet(merged_data)
