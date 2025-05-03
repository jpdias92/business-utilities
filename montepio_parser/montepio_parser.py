import pandas as pd
import sys
import os

# === Check input arguments ===
if len(sys.argv) < 2:
    print("❌ Please provide the input file name as an argument.")
    print("Example: python montepio_parser.py yourfile.csv")
    sys.exit(1)

input_file = sys.argv[1]

# Generate output file name
name, ext = os.path.splitext(input_file)
output_file = f"{name}_cleaned.csv"

# === Encoding settings ===
encoding = 'windows-1252'  # Fix for Portuguese characters

# === Load the file ===
# Read as plain text because it's messy
with open(input_file, 'r', encoding=encoding) as f:
    lines = f.readlines()

# Find the header line
for idx, line in enumerate(lines):
    if 'DATA MOV.' in line and 'IMPORTÂNCIA' in line:
        header_index = idx
        break
else:
    raise ValueError("Header line not found!")

# Read the relevant part into a DataFrame
from io import StringIO

relevant_data = ''.join(lines[header_index:])

df = pd.read_csv(
    StringIO(relevant_data),
    sep='\t',  # Tab-separated file
    encoding=encoding
)

# === Select and clean columns ===
df_clean = df[['DATA MOV.', 'DESCRIÇÃO', 'IMPORTÂNCIA']].copy()

# Convert "DATA MOV." to date
df_clean['DATA MOV.'] = pd.to_datetime(df_clean['DATA MOV.'], errors='coerce', dayfirst=True)

# Clean and convert "IMPORTÂNCIA" to proper number
df_clean['IMPORTÂNCIA'] = (
    df_clean['IMPORTÂNCIA']
    .astype(str)
    .str.replace('.', '', regex=False)  # remove thousands separator
    .str.replace(',', '.', regex=False)  # replace decimal comma to dot for parsing
)
df_clean['IMPORTÂNCIA'] = pd.to_numeric(df_clean['IMPORTÂNCIA'], errors='coerce')

# Format IMPORTÂNCIA back to string with comma decimal
df_clean['IMPORTÂNCIA'] = df_clean['IMPORTÂNCIA'].map(lambda x: f"{x:,.2f}".replace(",", "").replace(".", ","))

# === Save clean output ===
df_clean.to_csv(output_file, index=False, encoding='utf-8-sig', sep=';')  # Use semicolon separator for better Excel support

print(f"✅ Clean file saved as '{output_file}'!")
