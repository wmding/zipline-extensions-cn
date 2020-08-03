from zipline.pipeline import Pipeline
from zipline_extensions_cn.pipeline.data import CNFinancialData, CNEquityPricing

filter1 = CNEquityPricing.volume.latest > 4000
#filter2 = CNEquityPricing.high.latest < CNEquityPricing.up_limit.latest/1000
#filter3 = CNEquityPricing.high.latest > CNEquityPricing.down_limit.latest/1000
universe = filter1

market_cap = CNEquityPricing.close.latest * CNFinancialData.total_share_0QE.latest

market_cap_deciles = market_cap.deciles(mask=market_cap.notnull())
close = CNEquityPricing.close.latest

# market_cap_1_top = market_cap.top(5, mask=maket_cap_1)
pipe = Pipeline()
pipe.add(close, 'close')
pipe.add(market_cap, "market_cap")
pipe.set_screen(universe)

start_date = '2019-03-06'
end_date = '2019-4-8'

from zipline_extensions_cn.research import *
results=run_pipeline(pipe, start_date, end_date)
print(results.head(10))

p = get_pricing('000001.SZ', '2019-01-31', '2020-02-04', 'up_limit')