from zipline.utils.input_validation import preprocess
from zipline.utils.sqlite_utils import coerce_string_to_conn
import sqlite3
import six
import os
import errno
import numpy as np
from numpy import integer as any_integer

import pandas as pd
from zipline.utils.numpy_utils import (
    datetime64ns_dtype,
    float64_dtype,
    object_dtype,
    int64_dtype,
    bool_dtype,
    uint32_dtype,
    uint64_dtype,
    dtype,
)

SQLITE_FUNDAMENTALS_COLUMN_DTYPES = {
    'sid': any_integer,
    'ann_date': datetime64ns_dtype,
    'f_ann_date': datetime64ns_dtype,
    'end_date': object_dtype,
    'report_type': float64_dtype,
    'comp_type': float64_dtype,
    'update_flag': object_dtype,
    'total_share': float64_dtype,
    'cap_rese': float64_dtype,
}

SQLITE_FUNDAMENTAL_FACTORS_COLUMN_DTYPES = {
    'sid': any_integer,
    'date': datetime64ns_dtype,
    'value': float64_dtype,
}

SQLITE_FACTORS_VALUE_DTYPES = {
    int64_dtype,
    datetime64ns_dtype,
    bool_dtype,
    float64_dtype,
    object_dtype,
}


class SQLiteFundamentalsWriter(object):
    """
    Writer for data to be read by SQLiteFundamentalsReader

    Parameters
    ----------
    conn_or_path : str or sqlite3.Connection
        A handle to the target sqlite database.
    overwrite : bool, optional, default=False
        If True and conn_or_path is a string, remove any existing files at the
        given path before connecting.

    See Also
    --------
    zipline.data.us_equity_pricing.SQLiteFundamentalsReader
    """

    def __init__(self, conn_or_path, overwrite=False):
        if isinstance(conn_or_path, sqlite3.Connection):
            self.conn = conn_or_path
        elif isinstance(conn_or_path, six.string_types):
            if overwrite:
                try:
                    os.remove(conn_or_path)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
            self.conn = sqlite3.connect(conn_or_path)
            self.uri = conn_or_path
        else:
            raise TypeError("Unknown connection type %s" % type(conn_or_path))

    def write_factor(self, table=None, name=None):

        if table is None:
            return

        # df = table[fundamentals['name'] == name].copy()
        # df.drop('name', axis=1, inplace=True)
        table['date'] = table['date'].values.astype('datetime64[s]').astype(any_integer)

        if dtype(table['value']) in SQLITE_FACTORS_VALUE_DTYPES:
            table.to_sql(
                'fundamentals_%s' % name,
                self.conn,
                if_exists='append',
                chunksize=50000,
            )
        else:
            raise ValueError(
                "Unexpected frame columns:\n"
                "Expected Columns: %s\n"
                "Received Columns: %s" % (
                    set(SQLITE_FACTORS_VALUE_DTYPES),
                    dtype(table['value']),
                )
            )

    def write(self, fundamentals=None):
        """
        Writes data to a SQLite file to be read by SQLiteFundamentalsReader.

        Parameters
        ----------
        fundamentals : pandas.DataFrame, optional
            Dataframe containing fundamentals data. The format of this dataframe is:
              sid : int
                  The asset id associated with this fundamentals.
              date : datetime64
                  The date of the fundamental data
              name : string
                  A name of the fundamental
              value : float
                  A value of the fundamental
        """
        if fundamentals is None:
            return

        for name in fundamentals['name'].unique():
            df = fundamentals[fundamentals['name'] == name].copy()
            df.drop('name', axis=1, inplace=True)
            df['date'] = df['date'].values.astype('datetime64[s]').astype(any_integer)
            self._write(
                'fundamentals_%s' % name,
                SQLITE_FUNDAMENTAL_FACTORS_COLUMN_DTYPES,
                df,
            )

    def write_fundamentals(self, fundamentals):
        self._write(
            'fundamentals',
            SQLITE_FUNDAMENTALS_COLUMN_DTYPES,
            fundamentals,
        )

    def _write(self, tablename, expected_dtypes, frame):
        if frame is None or frame.empty:
            # keeping the dtypes correct for empty frames is not easy
            frame = pd.DataFrame(
                np.array([], dtype=list(expected_dtypes.items())),
            )
        else:
            if frozenset(frame.columns) != frozenset(six.viewkeys(expected_dtypes)):
                raise ValueError(
                    "Unexpected frame columns:\n"
                    "Expected Columns: %s\n"
                    "Received Columns: %s" % (
                        set(expected_dtypes),
                        frame.columns.tolist(),
                    )
                )

            actual_dtypes = frame.dtypes
            for colname, expected in six.iteritems(expected_dtypes):
                actual = actual_dtypes[colname]
                if not np.issubdtype(actual, expected):
                    raise TypeError(
                        "Expected data of type {expected} for column"
                        " '{colname}', but got '{actual}'.".format(
                            expected=expected,
                            colname=colname,
                            actual=actual,
                        ),
                    )

        frame.to_sql(
            tablename,
            self.conn,
            if_exists='append',
            chunksize=50000,
        )

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self):
        self.conn.close()


