
# This class is provided only to add docstring to dict
class __Period (dict):
    """Maps period marks adopted in trading platforms to Offset aliases using
    by pandas"""
    def __init__(self):
        '''dict.__init__(self, {"1m": "T", "5m": "5T", "30m": "30T",
                             "1h": "H", "5h": "5H", "8h": "8H", "12h": "12H",
                             "1d": "D", "1w": "1W"})'''

        dict.__init__(self, {"1m": 60, "5m": 5*60, "30m": 30*60, "1h": 1*3600})


Period = __Period()
