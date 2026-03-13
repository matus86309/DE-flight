import pandas as pd
import sqlite3

DB_PATH = "../data/flights_database.db"
connect = sqlite3.connect(DB_PATH)

#table names
tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;", connect)
print(tables)

#inspection
for table in tables["name"]:
    print(table)
    print(pd.read_sql_query("SELECT * FROM " + table + " LIMIT 6;", connect))
    print()