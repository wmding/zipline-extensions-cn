from zipline.data.data_portal import DataPortal
import pandas as pd

from zipline_extensions_cn.data.history_loader import (
    CNDailyHistoryLoader
)

import numpy as np
from numpy import float64, int64, nan
from pandas import isnull

from zipline.assets import (
    Asset,
    AssetConvertible,
    Equity,
    Future,
    PricingDataAssociable,
)
from zipline.assets.continuous_futures import ContinuousFuture
from zipline.data.continuous_future_reader import (
    ContinuousFutureSessionBarReader,
    ContinuousFutureMinuteBarReader
)
from zipline.assets.roll_finder import (
    CalendarRollFinder,
    VolumeRollFinder
)
from zipline.data.dispatch_bar_reader import (
    AssetDispatchMinuteBarReader,
    AssetDispatchSessionBarReader
)
from zipline.data.resample import (
    DailyHistoryAggregator,
    ReindexMinuteBarReader,
    ReindexSessionBarReader,
)
from zipline.data.history_loader import (
    MinuteHistoryLoader,
)

from zipline.data.bar_reader import NoDataOnDate

CNBASE_FIELDS = frozenset([
    "open",
    "high",
    "low",
    "close",
    "up_limit",
    "down_limit",
    "volume",
    "price",
    "contract",
    "sid",
    "last_traded",
])

CNOHLCV_FIELDS = frozenset([
    "open", "high", "low", "close", "volume", "up_limit", "down_limit"
])

CNOHLCVP_FIELDS = frozenset([
    "open", "high", "low", "close", "volume", "price", "up_limit", "down_limit"
])

HISTORY_FREQUENCIES = set(["1m", "1d"])

DEFAULT_MINUTE_HISTORY_PREFETCH = 1560
DEFAULT_DAILY_HISTORY_PREFETCH = 40

_DEF_M_HIST_PREFETCH = DEFAULT_MINUTE_HISTORY_PREFETCH
_DEF_D_HIST_PREFETCH = DEFAULT_DAILY_HISTORY_PREFETCH


