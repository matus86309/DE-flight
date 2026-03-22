# DE-flight
This project is a data engineering dashboard that provides insights into airport operations and flight performance. It is built using Python, SQL, and Streamlit for interactive visualizations. The dashboard allows users to explore various metrics related to airport performance, daily statistics, and flight analysis. 

The dataset includes information on flights departing from the top 3 airports from the New York area (JFK, LGA, EWR) in the year 2019. The dashboard is designed to help understand key performance indicators (KPIs) and trends in airport operations.

## Project Architecture
The system is divided into three parts to allow for better organization and separation of concerns:

data.py
Includes the functions that retrieve the data from the database and perform the necessary transformations to prepare it for analysis.

data_cleaning.py
Contains the functions that clean the data, such as handling missing values, removing duplicates, and standardizing formats.

dashboard.py
Implements the Streamlit dashboard, which provides an interactive interface for users to explore the data and visualize key performance indicators (KPIs) related to airport operations.


## Deployment
The  dashboard is accessible at the following URL:
https://de-flights7.streamlit.app/


## Dashboard structure
The interface allows to choose between specific airports and dates to access relevant operational information. The dashboard is organized into three primary modules:

### 1. Airport Overview
This module provides a insight into the long-term performance of the aiport. It relies on long-term historical data to visualize overall airport statictics such as: average departure delay, and yearly traffic statistics.

### 2. Daily Statistics
This page offers a snapshot of the daily airport activity for a selected day.

Outbound flights Tracking: A log of all outbound flights of the day and destination lists.

(There are no inbound flights in the dataset, so this module only tracks outbound flights)

### 3. Flight Analysis
This page focuses on the flights information instead of the airport itself, it analyzes all flights in the year. 

It is possible to search by flight properties for specific flights and see their departure delay, departure time, arrival time, and other relevant information.

Visualizations of flights data on this module include:

Airline Frequency: analyses the share each carrier represents for all flights during the year.

Aircraft Analysis: this module shows what type of aircraft the flight was made with offering insight into manufacturer and engine information

Average Delay by Carrier: Show the aggregated average delay for each airline in the past 12 months.

## Installation and Usage
To run the dashboard locally, install the necessary dependencies and execute the Streamlit application:

```bash
pip install -r requirements.txt
streamlit run dashboard.py
