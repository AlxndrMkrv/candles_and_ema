# candles_for_amacryteam
Test assignment for a vacancy Middle-Level Python Developer


Notes
-----

Pandas DataFrames looks veeeeeery slow. Given "df" has single row of 100k np.float64 elements, `timeit("max(df)", number=10000)` takes 0.014 seconds to run but `timeit("df.max()", number=10000)` takes 3 (sic!). `timeit("len(df)", number=10000)` takes 0.01 second but `timeit("df.size", number=10000)` somehow takes 0.12...


