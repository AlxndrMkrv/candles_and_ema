"""
Pandas-based implemetation of candlesticks and EMA calculation over given
timestamp-price CSV-file
"""

import pandas as _pd
from numpy import float64 as _float64
from copy import copy as _copy

import os as _os
from time import time as _time
from datetime import datetime
import defs as _defs


# This class is provided only to add docstring to dict
class __Period (_defs.Period):
    """Maps period marks adopted in trading platforms to Offset aliases using
    by pandas"""
    def __init__(self):
        def convert_mark(mark: str) -> str:
            return mark[:-1] + {'m': 'T', 'h': 'H', 'd': 'D', 'w': 'W'}[mark[-1]]
        dict.__init__(self, {k: convert_mark(k) for k in _defs.Period.marks})


Period = __Period()


def assert_dataframe_is_valid(func):
    """Decorator that asserts that dataframe passed to 'func' has datetime
    index and one or more numpy.float64 columns"""
    def magic(df: _pd.DataFrame, *args, **kwargs):
        assert isinstance(df, _pd.DataFrame), \
            f"{func.__name__}(): 'df' must be a pandas DataFrame, " \
            f"\"{type(df)}\" given"
        assert isinstance(df.index, _pd.DatetimeIndex), \
            f"{func.__name__}(): 'df' index must be a pandas " \
            f"{_pd.DatetimeIndex.__name__}, \"{type(df.index)}\" given"
        assert len(df.columns), f"{func.__name__}(): 'df' must have "
        assert all(df[col].dtype == _float64 for col in df.columns), \
            f"{func.__name__}(): 'df' must have single column of numpy " \
            f"float64 type"
        return func(df, *args, **kwargs)
    return magic


@assert_dataframe_is_valid
def convert_to_candlesticks(df: _pd.DataFrame, period: str) -> _pd.DataFrame:
    """The function splits given dataframe into given periods and calculates
    candlesticks (open, high, low, close) within

        Parameters:
            df (DataFrame): pandas DataFrame with prices indexed by pandas
                            DatetimeIndex
            period (str): period to calculate candlesticks. See defs.Period
                          values

        Returns:
            pandas DataFrame with "Open", "High", "Low", "Close" prices indexed
            by DatetimeIndex
    """
    me = f"{convert_to_candlesticks.__name__}()"
    assert len(df.columns) == 1, \
        f"{me}: given 'df' is ambiguous, please pass DataFrame with a single " \
        f"column containing prices"
    #assert isinstance(period, str) and period in _Period.values(), \
    #    f"{me}: 'period' must be any of [{list(_Period.values())}], " \
    #    f"{period} given"

    # round down first timestamp to given period to get start point
    #start_timestamp = int(df.index[0]//period * period)
    #end_timestamp = int(-(-df.index[-1]//period * period))

    #ohlc = _pd.DataFrame(index=range(start_timestamp, end_timestamp, period)[1:],
    #                     columns=columns, dtype=_float64)

    #open_idx = ohlc.columns.get_loc("Open")
    #high_idx = ohlc.columns.get_loc("High")
    #low_idx = ohlc.columns.get_loc("Low")
    #close_idx = ohlc.columns.get_loc("Close")

    # Create new dataframe
    ohlc = _pd.DataFrame(index=df.resample(period).sum().index[1:],
                         columns=[_defs.OPEN, _defs.HIGH,
                                  _defs.LOW, _defs.CLOSE], dtype=_float64)

    t0 = _time()
    for i, timestamp in enumerate(ohlc.index):
        #breakpoint()
        '''view = df[timestamp-period:timestamp]
        if not len(view):
            ohlc.iloc[i, open_idx] = ohlc.iloc[i, high_idx] = \
                ohlc.iloc[i, low_idx] = ohlc.iloc[i, close_idx] = \
                ohlc.iloc[i-1, close_idx]
        else:
            ohlc.iloc[i, open_idx] = view.iloc[0, 0]
            ohlc.iloc[i, high_idx] = max(view.iloc[:, 0])
            ohlc.iloc[i, low_idx] = min(view.iloc[:, 0])
            ohlc.iloc[i, close_idx] = view.iloc[-1, 0]'''

        '''sl = slice(timestamp-period, timestamp)
        if not len(df.iloc[sl]):
            ohlc.Open[i] = ohlc.High[i] = ohlc.Low[i] = ohlc.Close[i] = \
                ohlc.Close[i - 1]
        else:
            ohlc.Open[i] = df[sl].iloc[0, 0]
            ohlc.High[i] = df[sl].iloc[:, 0].max()
            ohlc.Low[i] = df[sl].iloc[:, 0].min()
            ohlc.Close[i] = df[sl].iloc[-1, 0]'''

        # set a slice from 'period' back in time to now
        view = df[timestamp-_pd.Timedelta(period):timestamp]
        # if chunk has no data then assign everything to the last close price
        #if not len(view):
        #    ohlc.Open[i] = ohlc.Close[i-1]

        if not len(view):
            ohlc.Open[i] = ohlc.High[i] = ohlc.Low[i] = ohlc.Close[i] = \
                ohlc.Close[i-1]
        #
        else:
            ohlc.Open[i] = view.iloc[0, 0]
            ohlc.High[i] = max(view.iloc[:, 0])
            ohlc.Low[i] = min(view.iloc[:, 0])
            ohlc.Close[i] = view.iloc[-1, 0]
    t1 = _time()
    print(f"Performance: {(t1 - t0)/len(df):.6f} seconds per line. {t1 - t0:.3f} totaly")

    return ohlc


