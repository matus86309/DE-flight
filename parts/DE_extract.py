import os
import sqlite3
import math
import numpy as np
import pandas as pd
import plotly.express as px
from scipy.stats import linregress
from scipy.stats import ttest_ind

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/flights_database.db")
connection = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = connection.cursor()

# JFK coordinates used as NYC origin for bearing/inner-product calculations
JFK_LAT = 40.6413
JFK_LON = -73.7781


def _bearing(lat1, lon1, lat2, lon2):
    """Compass bearing in degrees [0, 360) from point 1 to point 2."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.degrees(math.atan2(x, y)) % 360


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

def get_daily_outbound_log(day, month, origin=None):
    """
    Returns outbound flights for the given day/month.
    """
    origin_filter = f"AND origin = '{origin}'" if origin else ""
    query = f"SELECT dest, carrier, flight FROM flights WHERE day = '{day}' AND month = '{month}' {origin_filter};"
    cursor.execute(query)
    rows = cursor.fetchall()
    daily_outbound_log = pd.DataFrame(rows, columns=[x[0] for x in cursor.description])
    return daily_outbound_log


def get_daily_statistics(day, month, origin=None):
    '''
    Create a daily briefing DataFrame for the selected day and month.
    '''
    origin_filter = f"AND origin = '{origin}'" if origin else ""

    # number of distinct flights
    cursor.execute(f"SELECT COUNT(DISTINCT flight) FROM flights WHERE day = '{day}' AND month = '{month}' {origin_filter};")
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
    daily_business = f'{month}-{day} has {difference_percentage:.2f}% business compared to average day'

    df_structure = {"Date": [f"{month}-{day}"],
                    "Today's traffic":  [num_flight],
                    "Business today": [daily_business],
                    "Number of unique destinations": [num_unique_destinations],
                    "Most visited destination": [most_visited],
                    "Least visited destination": [least_visited],}

    return pd.DataFrame(df_structure)


def get_flight_trajectory(departing_airport,arriving_airport):

    #get the tailnumber of all flights between selected airports
    query = f"""
            SELECT planes.type, COUNT(*)
            FROM flights
            JOIN planes ON flights.tailnum = planes.tailnum
            WHERE flights.origin = '{departing_airport}'
                AND flights.dest = '{arriving_airport}'
            GROUP BY planes.type"""

    cursor.execute(query)
    type_distribution = dict(cursor.fetchall())
    return type_distribution



def get_carrier_delay():
    """
    Returns a DataFrame with average departure delay per airline.
    Displays a barplot with full airline names on the (rotated) x-axis.
    """
    query = """
        SELECT airlines.name, AVG(flights.dep_delay) AS avg_delay
        FROM flights
        JOIN airlines ON flights.carrier = airlines.carrier
        WHERE flights.dep_delay IS NOT NULL
        GROUP BY airlines.name
        ORDER BY avg_delay DESC;
    """
    delay_df = pd.read_sql(query, connection)

    return delay_df


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



def get_top_manufacturers(destination_airport):

    #return the top 5 plane manufacturers from designated airport

    query = f"""
            SELECT planes.manufacturer, COUNT(*) AS num_flights
            FROM flights
            JOIN planes ON flights.tailnum = planes.tailnum
            WHERE flights.dest = '{destination_airport}'
            GROUP BY planes.manufacturer
            ORDER BY num_flights DESC
            LIMIT 5;"""

    cursor.execute(query)
    rows = cursor.fetchall()
    top_5_manufacturers = pd.DataFrame(rows, columns=[x[0] for x in cursor.description])
    return top_5_manufacturers


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
    for dest, lat, lon in rows:
        bearing_deg = _bearing(JFK_LAT, JFK_LON, lat, lon)
        results.append({
            'dest': dest,
            'bearing_deg': round(bearing_deg, 1),
            'cardinal_dir': _to_cardinal(bearing_deg),
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
    bearing_rad = math.radians(_bearing(orig_lat, orig_lon, dest_lat, dest_lon))
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


