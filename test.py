#import bcrypt
import pandas as pd
#password = input("Password: ").encode("utf-8")

#hashed = bcrypt.hashpw(
#    password,
#    bcrypt.gensalt(),
#)
#print(hashed.decode("utf-8"))


###############################
#-----------------------------#
###############################


df = pd.read_parquet("benchmark/datasets/lmsys-chat-1m/0000.parquet")

print(df.columns.tolist())
print(df.head())
print(df.shape)
#print(df["conversation"][0])
print(df.iloc[0]["conversation"])