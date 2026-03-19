import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from streamlit_option_menu import option_menu

from data import (
    get_carrier_delay,
    get_flight_trajectory,
    get_top_manufacturers,
    get_daily_statistics,
    get_daily_inbound_log,
    get_daily_outbound_log,
    get_distinct_origins,
    get_distinct_destinations,
    get_filtered_flight_metrics,
    get_hourly_delay_stats,
    get_monthly_delay_stats,
    get_precipitation_delay_stats,
    get_visibility_delay_stats,
)

st.set_page_config(page_title="NYC Flights Dashboard", layout="wide")

# ── Navigation bar ────────────────────────────────────────────────────────────
page = option_menu(
    menu_title=None,
    options=["Overview", "Airport Stats", "Delay Analysis", "Daily Statistics"],
    icons=["house", "map", "clock-history", "calendar-day"],
    orientation="horizontal",
    styles={
        "container": {"padding": "0", "background-color": "#1e3a5f"},
        "icon": {"color": "#aac8f0"},
        "nav-link": {"color": "#cde", "font-size": "0.95rem", "padding": "0.6rem 1.5rem"},
        "nav-link-selected": {"background-color": "#2e5f9e", "color": "white", "font-weight": "600"},
    },
)


# ── PAGE 1: Overview ──────────────────────────────────────────────────────────
if page == "Overview":
    st.sidebar.header("Filters")
    
    origins = get_distinct_origins()
    selected_origin = st.sidebar.selectbox(
        "Airport",
        ["All"] + origins,
        index=0,
    )
    
    month_range = st.sidebar.slider(
        "Select Month Range",
        min_value=1,
        max_value=12,
        value=(1, 12),
    )

    st.title("NYC Flights — Overview (2023)")

    origin_param = selected_origin if selected_origin != "All" else None
    metrics = get_filtered_flight_metrics(
        origin=origin_param,
        month_start=month_range[0],
        month_end=month_range[1],
    )
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Flights", f"{metrics['total_flights']:,}")
    col2.metric("Unique Destinations", f"{metrics['unique_destinations']:,}")
    col3.metric("Airlines", f"{metrics['total_airlines']:,}")

    st.subheader("Average Departure Delay by Airline")
    delay_df = get_carrier_delay()
    fig = px.bar(delay_df, x="name", y="avg_delay",
                 labels={"name": "Airline", "avg_delay": "Avg Delay (min)"})
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


# ── PAGE 2: Airport Stats ─────────────────────────────────────────────────────
elif page == "Airport Stats":
    origins = get_distinct_origins()
    dests = get_distinct_destinations()

    st.sidebar.header("Filters")
    dep = st.sidebar.selectbox("Departure Airport", ["All"] + origins)
    arr = st.sidebar.selectbox("Arrival Airport", ["All"] + dests)
    
    dep_param = None if dep == "All" else dep
    arr_param = None if arr == "All" else arr
    
    # Build title
    if dep == "All" and arr == "All":
        title = "Flights: All Airports"
    elif dep == "All":
        title = f"Flights: All → {arr}"
    elif arr == "All":
        title = f"Flights: {dep} → All"
    else:
        title = f"Flights: {dep} → {arr}"
    
    st.title(title)

    st.subheader("Plane Type Distribution")
    traj = get_flight_trajectory(dep_param, arr_param)
    if not traj:
        st.info("No flights found for this route.")
    else:
        st.dataframe(pd.DataFrame(traj.items(), columns=["Type", "Count"]), use_container_width=True)

    st.subheader("Top 5 Manufacturers")
    st.dataframe(get_top_manufacturers(destination_airport=arr_param, origin_airport=dep_param), use_container_width=True)


# ── PAGE 3: Delay Analysis ────────────────────────────────────────────────────
elif page == "Delay Analysis":
    origins = get_distinct_origins()

    st.sidebar.header("Filters")
    origin = st.sidebar.selectbox("Airport", ["All"] + origins)
    origin_param = None if origin == "All" else origin
    title = "Delay Analysis — All Airports" if origin == "All" else f"Delay Analysis — {origin}"

    st.title(title)

    st.subheader("Average Departure Delay by Hour of Day")
    hourly_df = get_hourly_delay_stats(origin_param)
    st.plotly_chart(
        px.line(hourly_df, x="hour", y="avg_delay",
                labels={"hour": "Hour of Day", "avg_delay": "Avg Delay (min)"}),
        use_container_width=True,
    )

    st.subheader("Average Departure Delay by Month")
    monthly_df = get_monthly_delay_stats(origin_param)
    st.plotly_chart(
        px.bar(monthly_df, x="month", y="avg_delay",
               labels={"month": "Month", "avg_delay": "Avg Delay (min)"}),
        use_container_width=True,
    )

    st.subheader("Weather Impact on Delays")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Precipitation vs Avg Departure Delay**")
        precip_df = get_precipitation_delay_stats(origin_param)
        st.plotly_chart(
            px.bar(precip_df, x="precipitation", y="avg_delay",
                   labels={"precipitation": "Precipitation (inches)", "avg_delay": "Avg Delay (min)"}),
            use_container_width=True,
        )

    with col2:
        st.markdown("**Visibility vs Avg Departure Delay**")
        visib_df = get_visibility_delay_stats(origin_param)
        st.plotly_chart(
            px.line(visib_df, x="visibility", y="avg_delay",
                    labels={"visibility": "Visibility (miles)", "avg_delay": "Avg Delay (min)"},
                    markers=True),
            use_container_width=True,
        )


# ── PAGE 4: Daily Statistics ──────────────────────────────────────────────────
elif page == "Daily Statistics":
    origins = get_distinct_origins()

    st.sidebar.header("Filters")
    origin = st.sidebar.selectbox("Airport", ["All"] + origins)
    origin_param = None if origin == "All" else origin
    
    date = st.sidebar.date_input(
        "Date",
        value=datetime.date(2023, 1, 1),
        min_value=datetime.date(2023, 1, 1),
        max_value=datetime.date(2023, 12, 31),
    )
    month, day = date.month, date.day

    formatted_date = date.strftime('%A, %B %d')
    title = f"Daily Statistics — All Airports, {formatted_date}" if origin == "All" else f"Daily Statistics — {origin}, {formatted_date}"
    st.header(title)

    # Display daily briefing in metric cards
    daily_stats = get_daily_statistics(day, month, origin_param)
    stats_dict = daily_stats.iloc[0].to_dict()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Flights Today", stats_dict["Flights Today"])
    col2.metric("Daily Average", f"{stats_dict['Avg Flights/Day']:.0f}")
    col3.metric("Difference from Average", stats_dict["Difference"])
    
    col4, col5, col6 = st.columns(3)
    col4.metric("Destinations", stats_dict["Unique Destinations"])
    col5.metric("Most Visited", stats_dict["Most Visited"])
    col6.metric("Least Visited", stats_dict["Least Visited"])

    st.subheader("Inbound Flights")
    st.dataframe(get_daily_inbound_log(day, month, origin_param), use_container_width=True)

    st.subheader("Outbound Flights")
    st.dataframe(get_daily_outbound_log(day, month, origin_param), use_container_width=True)
