import pandas as pd, numpy as np
df = pd.read_csv("data/processed/panel_merged.csv")
print("Columns:", list(df.columns)); print("Rows:", len(df))

def share(col, grp):
    gm = df.groupby(grp)[col].transform("mean")
    tot = df[col].var(ddof=0)
    within = ((df[col]-gm)**2).mean()
    between = ((gm-df[col].mean())**2).mean()
    print(f"\n{col}")
    print(f"  within share  : {within/tot*100:.1f}%")
    print(f"  between share : {between/tot*100:.1f}%")

c = list(df.columns)
g = lambda *n: next((x for x in c if any(k in x.lower() for k in n)), None)
region = g("region","loc","name")
pm     = g("pm25","pm2","exposure")
asthma = g("asthma","prev","rate","val")
print("Using:", region, pm, asthma)
share(asthma, region)
share(pm, region)
