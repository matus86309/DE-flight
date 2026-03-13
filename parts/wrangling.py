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

#cleaning 
flights = pd.read_sql_query("SELECT * FROM flights;", connect)

# missing values
print("Missing Vals")
print(flights.isna().sum().sort_values(ascending=False))
print()
# duplicates
dupl_cols = ["year", "month", "day", "carrier", "flight", "origin", "dest", "sched_dep_time"]
duplicates = flights[flights.duplicated(subset=dupl_cols, keep=False)].sort_values(dupl_cols)
print("Duplicates:", len(duplicates))
print(duplicates.head(5))

# convert hhmm format 
def hhmm_to_minutes(x):
    if pd.isna(x):
        return float("nan")
    x = int(x)
    hours = x // 100
    minutes = x % 100
    return hours * 60 + minutes

#datetime column with year/month/day + hhmm column
def add_datetime(df, hhmm_col, new_col):
    base_date = pd.to_datetime(df[["year", "month", "day"]])
    minutes = df[hhmm_col].apply(hhmm_to_minutes)
    df[new_col] = base_date + pd.to_timedelta(minutes, unit="m")
    return df

# convert all time columns to datetime
flights = add_datetime(flights, "sched_dep_time", "sched_dep_dt")
flights = add_datetime(flights, "dep_time", "dep_dt")
flights = add_datetime(flights, "sched_arr_time", "sched_arr_dt")
flights = add_datetime(flights, "arr_time", "arr_dt")

#overnight flights 
mask = flights["sched_arr_dt"] < flights["sched_dep_dt"]
flights.loc[mask, "sched_arr_dt"] = flights.loc[mask, "sched_arr_dt"] + pd.Timedelta(days=1)

mask = flights["arr_dt"] < flights["dep_dt"]
flights.loc[mask, "arr_dt"] = flights.loc[mask, "arr_dt"] + pd.Timedelta(days=1)

# check delays match the datetime 
def check_consistency(df):
    df["calc_dep_delay"] = (df["dep_dt"] - df["sched_dep_dt"]).dt.total_seconds() / 60
    df["calc_arr_delay"] = (df["arr_dt"] - df["sched_arr_dt"]).dt.total_seconds() / 60

    print("dep_delay match rate:", round((( df["dep_delay"] - df["calc_dep_delay"]).abs() <= 5).mean(), 3))
    print("arr_delay match rate:", round(((df["arr_delay"] - df["calc_arr_delay"]).abs() <= 5).mean(), 3))

check_consistency(flights) 

# timezone info for each airport
airports = pd.read_sql_query("SELECT faa, tzone FROM airports;", connect)

# merge destination timezone
flights = flights.merge(
    airports.rename(columns={"faa": "dest", "tzone": "dest_tz"}),
    on="dest",
    how="left"
)

# local arrival time at destination
flights["arr_local"] = None

for i in flights.index:
    if pd.isna(flights.at[i, "arr_dt"]) or pd.isna(flights.at[i, "dest_tz"]):
        continue

    arr_local = pd.Timestamp(flights.at[i, "arr_dt"]).tz_localize(
        flights.at[i, "dest_tz"],
        nonexistent="shift_forward",
        ambiguous="NaT"
    )

    flights.at[i, "arr_local"] = arr_local

print(flights[["origin", "dest", "arr_dt", "dest_tz", "arr_local"]].head(10))

flights.to_csv("flights_cleaned.csv", index=False)
connect.close()