class CNDataPortal(DataPortal):

    def __init__(self,
                 asset_finder,
                 trading_calendar,
                 first_trading_day,
                 equity_daily_reader=None,
                 equity_minute_reader=None,
                 future_daily_reader=None,
                 future_minute_reader=None,
                 adjustment_reader=None,
                 last_available_session=None,
                 last_available_minute=None,
                 minute_history_prefetch_length=_DEF_M_HIST_PREFETCH,
                 daily_history_prefetch_length=_DEF_D_HIST_PREFETCH
                 ):

        super(CNDataPortal, self).__init__(
            asset_finder,
            trading_calendar,
            first_trading_day,
        )

        self.trading_calendar = trading_calendar

        self.asset_finder = asset_finder

        self._adjustment_reader = adjustment_reader

        # caches of sid -> adjustment list
        self._splits_dict = {}
        self._mergers_dict = {}
        self._dividends_dict = {}

        # Handle extra sources, like Fetcher.
        self._augmented_sources_map = {}
        self._extra_source_df = None

        self._first_available_session = first_trading_day

        if last_available_session:
            self._last_available_session = last_available_session
        else:
            # Infer the last session from the provided readers.
            last_sessions = [
                reader.last_available_dt
                for reader in [equity_daily_reader, future_daily_reader]
                if reader is not None
            ]
            if last_sessions:
                self._last_available_session = min(last_sessions)
            else:
                self._last_available_session = None

        if last_available_minute:
            self._last_available_minute = last_available_minute
        else:
            # Infer the last minute from the provided readers.
            last_minutes = [
                reader.last_available_dt
                for reader in [equity_minute_reader, future_minute_reader]
                if reader is not None
            ]
            if last_minutes:
                self._last_available_minute = max(last_minutes)
            else:
                self._last_available_minute = None

        aligned_equity_minute_reader = self._ensure_reader_aligned(
            equity_minute_reader)
        aligned_equity_session_reader = self._ensure_reader_aligned(
            equity_daily_reader)
        aligned_future_minute_reader = self._ensure_reader_aligned(
            future_minute_reader)
        aligned_future_session_reader = self._ensure_reader_aligned(
            future_daily_reader)

        self._roll_finders = {
            'calendar': CalendarRollFinder(self.trading_calendar,
                                           self.asset_finder),
        }

        aligned_minute_readers = {}
        aligned_session_readers = {}

        if aligned_equity_minute_reader is not None:
            aligned_minute_readers[Equity] = aligned_equity_minute_reader
        if aligned_equity_session_reader is not None:
            aligned_session_readers[Equity] = aligned_equity_session_reader

        if aligned_future_minute_reader is not None:
            aligned_minute_readers[Future] = aligned_future_minute_reader
            aligned_minute_readers[ContinuousFuture] = \
                ContinuousFutureMinuteBarReader(
                    aligned_future_minute_reader,
                    self._roll_finders,
                )

        if aligned_future_session_reader is not None:
            aligned_session_readers[Future] = aligned_future_session_reader
            self._roll_finders['volume'] = VolumeRollFinder(
                self.trading_calendar,
                self.asset_finder,
                aligned_future_session_reader,
            )
            aligned_session_readers[ContinuousFuture] = \
                ContinuousFutureSessionBarReader(
                    aligned_future_session_reader,
                    self._roll_finders,
                )

        _dispatch_minute_reader = AssetDispatchMinuteBarReader(
            self.trading_calendar,
            self.asset_finder,
            aligned_minute_readers,
            self._last_available_minute,
        )

        _dispatch_session_reader = AssetDispatchSessionBarReader(
            self.trading_calendar,
            self.asset_finder,
            aligned_session_readers,
            self._last_available_session,
        )

        self._pricing_readers = {
            'minute': _dispatch_minute_reader,
            'daily': _dispatch_session_reader,
        }

        self._daily_aggregator = DailyHistoryAggregator(
            self.trading_calendar.schedule.market_open,
            _dispatch_minute_reader,
            self.trading_calendar
        )
        self._history_loader = CNDailyHistoryLoader(
            self.trading_calendar,
            _dispatch_session_reader,
            self._adjustment_reader,
            self.asset_finder,
            self._roll_finders,
            prefetch_length=daily_history_prefetch_length,
        )

        self._minute_history_loader = MinuteHistoryLoader(
            self.trading_calendar,
            _dispatch_minute_reader,
            self._adjustment_reader,
            self.asset_finder,
            self._roll_finders,
            prefetch_length=minute_history_prefetch_length,
        )

        self._first_trading_day = first_trading_day

        # Get the first trading minute
        self._first_trading_minute, _ = (
            self.trading_calendar.open_and_close_for_session(
                self._first_trading_day
            )
            if self._first_trading_day is not None else (None, None)
        )

        # Store the locs of the first day and first minute
        self._first_trading_day_loc = (
            self.trading_calendar.all_sessions.get_loc(self._first_trading_day)
            if self._first_trading_day is not None else None
        )

    @staticmethod
    def _is_extra_source(asset, field, map):
        """
        Internal method that determines if this asset/field combination
        represents a fetcher value or a regular OHLCVP lookup.
        """
        # If we have an extra source with a column called "price", only look
        # at it if it's on something like palladium and not AAPL (since our
        # own price data always wins when dealing with assets).

        return not (field in CNBASE_FIELDS and
                    (isinstance(asset, (Asset, ContinuousFuture))))

    def _get_single_asset_value(self,
                                session_label,
                                asset,
                                field,
                                dt,
                                data_frequency):
        if self._is_extra_source(
                asset, field, self._augmented_sources_map):
            return self._get_fetcher_value(asset, field, dt)

        if field not in CNBASE_FIELDS:
            raise KeyError("Invalid column: " + str(field))

        if dt < asset.start_date or \
                (data_frequency == "daily" and
                 session_label > asset.end_date) or \
                (data_frequency == "minute" and
                 session_label > asset.end_date):
            if field == "volume":
                return 0
            elif field == "contract":
                return None
            elif field != "last_traded":
                return np.NaN

        if data_frequency == "daily":
            if field == "contract":
                return self._get_current_contract(asset, session_label)
            else:
                return self._get_daily_spot_value(
                    asset, field, session_label,
                )
        else:
            if field == "last_traded":
                return self.get_last_traded_dt(asset, dt, 'minute')
            elif field == "price":
                return self._get_minute_spot_value(
                    asset, "close", dt, ffill=True,
                )
            elif field == "contract":
                return self._get_current_contract(asset, dt)
            else:
                return self._get_minute_spot_value(asset, field, dt)

    def get_history_window(self,
                           assets,
                           end_dt,
                           bar_count,
                           frequency,
                           field,
                           data_frequency,
                           ffill=True):
        """
        Public API method that returns a dataframe containing the requested
        history window.  Data is fully adjusted.

        Parameters
        ----------
        assets : list of zipline.data.Asset objects
            The assets whose data is desired.

        bar_count: int
            The number of bars desired.

        frequency: string
            "1d" or "1m"

        field: string
            The desired field of the asset.

        data_frequency: string
            The frequency of the data to query; i.e. whether the data is
            'daily' or 'minute' bars.

        ffill: boolean
            Forward-fill missing values. Only has effect if field
            is 'price'.

        Returns
        -------
        A dataframe containing the requested data.
        """
        if field not in CNOHLCVP_FIELDS and field != 'sid':
            raise ValueError("Invalid field: {0}".format(field))

        if bar_count < 1:
            raise ValueError(
                "bar_count must be >= 1, but got {}".format(bar_count)
            )

        if frequency == "1d":
            if field == "price":
                df = self._get_history_daily_window(assets, end_dt, bar_count,
                                                    "close", data_frequency)
            else:
                df = self._get_history_daily_window(assets, end_dt, bar_count,
                                                    field, data_frequency)
        elif frequency == "1m":
            if field == "price":
                df = self._get_history_minute_window(assets, end_dt, bar_count,
                                                     "close")
            else:
                df = self._get_history_minute_window(assets, end_dt, bar_count,
                                                     field)
        else:
            raise ValueError("Invalid frequency: {0}".format(frequency))

        # forward-fill price
        if field == "price":
            if frequency == "1m":
                ffill_data_frequency = 'minute'
            elif frequency == "1d":
                ffill_data_frequency = 'daily'
            else:
                raise Exception(
                    "Only 1d and 1m are supported for forward-filling.")

            assets_with_leading_nan = np.where(isnull(df.iloc[0]))[0]

            history_start, history_end = df.index[[0, -1]]
            if ffill_data_frequency == 'daily' and data_frequency == 'minute':
                # When we're looking for a daily value, but we haven't seen any
                # volume in today's minute bars yet, we need to use the
                # previous day's ffilled daily price. Using today's daily price
                # could yield a value from later today.
                history_start -= self.trading_calendar.day

            initial_values = []
            for asset in df.columns[assets_with_leading_nan]:
                last_traded = self.get_last_traded_dt(
                    asset,
                    history_start,
                    ffill_data_frequency,
                )
                if isnull(last_traded):
                    initial_values.append(nan)
                else:
                    initial_values.append(
                        self.get_adjusted_value(
                            asset,
                            field,
                            dt=last_traded,
                            perspective_dt=history_end,
                            data_frequency=ffill_data_frequency,
                        )
                    )

            # Set leading values for assets that were missing data, then ffill.
            df.iloc[0, assets_with_leading_nan] = np.array(
                initial_values,
                dtype=np.float64
            )
            df.fillna(method='ffill', inplace=True)

            # forward-filling will incorrectly produce values after the end of
            # an asset's lifetime, so write NaNs back over the asset's
            # end_date.
            normed_index = df.index.normalize()
            for asset in df.columns:
                if history_end >= asset.end_date:
                    # if the window extends past the asset's end date, set
                    # all post-end-date values to NaN in that asset's series
                    df.loc[normed_index > asset.end_date, asset] = nan
        return df

    def _get_daily_spot_value(self, asset, column, dt):
        reader = self._get_pricing_reader('daily')
        if column == "last_traded":
            last_traded_dt = reader.get_last_traded_dt(asset, dt)

            if isnull(last_traded_dt):
                return pd.NaT
            else:
                return last_traded_dt
        elif column in CNOHLCV_FIELDS:
            # don't forward fill
            try:
                return reader.get_value(asset, dt, column)
            except NoDataOnDate:
                return np.nan
        elif column == "price":
            found_dt = dt
            while True:
                try:
                    value = reader.get_value(
                        asset, found_dt, "close"
                    )
                    if not isnull(value):
                        if dt == found_dt:
                            return value
                        else:
                            # adjust if needed
                            return self.get_adjusted_value(
                                asset, column, found_dt, dt, "minute",
                                spot_value=value
                            )
                    else:
                        found_dt -= self.trading_calendar.day
                except NoDataOnDate:
                    return np.nan

    def contains(self, asset, field):
        return field in CNBASE_FIELDS or \
               (field in self._augmented_sources_map and
                asset in self._augmented_sources_map[field])