class SQLiteFundamentalsReader(object):
    """
    Loads fundamentals from a SQLite database.

    Expects data written in the format output by `SQLiteFundamentalsWriter`.

    Parameters
    ----------
    conn : str or sqlite3.Connection
        Connection from which to load data.

    See Also
    --------
    :class:`zipline.data.fundamentals.SQLiteFundamentalsWriter`
    """

    @preprocess(conn=coerce_string_to_conn(require_exists=True))
    def __init__(self, conn):
        self.conn = conn

    def read(self, name, dates, assets):

        start_dt64 = dates[0].to_datetime64().astype(any_integer) / 1000000000
        end_dt64 = dates[-1].to_datetime64().astype(any_integer) / 1000000000

        sql = 'SELECT sid, value, date FROM fundamentals_%s WHERE date < %s ORDER BY date' % (name, end_dt64)

        df = pd.read_sql_query(
            sql,
            self.conn,
            # index_col=['trading_date', 'code'],
            # parse_dates=['date'],
            # chunksize=500,
        )
        result = pd.DataFrame(index=dates, columns=assets)

        for asset in assets:
            df_sid = df[df['sid'] == asset].copy()

            # set start_date
            st_df = df_sid[df_sid['date'] < start_dt64]['date']
            start_date = st_df.iloc[-1] if st_df.any() else start_dt64

            df_sid = df_sid[df_sid['date'] >= start_date]
            if start_date < start_dt64:
                result[asset].loc[dates[0]] = df_sid['value'].iloc[0]

            for row in df_sid.iterrows():
                date, value = int(row[1]['date']), row[1]['value']
                if date >= end_dt64:
                    break
                dtime = np.datetime64(date, 's')
                if dtime in result.index:
                    result[asset].loc[dtime] = value

        return result.fillna(method='ffill')

    def read_fundamentals(self, names, dates, assets):
        name = names[0]

        start_date = dates[0].to_datetime()
        end_date = dates[-1].to_datetime()

        sql = '''SELECT sid, f_ann_date, end_date, %s From fundamentals''' % name

        df = pd.read_sql_query(
            sql,
            self.conn,
            # index_col=['trading_date', 'code'],
            parse_dates=['f_ann_date'],
            # chunksize=500,
        )

        df = df.sort_values(by="f_ann_date", ascending=True)

        result = pd.DataFrame(index=dates, columns=assets)

        for asset in assets:
            df_sid = df[df['sid'] == asset].copy()

            # set start_date
            st_df = df_sid[df_sid['f_ann_date'] < start_date]['f_ann_date']
            st_date = st_df.iloc[-1] if st_df.any() else start_date

            df_sid = df_sid[df_sid['f_ann_date'] >= st_date]
            st_date = st_date.tz_localize('utc')
            if st_date < start_date:
                result[asset].loc[dates[0]] = df_sid[name].iloc[0]

            for row in df_sid.iterrows():
                date, value = row[1]['f_ann_date'], row[1][name]
                date = date.tz_localize('utc')
                if date >= end_date:
                    break
                dtime = np.datetime64(date, 's')
                if dtime in result.index:
                    result[asset].loc[dtime] = value

        return result.fillna(method='ffill')
