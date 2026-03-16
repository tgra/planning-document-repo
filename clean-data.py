import pandas as pd

df = pd.read_csv("planning_data.csv")

# remove duplicates
df = df.drop_duplicates(subset=["Reference"])

# convert dates
df["Application Received"] = pd.to_datetime(df["Application Received"], errors="coerce")
df["Decision Issued Date"] = pd.to_datetime(df["Decision Issued Date"], errors="coerce")

df.to_csv("planning_clean.csv", index=False)

print(len(df))