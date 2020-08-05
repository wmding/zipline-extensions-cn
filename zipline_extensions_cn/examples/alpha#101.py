from zipline_extensions_cn.pipeline.data import CNEquityPricing, CNFinancialData
from zipline.pipeline import CustomFactor, Pipeline
from zipline.pipeline.factors import SimpleMovingAverage


class RandomFactor(CustomFactor):
    # Pre-declare inputs and window_length
    inputs = [CNEquityPricing.close, CNEquityPricing.high, CNEquityPricing.low]
    window_length = 2

    # Compute market cap value
    def compute(self, today, assets, out, close, high, low):
        out[:] = (close[-1] - close[-2]) / ((high[-1] - low[-1]) + .001)


class MarketCap(CustomFactor):
    # Pre-declare inputs and window_length
    inputs = [CNEquityPricing.close, CNFinancialData.total_share_0QE]
    window_length = 1

    # Compute market cap value
    def compute(self, today, assets, out, close, shares):
        out[:] = close[-1] * shares[-1]

mkt_cap_top_500 = MarketCap().top(500)

last_price = CNEquityPricing.close.latest

remove_penny_stocks = last_price > 1.0

our_factor = RandomFactor().rank(ascending=False, mask=mkt_cap_top_500)

remove_null_factor = our_factor.notnull()

pipe = Pipeline()
pipe.add(our_factor, 'our_factor')
pipe.set_screen(remove_penny_stocks & remove_null_factor)

from zipline_extensions_cn.research import *
start_date = '2019-01-04'
end_date = '2020-06-01'
results = run_pipeline(pipe, start_date, end_date)

pricing_data = get_pricing(
  tickers=results.index.levels[1], # Finds all assets that appear at least once in "factor_data"
  start_date=start_date,
  end_date=end_date, # must be after run_pipeline()'s end date. Explained more in lesson 4
  field='close' # Generally, you should use open pricing. Explained more in lesson 4
)
from alphalens.utils import get_clean_factor_and_forward_returns

merged_data = get_clean_factor_and_forward_returns(
    factor=results,
    prices=pricing_data,
    periods=(1, 5, 10),
    max_loss=0.6,
    quantiles=5,
)

from alphalens.tears import *

create_full_tear_sheet(merged_data)