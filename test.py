"""Unit-test module"""

from typing import Iterable, Tuple
from random import randint
import pytest
import numpy as np

from numpy_implementation import calculate_ema as ema_numpy, \
    convert_to_candlesticks as ohlc_numpy, Period as Period_numpy
import defs


def get_ohlc_prices_and_reference(ticks_in_period: int = 4,
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

    assert isinstance(ticks_in_period, int), ticks_in_period >= 4
    assert isinstance(periods_number, int), periods_number > 5

    def interpolate_prices(o: int = randint(0, 100), h: int = randint(0, 100),
                           l: int = randint(0, 100), c: int = randint(0, 100)):
        """
        generate lineary interpolated prices for period with given ohlc values
        """
        return np.interp(range(ticks_in_period),
                         [round(i * (ticks_in_period - 1) / 3)
                          for i in range(4)],
                         [o, h, l, c])

    # temporary containers
    prices_table = np.zeros(0, dtype=[(defs.TS, int), (defs.PRICE, float)])
    ref_table = np.zeros(periods_number, dtype=[(defs.TS, int),
                                                (defs.OPEN, float),
                                                (defs.HIGH, float),
                                                (defs.LOW, float),
                                                (defs.CLOSE, float)])

    # iterate over periods to fill tables
    for period in range(periods_number):
        # timeline for the nth period aligned to the end of the period
        period_ticks = [period * ticks_in_period + tick + 1
                        for tick in range(ticks_in_period)]
        # use last periods second as timestamp for current candle
        ref_table[defs.TS][period] = period_ticks[-1]

        # calculations for non-skipped periods
        if period not in (1, 4):
            # get interpolated prices
            prices = interpolate_prices(10, 11, 5, 10) if period == 0 else \
                     interpolate_prices(25, 25, 20, 20) if period == 2 else \
                     interpolate_prices(30, 55, 16, 40) if period == 3 else \
                     interpolate_prices()

            # append period ticks and prices to prices_table
            prices_table = np.append(prices_table,
                                     np.array([*zip(period_ticks, prices)],
                                              dtype=[(defs.TS, int),
                                                     (defs.PRICE, float)]))

            # fill reference table with periods prices OHLC
            ref_table[defs.OPEN][period] = prices[0]
            ref_table[defs.HIGH][period] = prices.max()
            ref_table[defs.LOW][period] = prices.min()
            ref_table[defs.CLOSE][period] = prices[-1]
        # use last close value for skipped periods
        else:
            ref_table[defs.OPEN][period] = ref_table[defs.HIGH][period] = \
                ref_table[defs.LOW][period] = ref_table[defs.CLOSE][period] = \
                ref_table[defs.CLOSE][period - 1]

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
