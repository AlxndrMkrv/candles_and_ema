"""
Numpy-based implemetation of candlesticks and EMA calculation over given
timestamp-price CSV-file
"""

import defs as _defs
import numpy as _np
from pandas import DataFrame as _DataFrame
from numpy.lib.recfunctions import merge_arrays as _merge_arrays
import os as _os
from datetime import datetime as _datetime
from copy import copy as _copy


class __Period (_defs.Period):
    __doc__ = _defs.Period.__doc__
    __doc__ += """ (seconds)"""

    def __init__(self):
        def calc_value(v: str):
            value, time_mark = int(v[:-1]), v[-1]
            return value * {'m': 60, 'h': 60*60,
                            'd': 24*60*60, 'w': 7*24*60*60}[time_mark]

        dict.__init__(self, {k: calc_value(k) for k in _defs.Period.marks})


Period = __Period()


def assert_table_is_valid(func):
    """
    Decorator that asserts that numpy.ndarray passed to 'func':
       1) is non-empty
       2) has at least 2 columns
       3) has timestamp column
       4) all columns contains numpy.int64 or numpy float64 data
    """
    def magic(tbl: _np.ndarray, *args, **kwargs):
        # assert that given table is numpy multidimensional array
        assert isinstance(tbl, _np.ndarray), \
            f"{func.__name__}(): 'tbl' must be numpy.ndarray, " \
            f"\"{type(tbl)}\" given"

        # assert that given table is not empty
        assert len(tbl), f"{func.__name__}(): 'tbl' must be non-empty"

        # assert that given table has at least 2 columns
        assert len(tbl.dtype) >= 2, \
            f"{func.__name__}(): 'tbl' must contain at least 2 columns, " \
            f"{len(tbl.dtype)} given"

        # assert that all column of given table is either int64 or float64
        # note: tbl.dtype is not iterable
        assert all(tbl.dtype[i] in (_np.int64, _np.float64)
                   for i in range(len(tbl.dtype))), \
            f"{func.__name__}(): 'tbl' columns must has either numpy.float64 " \
            f"or numpy.int64 type, " \
            f"{[tbl.dtype[i].name for i in range(len(tbl.dtype))]} given"

        # assert that first column of given table is timestamp
        assert tbl.dtype.names[0] == _defs.TS, \
            f"{func.__name__}(): 'tbl' first column must be named " \
            f"\"{_defs.TS}\" instead of \"{tbl.dtype.names[0]}\""

        return func(tbl, *args, **kwargs)
    return magic


