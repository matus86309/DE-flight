import os
import sqlite3
import math
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from scipy.stats import linregress
from scipy.stats import ttest_ind

DB_PATH = os.path.join(os.path.dirname(__file__), "./data/flights_database.db")
connection = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = connection.cursor()

# JFK coordinates used as NYC origin for bearing/inner-product calculations
JFK_LAT = 40.6413
JFK_LON = -73.7781


def _bearing_vec(lat1, lon1, lat2, lon2):
    """Vectorised version of _bearing that works on numpy arrays."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = np.sin(dlon) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
    return np.degrees(np.arctan2(x, y)) % 360


def _to_cardinal(bearing_deg):
    if bearing_deg > 315 or bearing_deg <= 45:
        return "North"
    elif bearing_deg <= 135:
        return "East"
    elif bearing_deg <= 225:
        return "South"
    else:
        return "West"


# ── Cached Data Retrieval Functions ───────────────────────────────────────────
@st.cache_data
def get_distinct_origins():
    """Returns cached list of distinct origin airports, sorted."""
    return pd.read_sql("SELECT DISTINCT origin FROM flights ORDER BY origin;", connection)["origin"].tolist()


@st.cache_data
def get_distinct_destinations():
    """Returns cached list of distinct destination airports, sorted."""
    return pd.read_sql("SELECT DISTINCT dest FROM flights ORDER BY dest;", connection)["dest"].tolist()


def _build_flight_filters(origin=None, dest=None, date_start=None, date_end=None, month_start=None, month_end=None):
    """Build SQL WHERE clause and params for reusable flight filters."""
    filters = []
    params = []

    if origin:
        filters.append("origin = ?")
        params.append(origin)

    if dest:
        filters.append("dest = ?")
        params.append(dest)

    if date_start:
        filters.append("date(printf('%04d-%02d-%02d', year, month, day)) >= date(?)")
        params.append(date_start)

    if date_end:
        filters.append("date(printf('%04d-%02d-%02d', year, month, day)) <= date(?)")
        params.append(date_end)

    if month_start and month_end:
        filters.append("month BETWEEN ? AND ?")
        params.extend([month_start, month_end])

    where_clause = " AND ".join(filters) if filters else "1=1"
    return where_clause, params


def get_filtered_flight_metrics(origin=None, month_start=None, month_end=None):
    """
    Returns filtered flight metrics for a given origin and month range.
    Args:
        origin: Origin airport code (e.g., 'JFK'), or None for all
        month_start: Starting month (1-12), or None for all
        month_end: Ending month (1-12), or None for all
    """
    where_clause, params = _build_flight_filters(
        origin=origin,
        month_start=month_start,
        month_end=month_end,
    )
    
    query = f"""
    SELECT 
        (SELECT COUNT(*) FROM flights WHERE {where_clause}) AS total_flights,
        (SELECT COUNT(DISTINCT dest) FROM flights WHERE {where_clause}) AS unique_destinations,
        (SELECT COUNT(DISTINCT carrier) FROM flights WHERE {where_clause}) AS total_airlines
    """
    result = pd.read_sql(query, connection, params=params + params + params).iloc[0]
    return {
        'total_flights': int(result[0]),
        'unique_destinations': int(result[1]),
        'total_airlines': int(result[2])
    }


def get_filtered_overview_metrics(origin=None, dest=None, date_start=None, date_end=None):
    """Returns overview metrics filtered by origin, destination and date range."""
    where_clause, params = _build_flight_filters(
        origin=origin,
        dest=dest,
        date_start=date_start,
        date_end=date_end,
    )

    query = f"""
    SELECT
        COUNT(*) AS total_flights,
        COUNT(DISTINCT dest) AS unique_destinations,
        COUNT(DISTINCT carrier) AS total_airlines
    FROM flights
    WHERE {where_clause}
    """
    result = pd.read_sql(query, connection, params=params).iloc[0]
    return {
        "total_flights": int(result["total_flights"]),
        "unique_destinations": int(result["unique_destinations"]),
        "total_airlines": int(result["total_airlines"]),
    }


@st.cache_data
def get_incoming_airport_info():

    #get unique incoming airports
    query_a = 'SELECT DISTINCT origin FROM flights;'
    cursor.execute(query_a)
    incoming_airport_list = cursor.fetchall()
    incoming_airport_list = [i[0] for i in incoming_airport_list]

    #get all info for unique airports
    rows = []
    for airport in incoming_airport_list:
        query_b = f"SELECT * from airports WHERE faa = '{airport}';"
        cursor.execute(query_b)
        rows.extend(cursor.fetchall())

    origin_airport_df = pd.DataFrame(rows,columns=[x[0] for x in cursor.description])

    return origin_airport_df

@st.cache_data
def get_daily_inbound_log(day, month, dest=None):
    """
    Returns outbound flights for the given day/month.
    """
    origin_filter = f"AND destination = '{dest}'" if dest else "AND destination ='JFK' or destination ='LGA' or destination ='EWR'"
    query = f"SELECT DISTINCT origin, dest as destination, carrier, flight FROM flights WHERE day = '{day}' AND month = '{month}' {origin_filter};"
    cursor.execute(query)
    rows = cursor.fetchall()
    daily_inbound_log = pd.DataFrame(rows, columns=[x[0] for x in cursor.description])
    return daily_inbound_log



def get_daily_outbound_log(day, month, origin=None):
    """
    Returns outbound flights for the given day/month.
    """
    origin_filter = f"AND origin = '{origin}'" if origin else ""
    query = f"SELECT DISTINCT origin, dest as destination, carrier, flight FROM flights WHERE day = '{day}' AND month = '{month}' {origin_filter};"
    cursor.execute(query)
    rows = cursor.fetchall()
    daily_outbound_log = pd.DataFrame(rows, columns=[x[0] for x in cursor.description])
    return daily_outbound_log



@st.cache_data
def get_daily_statistics(day, month, origin=None):
    '''
    Create a daily briefing DataFrame for the selected day and month.
    '''
    origin_filter = f"AND origin = '{origin}'" if origin else ""

    # number of distinct flights
    cursor.execute(f"SELECT COUNT(flight) FROM flights WHERE day = '{day}' AND month = '{month}' {origin_filter};")
    num_flight = cursor.fetchone()[0]

    #number of unique destinations
    cursor.execute(f"SELECT COUNT(DISTINCT dest) FROM flights WHERE day = '{day}' AND month = '{month}' {origin_filter};")
    num_unique_destinations = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT dest FROM flights WHERE day = '{day}' AND month = '{month}' {origin_filter} "
        f"GROUP BY dest ORDER BY COUNT(dest) DESC LIMIT 1;"
    )
    most_visited = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT dest FROM flights WHERE day = '{day}' AND month = '{month}' {origin_filter} "
        f"GROUP BY dest ORDER BY COUNT(dest) ASC LIMIT 1;"
    )
    least_visited = cursor.fetchone()[0]

    #calculate average business (scoped to same origin if provided)
    cursor.execute(f"SELECT COUNT(*) FROM flights WHERE 1=1 {origin_filter};")
    total_flights = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(DISTINCT month || '-' || day) FROM flights WHERE 1=1 {origin_filter};")
    num_days = cursor.fetchone()[0]

    average_business = total_flights / num_days
    business_today = num_flight - average_business
    difference_percentage = (business_today/average_business)*100

    df_structure = {"Flights Today": [num_flight],
                    "Avg Flights/Day": [round(average_business, 1)],
                    "Difference": [f"{difference_percentage:+.1f}%"],
                    "Unique Destinations": [num_unique_destinations],
                    "Most Visited": [most_visited],
                    "Least Visited": [least_visited],}

    return pd.DataFrame(df_structure)


@st.cache_data
def get_flight_trajectory(departing_airport, arriving_airport):
    """Get aircraft type distribution for flights between two airports.
    Either airport can be None to show all origins/destinations."""
    filters = []
    if departing_airport:
        filters.append(f"flights.origin = '{departing_airport}'")
    if arriving_airport:
        filters.append(f"flights.dest = '{arriving_airport}'")
    
    where_clause = " AND ".join(filters) if filters else "1=1"
    
    query = f"""
            SELECT planes.type, COUNT(*) AS count
            FROM flights
            JOIN planes ON flights.tailnum = planes.tailnum
            WHERE {where_clause}
            GROUP BY planes.type
            ORDER BY count DESC"""

    cursor.execute(query)
    type_distribution = dict(cursor.fetchall())
    return type_distribution


@st.cache_data
def get_carrier_delay(origin=None, dest=None, date_start=None, date_end=None):
    """
    Returns a DataFrame with average departure delay per airline.
    Displays a barplot with full airline names on the (rotated) x-axis.
    """
    where_clause, params = _build_flight_filters(
        origin=origin,
        dest=dest,
        date_start=date_start,
        date_end=date_end,
    )

    query = f"""
        SELECT airlines.name, AVG(flights.dep_delay) AS avg_delay
        FROM flights
        JOIN airlines ON flights.carrier = airlines.carrier
        WHERE flights.dep_delay IS NOT NULL AND {where_clause}
        GROUP BY airlines.name
        ORDER BY avg_delay DESC;
    """
    delay_df = pd.read_sql(query, connection, params=params)

    return delay_df


@st.cache_data
def get_airline_frequency(origin=None, dest=None, date_start=None, date_end=None):
    """Returns airline frequency and average delay for the selected filters."""
    where_clause, params = _build_flight_filters(
        origin=origin,
        dest=dest,
        date_start=date_start,
        date_end=date_end,
    )

    query = f"""
        SELECT
            a.name AS airline,
            COUNT(*) AS total_flights,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS flight_share_pct,
            ROUND(AVG(f.dep_delay), 2) AS avg_dep_delay
        FROM flights f
        JOIN airlines a ON f.carrier = a.carrier
        WHERE {where_clause}
        GROUP BY a.name
        ORDER BY total_flights DESC;
    """
    return pd.read_sql(query, connection, params=params)


def get_filtered_flights_page(
    origin=None,
    dest=None,
    date_start=None,
    date_end=None,
    search_term=None,
    sort_by="flight_date",
    sort_order="DESC",
    page=1,
    page_size=25,
):
    """Returns one page of filtered flights plus total rows for pagination."""
    where_clause, params = _build_flight_filters(
        origin=origin,
        dest=dest,
        date_start=date_start,
        date_end=date_end,
    )

    search_clause = ""
    if search_term:
        search_clause = """
            AND (
                f.origin LIKE ? OR
                f.dest LIKE ? OR
                f.carrier LIKE ? OR
                CAST(f.flight AS TEXT) LIKE ? OR
                f.tailnum LIKE ? OR
                a.name LIKE ?
            )
        """
        like_term = f"%{search_term}%"
        params.extend([like_term, like_term, like_term, like_term, like_term, like_term])

    allowed_sort_cols = {
        "flight_date": "flight_date",
        "origin": "f.origin",
        "destination": "f.dest",
        "airline": "a.name",
        "carrier": "f.carrier",
        "flight": "f.flight",
        "dep_delay": "f.dep_delay",
        "arr_delay": "f.arr_delay",
        "distance": "f.distance",
    }
    sort_expr = allowed_sort_cols.get(sort_by, "flight_date")
    sort_dir = "ASC" if str(sort_order).upper() == "ASC" else "DESC"

    count_query = f"""
        SELECT COUNT(*) AS total_rows
        FROM flights f
        LEFT JOIN airlines a ON f.carrier = a.carrier
        WHERE {where_clause}
        {search_clause}
    """
    total_rows = int(pd.read_sql(count_query, connection, params=params).iloc[0]["total_rows"])

    offset = max(page - 1, 0) * page_size
    page_query = f"""
        SELECT
            date(printf('%04d-%02d-%02d', f.year, f.month, f.day)) AS flight_date,
            f.origin,
            f.dest AS destination,
            f.carrier,
            a.name AS airline,
            f.flight,
            f.tailnum,
            ROUND(f.dep_delay, 1) AS dep_delay,
            ROUND(f.arr_delay, 1) AS arr_delay,
            ROUND(f.distance, 1) AS distance,
            ROUND(f.air_time, 1) AS air_time
        FROM flights f
        LEFT JOIN airlines a ON f.carrier = a.carrier
        WHERE {where_clause}
        {search_clause}
        ORDER BY {sort_expr} {sort_dir}
        LIMIT ? OFFSET ?
    """
    page_params = params + [page_size, offset]
    page_df = pd.read_sql(page_query, connection, params=page_params)
    return page_df, total_rows


def get_delayed_flight(month_range:list[str],destinations_list:list[str]):
    #only use it with 'JFK'/'LAX' SQL ready format !

    #count the number of delayed flights in a given period
    cursor.execute(f"""SELECT COUNT(*) 
                   FROM flights 
                   WHERE arr_delay > 0 
                    AND month IN {month_range} 
                    AND dest IN {destinations_list};""")

    num_delays = cursor.fetchone()[0]
    return num_delays



@st.cache_data
def get_top_manufacturers(destination_airport=None, origin_airport=None):
    """Return top 5 plane manufacturers. Either airport can be None for all."""
    filters = []
    if destination_airport:
        filters.append(f"flights.dest = '{destination_airport}'")
    if origin_airport:
        filters.append(f"flights.origin = '{origin_airport}'")
    
    where_clause = " AND ".join(filters) if filters else "1=1"

    query = f"""
            SELECT planes.manufacturer as "Manufacturer", COUNT(*) AS "No. flights"
            FROM flights
            JOIN planes ON flights.tailnum = planes.tailnum
            WHERE {where_clause}
            GROUP BY "Manufacturer"
            ORDER BY "No. flights" DESC
            LIMIT 5;"""

    cursor.execute(query)
    rows = cursor.fetchall()
    top_5_manufacturers = pd.DataFrame(rows, columns=[x[0] for x in cursor.description])
    return top_5_manufacturers


@st.cache_data
def get_hourly_delay_stats(origin=None):
    """Get average departure delay by hour of day."""
    origin_filter = "" if origin is None else f"AND origin = '{origin}'"
    query = f"""
        SELECT hour, AVG(dep_delay) AS avg_delay
        FROM flights WHERE dep_delay IS NOT NULL {origin_filter}
        GROUP BY hour ORDER BY hour;
    """
    return pd.read_sql(query, connection)


@st.cache_data
def get_monthly_delay_stats(origin=None):
    """Get average departure delay by month."""
    origin_filter = "" if origin is None else f"AND origin = '{origin}'"
    query = f"""
        SELECT month, AVG(dep_delay) AS avg_delay
        FROM flights WHERE dep_delay IS NOT NULL {origin_filter}
        GROUP BY month ORDER BY month;
    """
    return pd.read_sql(query, connection)


@st.cache_data
def get_precipitation_delay_stats(origin=None):
    """Get average departure delay by precipitation level."""
    origin_filter = "" if origin is None else f"AND f.origin = '{origin}'"
    query = f"""
        SELECT ROUND(w.precip, 1) AS precipitation,
               AVG(f.dep_delay)   AS avg_delay
        FROM flights f
        JOIN weather w ON f.origin = w.origin
            AND f.month = w.month
            AND f.day   = w.day
            AND f.hour  = w.hour
        WHERE f.dep_delay IS NOT NULL
            AND w.precip IS NOT NULL
            {origin_filter}
        GROUP BY ROUND(w.precip, 1)
        ORDER BY precipitation;
    """
    return pd.read_sql(query, connection)


@st.cache_data
def get_visibility_delay_stats(origin=None):
    """Get average departure delay by visibility."""
    origin_filter = "" if origin is None else f"AND f.origin = '{origin}'"
    query = f"""
        SELECT ROUND(w.visib) AS visibility,
               AVG(f.dep_delay) AS avg_delay
        FROM flights f
        JOIN weather w ON f.origin = w.origin
            AND f.month = w.month
            AND f.day   = w.day
            AND f.hour  = w.hour
        WHERE f.dep_delay IS NOT NULL
            AND w.visib IS NOT NULL
            {origin_filter}
        GROUP BY ROUND(w.visib)
        ORDER BY visibility;
    """
    return pd.read_sql(query, connection)


def get_distance_delay_regression():

    '''
    we calculate the regression coefficient to investigate how delay and flight distance correlate.
    '''

    query = """ SELECT distance, arr_delay FROM flights WHERE distance IS NOT NULL AND arr_delay IS NOT NULL"""
    delay_df = pd.read_sql(query, connection)

    slope, intercept, r_val, p_val, std_error = linregress(delay_df['distance'], delay_df['arr_delay'])

    return f" Expected baseline delay: {intercept:.3f} ; additional delay for every mile travelled: {slope:.3}"



def get_speed_for_model():


    # get the average speed for all plane types using sql JOIN
    query = """
    SELECT
        planes.model,
        AVG(flights.distance * 1.0 / flights.air_time) AS average_speed
    FROM flights
    JOIN planes ON flights.tailnum = planes.tailnum
    WHERE flights.air_time IS NOT NULL AND flights.air_time > 0
    GROUP BY planes.model;"""

    #save as a pandas dataframe
    avg_speed_df = pd.read_sql(query, connection)

    for i, row in avg_speed_df.iterrows():
        model = row['model']
        speed = row['average_speed']

        #write to the speed column for planes table
        write = """
            UPDATE planes
            SET speed = ?
            WHERE model = ?
            """

        #execute the query
        cursor.execute(write, (speed, model))


    #save the query once
    connection.commit()


def get_wind_direction():
    """
    For each unique destination airport, computes the compass bearing of the flight
    path from JFK (the direction the plane follows), not the meteorological wind.
    Returns a DataFrame with dest, bearing_deg, and cardinal_dir columns.
    """
    query = """
        SELECT DISTINCT f.dest, a.lat, a.lon
        FROM flights f
        JOIN airports a ON f.dest = a.faa
        WHERE a.lat IS NOT NULL AND a.lon IS NOT NULL;
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    results = []
    if rows:
        dests, lats, lons = zip(*rows)
        bearings = _bearing_vec(np.array([JFK_LAT]*len(rows)), np.array([JFK_LON]*len(rows)), np.array(lats), np.array(lons))
        for dest, bearing_deg in zip(dests, bearings):
            results.append({
                'dest': dest,
                'bearing_deg': round(float(bearing_deg), 1),
                'cardinal_dir': _to_cardinal(float(bearing_deg)),
            })

    return pd.DataFrame(results)