@assert_dataframe_is_valid
def add_ema(df: _pd.DataFrame, length: int = 14) -> None:
    """Add new column "EMA<length>" to given DataFrame with Exponential moving
    average of given 'length' calculated over "Close" prices. If the column
    already present the function will replace its values

        Parameters:
            df (DataFrame): pandas DataFrame containing "Open", "High", "Low",
                            "Close" prices indexed by DatatimeIndex
            length (int): number of "observations" to calculate EMA.
                          Since EMA is a first order IIR filter, this number
                          will be just converted to alpha by the equation
                          "2/(length+1)"
    """

    # assert that dataframe is non-empty and given length is exclusively
    # between 0 and length of the dataframe
    me = f"{add_ema.__name__}()"
    assert len(df) > 0, f"{me}: 'df' must be non-empty"
    assert isinstance(length, int) and 0 < length < len(df), \
        f"{me}: 'observations' must be integer in range (0 .. {len(df)})"

    # convert given 'length' to IIR alpha value
    alpha = 2/(length+1)

    # set EMA value to the first Close price to avoid transition process
    value = _copy(df[_defs.CLOSE][0])

    # create empty column for EMA values
    df[_defs.EMA] = ''
    col_idx = df.columns.get_loc(_defs.EMA)

    # fill the column with EMA values
    for i, close_price in enumerate(df[_defs.CLOSE]):
        value += (close_price - value) * alpha
        df.loc[i, col_idx] = value


def process_csv_file(filename: str, period: str, length: int):
    assert _os.path.isfile(filename) and \
           _os.path.splitext(filename)[1] == ".csv", \
        f"{process_csv_file.__name__}(): 'filename' must be *.csv file, " \
        f"{filename} given"
    assert isinstance(period, str) and period in Period.keys(), \
        f"{process_csv_file.__name__}(): 'period' must be any of " \
        f"{list(Period.keys())}, \"{period}\" given"

    df = _pd.read_csv(filename, index_col=_defs.TS, parse_dates=True,
                      header=0, names=[_defs.TS, _defs.PRICE])

    # resample to OHLC
    table = df.resample(Period[period]).ohlc()

    # add EMA
    table[_defs.EMA] = _pd.Series.ewm(df[_defs.CLOSE], span=length).mean()

    return table

