"""Implementation independent definitions"""
from os import path as _path


class Period (dict):
    """
    Maps period marks often used in financial applications to implementation
    dependant format
    """
    # See numpy and pandas implementations for a target format

    marks: tuple = ("1m", "5m", "30m", "1h", "4h", "8h", "12h", "1d", "1w")

    # This class must be inherited
    def __init__(self):
        raise NotImplementedError


# Column names for tables
TS = "Timestamp"
PRICE = "Price"
OPEN = "Open"
HIGH = "High"
LOW = "Low"
CLOSE = "Close"
EMA = "EMA"


def csv_file_is_valid(func):
    def magic(filename: str, period: str, *args, **kwargs):
        # assert that given filename exist and has ".csv" extension
        assert _path.isfile(filename) and \
               _path.splitext(filename)[1] == ".csv", \
            f"{func.__name__}(): 'filename' must be *.csv file, " \
            f"{filename} given"

        # assert that given period is one of valid marks
        assert period in Period.marks, \
            f"{func.__name__}(): 'period' must be any of " \
            f"{list(Period.marks)}, \"{period}\" given"

        return func(filename, period, *args, **kwargs)
    return magic
