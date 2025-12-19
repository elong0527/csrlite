
import polars as pl
try:
    df = pl.read_parquet("data/adcm.parquet")
    for col in df.columns:
        print(col)
    print(df.head(5))
except Exception as e:
    print(e)
