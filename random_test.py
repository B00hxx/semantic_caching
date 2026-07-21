import pandas as pd
df = pd.read_csv("train.csv")
print(df.head())
print(df.loc[0]["question1"])
print(df.loc[0]["question2"])