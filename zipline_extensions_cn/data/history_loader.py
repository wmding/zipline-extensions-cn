from zipline.data.history_loader import DailyHistoryLoader

class CNDailyHistoryLoader(DailyHistoryLoader):
    FIELDS = ('open', 'high', 'low', 'close', 'volume', 'sid', 'up_limit')