def get_inner_product(flight_id):
    """
    Computes the 2D inner product (dot product) of:
      - the unit vector along the flight's bearing (origin -> destination)
      - the wind velocity vector (wind_speed in the direction the wind blows toward)
    Positive = tailwind, negative = headwind.
    """
    query = f"""
        SELECT flights.origin, flights.dest,
               weather.wind_dir, weather.wind_speed,
               orig_ap.lat, orig_ap.lon,
               dest_ap.lat, dest_ap.lon
        FROM flights
        JOIN weather ON flights.origin = weather.origin
            AND flights.month = weather.month
            AND flights.day = weather.day
            AND flights.hour = weather.hour
        JOIN airports AS orig_ap ON flights.origin = orig_ap.faa
        JOIN airports AS dest_ap ON flights.dest = dest_ap.faa
        WHERE flights.flight = '{flight_id}'
            AND weather.wind_dir IS NOT NULL
            AND weather.wind_speed IS NOT NULL
        LIMIT 1;
    """
    cursor.execute(query)
    row = cursor.fetchone()
    if row is None:
        return None

    _, _, wind_dir, wind_speed, orig_lat, orig_lon, dest_lat, dest_lon = row

    # flight direction: unit vector in the bearing direction from origin to destination
    bearing_deg = _bearing_vec(np.array([orig_lat]), np.array([orig_lon]), np.array([dest_lat]), np.array([dest_lon]))[0]
    bearing_rad = math.radians(float(bearing_deg))
    flight_vec = (math.sin(bearing_rad), math.cos(bearing_rad))

    # wind vector: wind_dir is direction wind blows FROM (meteorological convention),
    # so add 180° to get the direction it blows toward
    wind_toward_rad = math.radians((wind_dir + 180) % 360)
    wind_vec = (wind_speed * math.sin(wind_toward_rad), wind_speed * math.cos(wind_toward_rad))

    return flight_vec[0] * wind_vec[0] + flight_vec[1] * wind_vec[1]


