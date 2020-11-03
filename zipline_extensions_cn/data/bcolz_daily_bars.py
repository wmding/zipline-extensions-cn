from zipline.data.bcolz_daily_bars import BcolzDailyBarWriter, BcolzDailyBarReader, winsorise_uint32, check_uint32_safe
from functools import partial
import warnings

from bcolz import carray, ctable
import logbook
import numpy as np
from numpy import (
    array,
    full,
    iinfo,
    nan,
)
from pandas import (
    DatetimeIndex,
    NaT,
    read_csv,
    to_datetime,
    Timestamp,
)
from toolz import compose

from zipline.utils.functional import apply
from zipline.utils.input_validation import expect_element
from zipline.utils.numpy_utils import iNaT, float64_dtype, uint32_dtype

logger = logbook.Logger('CNEquityPricing')

CNOHLC = frozenset(['open', 'high', 'low', 'close', 'up_limit', 'down_limit'])

CN_EQUITY_PRICING_BCOLZ_COLUMNS = (
    'open', 'high', 'low', 'close', 'volume', 'day', 'id', 'up_limit', 'down_limit'
)


class CNBcolzDailyBarWriter(BcolzDailyBarWriter):

    def _write_internal(self, iterator, assets):
        """
        Internal implementation of write.

        `iterator` should be an iterator yielding pairs of (asset, ctable).
        """
        total_rows = 0
        first_row = {}
        last_row = {}
        calendar_offset = {}

        # Maps column name -> output carray.
        columns = {
            k: carray(array([], dtype=uint32_dtype))
            for k in CN_EQUITY_PRICING_BCOLZ_COLUMNS
        }

        earliest_date = None
        sessions = self._calendar.sessions_in_range(
            self._start_session, self._end_session
        )

        if assets is not None:
            @apply
            def iterator(iterator=iterator, assets=set(assets)):
                for asset_id, table in iterator:
                    if asset_id not in assets:
                        raise ValueError('unknown asset id %r' % asset_id)
                    yield asset_id, table

        for asset_id, table in iterator:
            nrows = len(table)
            for column_name in columns:
                if column_name == 'id':
                    # We know what the content of this column is, so don't
                    # bother reading it.
                    columns['id'].append(
                        full((nrows,), asset_id, dtype='uint32'),
                    )
                    continue

                columns[column_name].append(table[column_name])

            if earliest_date is None:
                earliest_date = table["day"][0]
            else:
                earliest_date = min(earliest_date, table["day"][0])

            # Bcolz doesn't support ints as keys in `attrs`, so convert
            # assets to strings for use as attr keys.
            asset_key = str(asset_id)

            # Calculate the index into the array of the first and last row
            # for this asset. This allows us to efficiently load single
            # assets when querying the data back out of the table.
            first_row[asset_key] = total_rows
            last_row[asset_key] = total_rows + nrows - 1
            total_rows += nrows

            table_day_to_session = compose(
                self._calendar.minute_to_session_label,
                partial(Timestamp, unit='s', tz='UTC'),
            )
            asset_first_day = table_day_to_session(table['day'][0])
            asset_last_day = table_day_to_session(table['day'][-1])

            asset_sessions = sessions[
                sessions.slice_indexer(asset_first_day, asset_last_day)
            ]
            assert len(table) == len(asset_sessions), (
                'Got {} rows for daily bars table with first day={}, last '
                'day={}, expected {} rows.\n'
                'Missing sessions: {}\n'
                'Extra sessions: {}'.format(
                    len(table),
                    asset_first_day.date(),
                    asset_last_day.date(),
                    len(asset_sessions),
                    asset_sessions.difference(
                        to_datetime(
                            np.array(table['day']),
                            unit='s',
                            utc=True,
                        )
                    ).tolist(),
                    to_datetime(
                        np.array(table['day']),
                        unit='s',
                        utc=True,
                    ).difference(asset_sessions).tolist(),
                )
            )

            # Calculate the number of trading days between the first date
            # in the stored data and the first date of **this** asset. This
            # offset used for output alignment by the reader.
            calendar_offset[asset_key] = sessions.get_loc(asset_first_day)

        # This writes the table to disk.
        full_table = ctable(
            columns=[
                columns[colname]
                for colname in CN_EQUITY_PRICING_BCOLZ_COLUMNS
            ],
            names=CN_EQUITY_PRICING_BCOLZ_COLUMNS,
            rootdir=self._filename,
            mode='w',
        )

        full_table.attrs['first_trading_day'] = (
            earliest_date if earliest_date is not None else iNaT
        )

        full_table.attrs['first_row'] = first_row
        full_table.attrs['last_row'] = last_row
        full_table.attrs['calendar_offset'] = calendar_offset
        full_table.attrs['calendar_name'] = self._calendar.name
        full_table.attrs['start_session_ns'] = self._start_session.value
        full_table.attrs['end_session_ns'] = self._end_session.value
        full_table.flush()
        return full_table

    @expect_element(invalid_data_behavior={'warn', 'raise', 'ignore'})
    def to_ctable(self, raw_data, invalid_data_behavior):
        if isinstance(raw_data, ctable):
            # we already have a ctable so do nothing
            return raw_data

        winsorise_uint32(raw_data, invalid_data_behavior, 'volume', *CNOHLC)
        processed = (raw_data[list(CNOHLC)] * 1000).round().astype('uint32')
        dates = raw_data.index.values.astype('datetime64[s]')
        check_uint32_safe(dates.max().view(np.int64), 'day')
        processed['day'] = dates.astype('uint32')
        processed['volume'] = raw_data.volume.astype('uint32')
        return ctable.fromdataframe(processed)


class CNBcolzDailyBarReader(BcolzDailyBarReader):

    def __init__(self, table, read_all_threshold=3000):
        super(CNBcolzDailyBarReader, self).__init__(
            table,
            read_all_threshold=3000,
        )
