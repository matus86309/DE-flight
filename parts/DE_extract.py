import sqlite3
import pandas as pd
from scipy.stats import linregress
from scipy.stats import ttest_ind

DB_PATH = "../data/flights_database.db"
connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()




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

def get_daily_outbound_log(day,month):

    # select the destination, tailnumber and carrier of all outbound flights for a given day
    query = f"SELECT dest,carrier,flight from flights WHERE day = '{day}' AND month = '{month}'; "
    cursor.execute(query)
    rows = cursor.fetchall()
    daily_outbound_log = pd.DataFrame(rows,columns=[x[0] for x in cursor.description])
    return daily_outbound_log


def get_daily_statistics(day,month):

    '''
    create a dict containing a daily briefing for the selected day and month
    '''

    # number of distinct flights
    num_flight_query = f"SELECT COUNT(DISTINCT flight) FROM flights WHERE day = '{day}' AND month = '{month}';"
    cursor.execute(num_flight_query)
    num_flight = cursor.fetchone()[0]

    #number of unique destinations
    num_unique_destinations_query = f"SELECT COUNT(DISTINCT dest) FROM flights WHERE day = '{day}' AND month = '{month}';"
    cursor.execute(num_unique_destinations_query)
    num_unique_destinations = cursor.fetchone()[0]



    most_visited_query = (f"SELECT dest from flights "
                          f"WHERE day = '{day}' AND month = '{month}' "
                          f"GROUP BY dest ORDER BY COUNT(dest) DESC "
                          f"LIMIT 1;")
    cursor.execute(most_visited_query)
    most_visited = cursor.fetchone()[0]


    least_visited_query = (f"SELECT dest from flights "
                                 f"WHERE day = '{day}' AND month = '{month}' "
                                 f"GROUP BY dest ORDER BY COUNT(dest) ASC "
                                 f"LIMIT 1;")
    cursor.execute(least_visited_query)
    least_visited = cursor.fetchone()[0]

    #calculate average business
    cursor.execute("SELECT COUNT(*) FROM flights;")
    total_flights = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT month || '-' || day) FROM flights;")
    num_days = cursor.fetchone()[0]

    average_business = total_flights / num_days
    business_today = num_flight - average_business
    difference_percentage = (business_today/average_business)*100
    daily_business = f'{month}-{day} has {difference_percentage:.2f}% business compared to average day'

    df_structure = {"Date": [f"{month}-{day}"],
                    "Today's traffic":  [num_flight],
                    "Business today": [daily_business],
                    " Number of unique destinations": [num_unique_destinations],
                    "Most visited destination": [most_visited],
                    "Least visited destination": [least_visited],}

    daily_briefing_df = pd.DataFrame(df_structure)

    return daily_briefing_df


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

    #get all carriers
    delay_per_carrier = {}
    cursor.execute("SELECT DISTINCT carrier FROM flights;")
    unique_carriers = [i[0] for i in cursor.fetchall()]

    #calculate average delay per carrier
    for carrier in unique_carriers:
        cursor.execute(f"SELECT SUM(dep_delay) FROM flights WHERE carrier = '{carrier}';")
        sum_delay = cursor.fetchone()[0]

        cursor.execute(f"SELECT COUNT(*) FROM  flights WHERE carrier = '{carrier}';")
        num_flights = cursor.fetchone()[0]

        avg_delay = sum_delay/num_flights
        delay_per_carrier[carrier] = avg_delay

    #return a dict with avg delay for carriers
    return delay_per_carrier


def get_delayed_flight(month_range:[str],destinations_list:[str]):
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

    # get the wind_dir variable for all outbound flights from JFK
    query = "SELECT wind_dir FROM weather WHERE origin = 'JFK' AND wind_dir IS NOT NULL;"
    cursor.execute(query)
    rows = cursor.fetchall()

    directions = []

    #convert the degrees into direction
    for row in rows:
        degrees  = row[0]
        if degrees > 315 or degrees <= 45:
            direction = "North"
        elif degrees >45 and degrees <= 135:
            direction = "East"
        elif degrees >135 and degrees <= 225:
            direction = "South"
        else:
            direction = "West"
        directions.append(direction)
    wind_dir = pd.DataFrame(directions, columns=["wind_dir"])
    #get the direction dataframe
    return wind_dir


def get_inner_product(flight_id):

    '''
    get the merged day-month for the unique flight id, match it to the weather table on day-month object
    return the inner product of the wind_dir degrees and the wind_speed
    '''

    query = f"""
            SELECT flights.flight,
                (flights.month || '-' || flights.day) AS daytime,
                weather.wind_dir,
                weather.wind_speed,
                (weather.wind_speed * weather.wind_dir) AS inner_product
            FROM flights
            JOIN weather ON (flights.month || '-' || flights.day) = (weather.month || '-' || weather.day)
            WHERE flights.flight = '{flight_id}';"""
    cursor.execute(query)
    inner_product= cursor.fetchone()

    return inner_product[4]


def wind_speed_innerprod_regression():

    '''
    this function gets a dataframe of all inner products of flights and their corresponding airtime
    then sorts the inner product into positive or negative bucket
    then it runs a T-test to see if the inner prod and air time have statistically signifiant correlation
    '''

    #get inner_prod, air_time
    query= f"""
            SELECT flights.air_time,
                (weather.wind_speed * weather.wind_dir) AS inner_product
            FROM flights
            JOIN weather
                ON (flights.month || '-' || flights.day) = (weather.month || '-' || weather.day)
                AND flights.origin = weather.origin
                AND flights.month = weather.month
                AND flights.day = weather.day
                AND flights.hour = weather.hour
            WHERE flights.air_time IS NOT NULL
                AND weather.wind_speed IS NOT NULL;"""

    df = pd.read_sql(query, connection)

    #split to positive negatibe
    postive = df[df['inner_product'] >0]['air_time']
    negative = df[df['inner_product'] < 0]['air_time']

    #run the t-test
    t_stat,p_value = ttest_ind(postive, negative, nan_policy = 'omit')

    return f"there is {p_value:.3f} correlation between wind and airtime"


connection.close()