def wind_speed_innerprod_regression():
    """
    Computes the 2D inner product of the flight direction vector and wind vector for all
    flights, splits into tailwind (>0) and headwind (<0) groups, then runs a T-test
    to check whether wind direction has a significant effect on air time.
    """
    query = """
        SELECT flights.air_time,
               weather.wind_dir, weather.wind_speed,
               orig_ap.lat AS orig_lat, orig_ap.lon AS orig_lon,
               dest_ap.lat AS dest_lat, dest_ap.lon AS dest_lon
        FROM flights
        JOIN weather ON flights.origin = weather.origin
            AND flights.month = weather.month
            AND flights.day = weather.day
            AND flights.hour = weather.hour
        JOIN airports AS orig_ap ON flights.origin = orig_ap.faa
        JOIN airports AS dest_ap ON flights.dest = dest_ap.faa
        WHERE flights.air_time IS NOT NULL
            AND weather.wind_speed IS NOT NULL
            AND weather.wind_dir IS NOT NULL;
    """
    df = pd.read_sql(query, connection)

    # Vectorised bearing and inner product calculation
    bearings = _bearing_vec(df['orig_lat'].values, df['orig_lon'].values,
                            df['dest_lat'].values, df['dest_lon'].values)
    bearing_rad = np.radians(bearings)
    flight_x, flight_y = np.sin(bearing_rad), np.cos(bearing_rad)

    wind_toward_rad = np.radians((df['wind_dir'].values + 180) % 360)
    wind_x = df['wind_speed'].values * np.sin(wind_toward_rad)
    wind_y = df['wind_speed'].values * np.cos(wind_toward_rad)

    df['inner_product'] = flight_x * wind_x + flight_y * wind_y

    positive = df[df['inner_product'] > 0]['air_time']
    negative = df[df['inner_product'] < 0]['air_time']

    t_stat, p_value = ttest_ind(positive, negative, nan_policy='omit')

    return f"T-test p-value: {p_value:.3f} — {'significant' if p_value < 0.05 else 'no significant'} correlation between wind direction and air time"


