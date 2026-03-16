import sqlite3
import pandas as pd


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
            FROM flight
            JOIN planes ON flights.tailnum = planes.tailnum
            WHERE flights.origin = {departing_airport}
                AND flights.destination = {arriving_airport}
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

    #count the number of delayed flights in a given period
    cursor.execute(f"SELECT COUNT(*) FROM flights WHERE arr_delay >0 AND month IN '{month_range}' AND dest IN '{destinations_list}';'")
    num_days = cursor.fetchone()[0]



def get_top_manufacturers(destination_airport):

    #return the top 5 plane manufacturers from designated airport

    query = f"""
            SELECT planes.manufacturer, COUNT(*) AS num_flights
            FROM flights
            JOIN planes ON flights.tailnum = planes.tailnum
            WHERE flights.dest = '{destination_airport}'
            GROUP BY planes.manufacturer;
            ORDER BY num_flights DESC
            LIMIT 5;
            """
    cursor.execute(query)
    rows = cursor.fetchall()
    top_5_manufacturers = pd.DataFrame(rows, columns=[x[0] for x in cursor.description])
    return top_5_manufacturers


connection.close()