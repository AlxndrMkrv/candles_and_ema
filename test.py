"""Unit-test module"""

from typing import Iterable, Tuple
from random import randint
import pytest
import numpy as np

from numpy_implementation import calculate_ema as ema_numpy, \
    convert_to_candlesticks as ohlc_numpy, Period as Period_numpy
import defs


def get_ohlc_prices_and_reference(period: int = 4,
                                  periods_number: int = 10) \
        -> Tuple[np.ndarray, np.ndarray]:
    """
    Function returns timestamp-price dataset and reference ohlc with following
    rules:
       - period 0: open == close, high == open+1, low == open-5
       - period 1: skipped
       - period 2: open == close + 5, high == open, low == close
       - period 3: open == close - 10, high == close + 15, low == open - 14
       - period 4: skipped
       - other periods are random
    """

    assert isinstance(period, int), period >= 4
    assert isinstance(periods_number, int), periods_number > 5

    def interpolate_ohlc(o: int = randint(0, 100), h: int = randint(0, 100),
                         l: int = randint(0, 100), c: int = randint(0, 100)):
        """use numpy interpolation to generate linear price chart for period"""
        return np.interp(range(period),
                         [round(i * (period-1)/3) for i in range(4)],
                         [o, h, l, c])

    # temporary containers
    price_timestamps = []
    prices = []
    ohlc_timestamps = []
    opens, highs, lows, closes = [], [], [], []

    for n in range(periods_number):
        # timeline for the nth period aligned to the end of the period
        period_seconds = [n*period + i + 1 for i in range(period)]
        # use last periods second as timestamp for current candle
        ohlc_timestamps.append(period_seconds[-1])

        # calculations for non-skipped periods
        if n not in (1, 4):
            price_timestamps += period_seconds
            ohlc = interpolate_ohlc(10, 11, 5, 10) if n == 0 else \
                   interpolate_ohlc(25, 25, 20, 20) if n == 2 else \
                   interpolate_ohlc(30, 55, 16, 40) if n == 3 else \
                   interpolate_ohlc()
            prices += list(ohlc)

            opens.append(ohlc[0])
            highs.append(ohlc.max())
            lows.append(ohlc.min())
            closes.append(ohlc[-1])
        # use last close value for skipped periods
        else:
            opens.append(closes[-1])
            highs.append(closes[-1])
            lows.append(closes[-1])
            closes.append(closes[-1])

    # create timestamp-price table from previously calculated values
    prices_table = np.array([(price_timestamps[i], p)
                             for i, p in enumerate(prices)],
                            dtype=[(defs.TS, int),
                                   (defs.PRICE, np.float64)])

    # create timestamp-OHLC table from previously calculated values
    ref_table = np.array([(ts, opens[i], highs[i], lows[i], closes[i])
                          for i, ts in enumerate(ohlc_timestamps)],
                         dtype=[(defs.TS, int),
                                (defs.OPEN, np.float64),
                                (defs.HIGH, np.float64),
                                (defs.LOW, np.float64),
                                (defs.CLOSE, np.float64)])

    return prices_table, ref_table


def get_reference_ema(n: int, amplitude: int = 1000000,
                      dataset_width: int = 2000) -> np.ndarray:
    """Function returns single square pulse with reference EMA"""

    assert isinstance(amplitude, int) and amplitude > 1
    assert isinstance(dataset_width, int) and dataset_width > 100

    def ema_generator(iterable: Iterable):
        """Generator yielding EMA<n> value for given iterable."""
        smooth = 2 / (n + 1)
        iterator = iter(iterable)
        value = next(iterator)
        yield value
        for v in iterator:
            value += smooth * (v - value)
            yield value

    # create square pulse
    pulse_width = dataset_width // 2
    pulse = [0] + [amplitude] * pulse_width + \
            [0] * (dataset_width - pulse_width - 1)

    # return structured array
    return np.array([(i, pulse[i], v)
                     for i, v in enumerate(ema_generator(pulse))],
                    dtype=[(defs.TS, int),
                           (defs.CLOSE, np.float64),
                           ("reference", np.float64)])


@pytest.mark.parametrize("length", range(1, 100, 4))
def test_numpy_ema_calculation(length: int):
    """
    Pass generated square pulse to the function under test and compare
    its output with reference EMA values
    """
    ref_table = get_reference_ema(length)
    test_table = ema_numpy(ref_table, length)
    assert np.array_equal(test_table[defs.EMA], ref_table["reference"])


@pytest.mark.parametrize("period", defs.Period.marks)
def test_numpy_candlesticks(period: str):
    """
    Pass generated time series to the function under test and compare its output
     with reference OHLC values
    """
    prices_table, ref_table = get_ohlc_prices_and_reference(Period_numpy[period])
    test_table = ohlc_numpy(prices_table, Period_numpy[period])

    # assert equality of reference and test tables for listed columns
    for col in (defs.TS, defs.OPEN, defs.HIGH, defs.LOW, defs.CLOSE):
        assert np.array_equal(test_table[col], ref_table[col])
