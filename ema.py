from pandas import DataFrame as _DataFrame


def ema(df: _DataFrame, observations: int = 14):
    assert isinstance(df, _DataFrame), \
        f"{ema.__name__}(): 'df' must be a pandas DataFrame, " \
        f"\"{type(df)}\" given"
    assert isinstance(observations, int) and 0 < observations < len(df), \
        f"{ema.__name__}(): 'observations' must be integer in range " \
        f"(0 .. {len(df)})"

    rate = 2/(observations+1)
