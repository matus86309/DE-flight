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



connection.close()