@assert_table_is_valid
def convert_to_candlesticks(tbl: _np.ndarray, period: int = Period["5m"]):
    """
    Function calculates candlesticks for given timestamp-price table. It splits
     timestamps into given periods and then evaluates open, high, low and close
     prices over a period. If period contains no timestamps (price didn't
    change over the period) than close price of previous period will be used.

    Args:
        tbl (numpy.ndarray): structured array containing timestamp and price
                             columns
        period (int): candlestick duration in seconds

    Returns:
        structured numpy.ndarray with timestamps and open, high, low, close
        prices. Note that timestamps aligned to periods close prices.
    """

    # alias the function name
    me = f"{convert_to_candlesticks.__name__}()"

    # assert that given table contains price column
    assert _defs.PRICE in tbl.dtype.names, \
        f"{me}: 'tbl' must contain named column \"{_defs.PRICE}\""

    # assert that given period is integer
    assert isinstance(period, int), \
        f"{me}: 'period' must be integer, {type(period)} given"

    # round down first timestamp to given period to get start point
    start_timestamp = int(tbl[_defs.TS][0] // period * period)
    # round up last timestamp to given period to get end point
    end_timestamp = int(-(-tbl[_defs.TS][-1] // period * period))

    # generate timestamps from start+1 to end-1 and append last timestamp
    # from prices table to create last incomplete candle
    def ts_generator():
        yield from range(start_timestamp, end_timestamp, period)[1:]
        yield int(tbl[_defs.TS][-1])

    # initialize candlesticks structured array
    ohlc = _np.array([(0, _np.nan, _np.nan, _np.nan, _np.nan)
                      for _ in ts_generator()],
                     dtype=[(_defs.TS, int),
                            (_defs.OPEN, _np.float64),
                            (_defs.HIGH, _np.float64),
                            (_defs.LOW, _np.float64),
                            (_defs.CLOSE, _np.float64)])

    # find the price table slice that covers range from given index to
    # timestamp
    def get_slice(start_idx: int, timestamp: int) -> slice:
        # iterate from given index to the end of the price table until given
        # timestamp is exceeded
        for idx in range(start_idx, len(tbl)):
            if tbl[_defs.TS][idx] > timestamp:
                # return slice from start index to index that exceeds given
                # timestamp. This last index will become start index for next
                # period
                return slice(start_idx, idx)
        # return if loop reached the end of the price table
        return slice(start_idx, len(tbl))

    # iterate over periods timestamps and calculate OHLC values
    prev_idx = 0
    for i, ts in enumerate(ts_generator()):
        sl = get_slice(prev_idx, ts)
        prev_idx = sl.stop

        # copy previous close price if slice has zero width:
        # price hasn't changed during this period
        if sl.start == sl.stop:
            ohlc[i] = (ts,  # timestamp
                       ohlc[_defs.CLOSE][i-1],  # open
                       ohlc[_defs.CLOSE][i-1],  # high
                       ohlc[_defs.CLOSE][i-1],  # low
                       ohlc[_defs.CLOSE][i-1],  # close
                       )
        # calculate OHLC: open is the price at the slice start index,
        # close is the price at the previous to end index
        # high is maximal price in slice and low is minimal price in slice
        else:
            ohlc[i] = (ts,  # timestamp
                       tbl[_defs.PRICE][sl.start],  # open
                       tbl[_defs.PRICE][sl].max(),  # high
                       tbl[_defs.PRICE][sl].min(),  # low
                       tbl[_defs.PRICE][sl.stop - 1]  # close
                       )

    return ohlc


@assert_table_is_valid
def calculate_ema(tbl: _np.ndarray, length: int = 14) -> _np.ndarray:
    """
    Calculate EMA over close prices of given candlesticks table with given
    length

    Args:
        tbl (numpy.ndarray): structured array containing timestamps and close
                             prices
        length (int): integer constant to evaluate first-order IIR alpha value
                      with equation "2/(length + 1)"

    Returns:
        one-dimension numpy ndarray with calculated EMA values
    """

    # set alias for function name
    me = f"{calculate_ema.__name__}()"
    # assert that given EMA length is positive non-zero integer
    assert isinstance(length, int) and length > 0, \
        f"{me}: 'length' must be positive non-zero integer, {length} given"
    # assert that given table has 'close' column
    assert _defs.CLOSE in tbl.dtype.names, \
        f"{me}: 'tbl' must contain named column \"{_defs.CLOSE}\""

    # initialize EMA ndarray
    ema = _np.zeros(tbl.size, dtype=[(_defs.EMA, _np.float64)])

    # Convert given 'length' to IIR alpha value
    alpha = 2 / (length + 1)

    # Set EMA start value to the first close price to avoid transition process
    value = _copy(tbl[_defs.CLOSE][0])

    # Fill the column with EMA values
    for i, close_price in enumerate(tbl[_defs.CLOSE]):
        value += (close_price - value) * alpha  # first-order IIR equation
        ema[i] = value

    return ema


def process_csv_file(filename: str, period: str, length: int) -> _DataFrame:
    """
    Read given csv file into numpy structured array, convert prices to
     candlesticks with given period and then calculate EMA with given length
     over a candlesticks close prices.
    The function assumed to be called from outside

    Args:
        filename (str): path to csv-file containing timestamp-price pairs
        period (str): candlesticks duration, see :Period.marks: in defs.py
        length:

    Returns:
        pandas DataFrame with timestamps, candlestick prices and calculated EMA
    """
    # assert that given filename exist and has ".csv" extension
    assert _os.path.isfile(filename) and \
           _os.path.splitext(filename)[1] == ".csv", \
        f"{process_csv_file.__name__}(): 'filename' must be *.csv file, " \
        f"{filename} given"

    # assert that given period is one of valid marks
    assert period in _defs.Period.marks, \
        f"{process_csv_file.__name__}(): 'period' must be any of " \
        f"{list(_defs.Period.marks)}, \"{period}\" given"

    # function converts string datetime to timestamp
    def datetime2timestamp(s: str) -> float:
        return _datetime.fromisoformat(s).timestamp()

    # read prices from CSV file assuming that first column is datetime string
    # and second is prices
    prices = _np.genfromtxt(filename, delimiter=',', encoding="ascii",
                            skip_header=1, names=(_defs.TS, _defs.PRICE),
                            usecols=(0, 1),
                            converters={0: datetime2timestamp,
                                        1: _np.float64})

    # convert timestamp-price ndarray to candlesticks
    candles = convert_to_candlesticks(prices, Period[period])

    # create ema array from candlesticks
    ema = calculate_ema(candles, length)

    # merge candlesticks with ema in pandas DataFrame,
    # use numpy.datetime64 array of timestamps as index,
    # take OHLC and EMA as columns and return the result
    return _DataFrame(_merge_arrays((candles, ema), flatten=True),
                      index=_np.array(candles[_defs.TS],
                                      dtype="datetime64[s]"),
                      columns=[_defs.OPEN, _defs.HIGH, _defs.LOW, _defs.CLOSE,
                               _defs.EMA])
