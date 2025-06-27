import os
import re

SCHEMA_PATH = os.path.join("knowledge", "db_schema.sql")
OUTPUT_DIR = os.path.join("knowledge", "database")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Regex to match CREATE TABLE statements for public schema
table_regex = re.compile(r'(CREATE TABLE public\.([a-zA-Z0-9_]+) \([\s\S]+?\);)', re.MULTILINE)

def chunk_public_tables(schema_path, output_dir):
    with open(schema_path, 'r') as f:
        sql = f.read()

    matches = table_regex.findall(sql)
    for full_stmt, table_name in matches:
        out_path = os.path.join(output_dir, f"{table_name}.sql")
        with open(out_path, 'w') as out_f:
            out_f.write(full_stmt.strip() + '\n')
        print(f"Wrote {out_path}")

if __name__ == "__main__":
    chunk_public_tables(SCHEMA_PATH, OUTPUT_DIR) 