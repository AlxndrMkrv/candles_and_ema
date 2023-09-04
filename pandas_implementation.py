import defs as _defs
import pandas as _pd
import os as _os
import numpy as _np


class __Period (_defs.Period):
    """
    Maps period marks adopted in trading platforms to Offset aliases using by
    pandas
    """
    def __init__(self):
        def convert_mark(mark: str) -> str:
            # rename 'm' (minutes) mark to 'T'. Leave
            return mark[:-1] + 'T' if mark[-1].lower() == 'm' else mark.upper()

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
        assert len(df.columns), f"{func.__name__}(): 'df' must be non-empty"
        assert all(df[col].dtype == _np.float64 for col in df.columns), \
            f"{func.__name__}(): 'df' must have single column of numpy " \
            f"float64 type"
        return func(df, *args, **kwargs)
    return magic


class _PeriodAggregator:
    """
    Aggregator class that calculates OHLC values for given pandas.Series.
    Returns Close value of previous period if series is empty
    """
    def __init__(self, prev_close: float):
        self.__prev_close = prev_close

    def handle_series(self, series: _pd.Series):
        # calculate OHLC values if given series has elements
        if len(series):
            self.__prev_close = series[_defs.PRICE][-1]
            return _pd.Series({_defs.OPEN: series[_defs.PRICE][0],
                               _defs.LOW: min(series[_defs.PRICE]),
                               _defs.HIGH: max(series[_defs.PRICE]),
                               _defs.CLOSE: series[_defs.PRICE][-1]})
        # return previous Close value if series is empty
        else:
            return _pd.Series({_defs.OPEN: self.__prev_close,
                               _defs.LOW: self.__prev_close,
                               _defs.HIGH: self.__prev_close,
                               _defs.CLOSE: self.__prev_close})


@assert_dataframe_is_valid
def convert_to_candlesticks(df: _pd.DataFrame,
                            period: str = Period["5m"]) -> _pd.DataFrame:
    # assert given dataframe has "Price" column
    assert _defs.PRICE in df.columns, \
        f"{convert_to_candlesticks.__name__}(): 'df' must contain " \
        f"{_defs.PRICE} column to calculate candlesticks"

    # use the custom aggregator to resample Timestamp-Price dataframe to OHLC
    # with given period and avoid NaN values
    pa = _PeriodAggregator(df[_defs.PRICE][0])
    return df.resample(period).aggregate(pa.handle_series)


@assert_dataframe_is_valid
def calculate_ema(df: _pd.DataFrame, length: int = 14) -> _pd.DataFrame:
    return _pd.Series.ewm(df[_defs.CLOSE], span=length).mean()


@_defs.csv_file_is_valid
def process_csv_file(filename: str, period: str, length: int) -> _pd.DataFrame:
    """
    Read given csv file into pandas DataFrame, convert prices to candlesticks
     with given period and then calculate EMA with given length over a
     candlesticks close prices.
    The function assumed to be called from outside

    Args:
        filename (str): path to csv-file containing timestamp-price pairs
        period (str): candlesticks duration, see :Period.marks: in defs.py
        length (int): number of observations to calculate EMA

    Returns:
        pandas DataFrame with timestamps, candlestick prices and calculated EMA
    """

    # read prices from CSV file. Ignore csv header in favor of project-wide
    # column names
    prices = _pd.read_csv(filename, index_col=_defs.TS, parse_dates=True,
                          header=0, names=[_defs.TS, _defs.PRICE])

    # calculate candlesticks
    ohlc = convert_to_candlesticks(prices, Period[period])

    # calculate EMA and add new column to candlesticks
    ohlc["EMA"] = calculate_ema(ohlc, length)

    # return everything
    return ohlc
