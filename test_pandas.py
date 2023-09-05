"""Pandas-based implementation test module"""

import pytest
import numpy as np

from pandas_implementation import calculate_ema, \
    convert_to_candlesticks, Period
from reference_generator import *
import defs


@pytest.mark.parametrize("period", [f"{randint(1, 100)}"
                                    f"{choice(['m', 'h', 'd', 'w'])}"
                                    for _ in range(100)])
def test_period_conversion(period: str):
    assert isinstance(Period_numpy[period], str)


@pytest.mark.parametrize("length", range(1, 100, 4))
def test_ema_calculation(length: int):
    """
    Pass generated square pulse to the function under test and compare
    its output with reference EMA values
    """
    ref_table = get_reference_ema(length)
    test_table = calculate_ema(ref_table, length)
    assert np.array_equal(test_table[defs.EMA], ref_table["reference"])


@pytest.mark.parametrize("period", defs.Period.marks)
def test_candlesticks(period: str):
    """
    Pass generated time series to the function under test and compare its output
     with reference OHLC values
    """
    prices_table, ref_table = get_ohlc_prices_and_reference(
        Period[period])
    test_table = convert_to_candlesticks(prices_table, Period[period])

    # assert equality of reference and test tables for listed columns
    for col in (defs.TS, defs.OPEN, defs.HIGH, defs.LOW, defs.CLOSE):
        assert np.array_equal(test_table[col], ref_table[col])
