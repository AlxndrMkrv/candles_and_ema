"""Numpy-based implementation test module"""

import pytest
import numpy as np
from random import randint, choice

from numpy_implementation import calculate_ema as ema_numpy, \
    convert_to_candlesticks as ohlc_numpy, Period as Period_numpy
from reference_generator import *
import defs


@pytest.mark.parametrize("period", [f"{randint(1, 100)}"
                                    f"{choice(['m', 'h', 'd', 'w'])}"
                                    for _ in range(100)])
def test_period_conversion(period: str):
    seconds = int(period[:-1]) * (60 if period[-1] == 'm' else
                                  60*60 if period[-1] == 'h' else
                                  24*60*60 if period[-1] == 'd' else
                                  7*24*60*60 if period[-1] == 'w' else
                                  0)
    test_period = Period_numpy[period]
    assert isinstance(test_period, int)
    assert test_period == seconds


@pytest.mark.parametrize("length", range(1, 100, 4))
def test_ema_calculation(length: int):
    """
    Pass generated square pulse to the function under test and compare
    its output with reference EMA values
    """
    ref_table = get_reference_ema(length)
    test_table = ema_numpy(ref_table, length)
    assert np.array_equal(test_table[defs.EMA], ref_table["reference"])


@pytest.mark.parametrize("period", defs.Period.marks)
def test_candlesticks(period: str):
    """
    Pass generated time series to the function under test and compare its output
     with reference OHLC values
    """
    prices_table, ref_table = get_ohlc_prices_and_reference(Period_numpy[period])
    test_table = ohlc_numpy(prices_table, Period_numpy[period])

    # assert equality of reference and test tables for listed columns
    for col in (defs.TS, defs.OPEN, defs.HIGH, defs.LOW, defs.CLOSE):
        assert np.array_equal(test_table[col], ref_table[col])
