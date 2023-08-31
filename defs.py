"""Implementation independent definitions"""


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
