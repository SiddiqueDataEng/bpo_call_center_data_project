import pandas as pd
from pathlib import Path
for f in sorted(Path("lakehouse/gold").glob("*.parquet")):
    df = pd.read_parquet(f)
    print(f"{f.stem}")
    print(f"  {list(df.columns)}")
