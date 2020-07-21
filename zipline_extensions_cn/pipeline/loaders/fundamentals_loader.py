from zipline.pipeline.loaders.base import PipelineLoader
from zipline.pipeline.loaders.frame import DataFrameLoader
from interface import implements


class FundamentalsLoader(implements(PipelineLoader)):
    """
    Fundamental data loader.
    """

    def __init__(self, fundamentals_reader):
        self.fundamentals_reader = fundamentals_reader
        # self._all_sessions = get_calendar("NYSE").all_sessions

    def load_adjusted_array(self, domain, columns, dates, sids, mask):
        out = {}
        for column in columns:
            fundamentals_df = self.fundamentals_reader.read(
                column.name,
                dates,
                sids,
            )
            df_loader = DataFrameLoader(column, fundamentals_df)
            out.update(df_loader.load_adjusted_array(domain, [column,], dates, sids, mask))

        return out
