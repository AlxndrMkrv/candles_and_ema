import numpy as _np
import os as _os
from datetime import datetime as _datetime
from copy import copy as _copy
from typing import Tuple as _Tuple

import numpy as np


class __Period (dict):
    """Maps period marks adopted in trading platforms to seconds"""
    def __init__(self):
        dict.__init__(self, {"1m": 60, "5m": 5*60, "30m": 30*60,
                             "1h": 3600, "5h": 5*3600, "8h": 8*3600,
                             "12h": 12*3600, "1d": 24*3600, "1w": 7*24*3600})


Period = __Period()


def assert_table_is_valid(func):
    """Decorator that asserts that numpy.ndarray passed to 'func' is a
    non-empty table with more than 2 columns containing numpy.float64 values.
    Also, the first column must be named "timestamp" """
    def magic(tbl: _np.ndarray, *args, **kwargs):
        assert isinstance(tbl, _np.ndarray), \
            f"{func.__name__}(): 'tbl' must be numpy.ndarray, " \
            f"\"{type(tbl)}\" given"
        assert len(tbl), f"{func.__name__}(): 'tbl' must be non-empty"
        assert len(tbl.dtype) >= 2, \
            f"{func.__name__}(): 'tbl' must contain at least 2 columns, " \
            f"{len(tbl.dtype)} given"
        assert all(dtype == _np.float64 for dtype in tbl.dtype), \
            f"{func.__name__}(): 'tbl' data must be of numpy.float64 type, " \
            f"{[t.name for t in tbl.dtype]} given"
        assert tbl.dtype.names[0] == "timestamp", \
            f"{func.__name__}(): 'tbl' first column must be named " \
            f"\"timestamp\" instead of \"{tbl.dtype.names[0]}\""
        return func(tbl, *args, **kwargs)
    return magic


@assert_table_is_valid
def convert_to_candlesticks(tbl: _np.ndarray, period: int = Period["5m"]):
    me = f"{convert_to_candlesticks.__name__}()"
    assert "price" in tbl.dtype.names, \
        f"{me}: 'tbl' must contain named column \"price\""
    assert isinstance(period, int), f"{me}: 'period' must be integer, " \
                                    f"{type(period)} given"

    # round down first timestamp to given period to get start point
    start_timestamp = int(tbl["timestamp"][0] // period * period)
    # round up last timestamp to given period to get end point
    end_timestamp = int(-(-tbl["timestamp"][-1] // period * period))

    # generate timestamps from start+1 to end-1 and append last timestamp
    # from prices table to create last incomplete candle
    def ts_generator():
        yield from range(start_timestamp, end_timestamp, period)[1:]
        yield int(tbl["timestamp"][-1])

    # initialize candlesticks structured array
    ohlc = _np.array([(0, _np.nan, _np.nan, _np.nan, _np.nan)
                      for _ in ts_generator()],
                     dtype=[("timestamp", int),
                            ("open", _np.float64),
                            ("high", _np.float64),
                            ("low", _np.float64),
                            ("close", _np.float64)])

    # find price table slice that covers range from given index to timestamp
    def get_slice(start_idx: int, timestamp: int) -> slice:
        for idx in range(start_idx, len(tbl)):
            if tbl["timestamp"][idx] > timestamp:
                return slice(start_idx, idx)
        return slice(start_idx, len(tbl))

    prev_idx = 0
    for i, ts in enumerate(ts_generator()):
        sl = get_slice(prev_idx, ts)
        prev_idx = sl.stop

        # fill candle with values from calculated slice of price table
        ohlc[i] = (ts,  # "timestamp"
                   tbl["price"][sl.start],  # "open"
                   tbl["price"][sl].max(),  # "high"
                   tbl["price"][sl].min(),  # "low"
                   tbl["price"][sl.stop-1]  # "close"
                   )

    return ohlc


@assert_table_is_valid
def calculate_ema(tbl: _np.ndarray, length: int = 14) -> _np.ndarray:
    me = f"{calculate_ema.__name__}()"
    assert isinstance(length, int) and 0 < length < tbl.size
    assert "close" in tbl.dtype.names, \
        f"{me}: 'tbl' must contain named column \"close\""

    # initialize EMA ndarray
    ema = _np.array([(0, _np.nan) for _ in range(len(tbl))],
                    dtype=[("timestamp", int),
                           ("EMA", _np.float64)])
    ema["timestamp"] = tbl["timestamp"]

    # Convert given 'length' to IIR alpha value
    alpha = 2 / (length + 1)

    # Set EMA value to the first Close price to avoid transition process
    value = _copy(tbl["close"][0])

    # Fill the column with EMA values
    for i, close_price in enumerate(tbl["close"]):
        value += (close_price - value) * alpha
        ema[i] = value

    return ema


def process_csv_file(filename: str, period: str, length: int):
    assert _os.path.isfile(filename) and \
           _os.path.splitext(filename)[1] == ".csv", \
        f"{process_csv_file.__name__}(): 'filename' must be *.csv file, " \
        f"{filename} given"
    assert isinstance(period, str) and period in Period.keys(), \
        f"{process_csv_file.__name__}(): 'period' must be any of " \
        f"{list(Period.keys())}, \"{period}\" given"

    def bytestring2timestamp(s: str):
        _datetime.fromisoformat(s).timestamp()

    prices = _np.genfromtxt(filename, delimiter=',', encoding="ascii",
                            usecols=(0, 1), names=("timestamp", "price"),
                            skip_header=1,
                            converters={0: bytestring2timestamp,
                                        1: _np.float64})
    candles = convert_to_candlesticks(prices, Period[period])
    ema = calculate_ema(candles, length)

