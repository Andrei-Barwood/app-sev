import pandas as pd
import numpy as np

# Create dummy data
data = "1;154,6\n1,5;168,4\n2;170,8"
with open("test.csv", "w") as f:
    f.write(data)

df_upload = pd.read_csv("test.csv", sep=';')

valid_cols = []
for col in df_upload.columns:
    print(f"Col: {col}")
    temp_col = pd.to_numeric(df_upload[col].astype(str).str.replace(',', '.'), errors='coerce')
    print(f"Not NA: {temp_col.notna().sum()}")
    if temp_col.notna().sum() > 0:
        valid_cols.append(col)
    if len(valid_cols) == 2:
        break

print(f"Valid cols: {valid_cols}")
col1, col2 = valid_cols[0], valid_cols[1]
df_upload[col1] = pd.to_numeric(df_upload[col1].astype(str).str.replace(',', '.'), errors='coerce')
df_upload[col2] = pd.to_numeric(df_upload[col2].astype(str).str.replace(',', '.'), errors='coerce')
df_upload = df_upload.dropna(subset=[col1, col2])
print("Len after dropna:", len(df_upload))
