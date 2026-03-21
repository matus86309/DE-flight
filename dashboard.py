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
    get_filtered_overview_metrics,
    get_filtered_flights_page,
    get_airline_frequency,
    get_hourly_delay_stats,
    get_monthly_delay_stats,
    get_precipitation_delay_stats,
    get_visibility_delay_stats,
)

def get_airport_color(airport_name, default=None):
    """Get airport color that adapts to dark/light mode"""
    is_dark = st.config.get_option("theme.base") == "dark"
    
    color_schemes = {
        "JFK": {"light": "#e74c3c", "dark": "#ff6b6b"},     # Red variants
        "LGA": {"light": "#27ae60", "dark": "#2ecc71"},     # Blue variants
        "EWR": {"light": "#f39c12", "dark": "#f8b739"},     # Orange variants
    }

    if default is not None and airport_name not in color_schemes: 
        return default
    
    scheme = color_schemes.get(airport_name, {"light": "#3498db", "dark": "#5dade2"})
    return scheme["dark"] if is_dark else scheme["light"]

def style_airport_names(val):
    """Color code airport names in tables"""
    color =  get_airport_color(val, default=False)
    if color != False:
        return f"color: {color}"
    return ""

st.set_page_config(page_title="NYC Flights Dashboard", layout="wide")

# ── Navigation bar ────────────────────────────────────────────────────────────
page = option_menu(
    menu_title=None,
    options=["Overview", "Aircraft Analysis", "Delay Analysis", "Daily Statistics"],
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
    destinations = get_distinct_destinations()

    selected_origin = st.sidebar.selectbox(
        "Departure Airport",
        ["All"] + origins,
        index=0,
    )

    selected_destination = st.sidebar.selectbox(
        "Arrival Airport",
        ["All"] + destinations,
        index=0,
    )

    start_date = st.sidebar.date_input(
        "Start Date",
        value=datetime.date(2023, 1, 1),
        min_value=datetime.date(2023, 1, 1),
        max_value=datetime.date(2023, 12, 31),
    )

    end_date = st.sidebar.date_input(
        "End Date",
        value=datetime.date(2023, 12, 31),
        min_value=datetime.date(2023, 1, 1),
        max_value=datetime.date(2023, 12, 31),
    )

    if end_date < start_date:
        st.sidebar.error("End date must be after start date.")
        st.stop()

    st.title("NYC Flights — Overview (2023)")

    origin_param = selected_origin if selected_origin != "All" else None
    destination_param = selected_destination if selected_destination != "All" else None

    metrics = get_filtered_overview_metrics(
        origin=origin_param,
        dest=destination_param,
        date_start=start_date.isoformat(),
        date_end=end_date.isoformat(),
    )
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Flights", f"{metrics['total_flights']:,}")
    col2.metric("Unique Destinations", f"{metrics['unique_destinations']:,}")
    col3.metric("Airlines", f"{metrics['total_airlines']:,}")

    st.subheader("Flights")
    search_term = st.text_input("Search flights (carrier, airline, airport, flight no., tailnum)", "")

    sort_col1, sort_col2, sort_col3 = st.columns([2, 1, 1])
    with sort_col1:
        sort_by = st.selectbox(
            "Sort by",
            ["flight_date", "origin", "destination", "airline", "carrier", "flight", "dep_delay", "arr_delay", "distance"],
            index=0,
        )
    with sort_col2:
        sort_order = st.selectbox("Order", ["DESC", "ASC"], index=0)
    with sort_col3:
        page_size = st.selectbox("Rows per page", [25, 50, 100], index=0)

    flights_df_preview, total_rows = get_filtered_flights_page(
        origin=origin_param,
        dest=destination_param,
        date_start=start_date.isoformat(),
        date_end=end_date.isoformat(),
        search_term=search_term.strip() or None,
        sort_by=sort_by,
        sort_order=sort_order,
        page=1,
        page_size=1,
    )

    del flights_df_preview

    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page_number = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)

    flights_df, _ = get_filtered_flights_page(
        origin=origin_param,
        dest=destination_param,
        date_start=start_date.isoformat(),
        date_end=end_date.isoformat(),
        search_term=search_term.strip() or None,
        sort_by=sort_by,
        sort_order=sort_order,
        page=int(page_number),
        page_size=page_size,
    )

    st.caption(f"Showing page {int(page_number)} of {total_pages} ({total_rows:,} flights total)")
    st.dataframe(flights_df, use_container_width=True, hide_index=True)

    st.subheader("Airline Frequency")
    airline_freq_df = get_airline_frequency(
        origin=origin_param,
        dest=destination_param,
        date_start=start_date.isoformat(),
        date_end=end_date.isoformat(),
    )
    st.dataframe(airline_freq_df, use_container_width=True, hide_index=True)

    st.subheader("Average Departure Delay by Airline")
    delay_df = get_carrier_delay(
        origin=origin_param,
        dest=destination_param,
        date_start=start_date.isoformat(),
        date_end=end_date.isoformat(),
    )
    fig = px.bar(delay_df, x="name", y="avg_delay",
                 labels={"name": "Airline", "avg_delay": "Avg Delay (min)"})
    fig.update_layout(xaxis_tickangle=-45)
    fig.update_traces(marker_color=get_airport_color(selected_origin))
    st.plotly_chart(fig, use_container_width=True)


# ── PAGE 2: Aircraft Analysis ─────────────────────────────────────────────────
elif page == "Aircraft Analysis":
    origins = get_distinct_origins()
    dests = get_distinct_destinations()

    st.sidebar.header("Filters")
    dep = st.sidebar.selectbox("Departure Airport", ["All"] + origins)
    arr = st.sidebar.selectbox("Arrival Airport", ["All"] + dests)
    
    dep_param = None if dep == "All" else dep
    arr_param = None if arr == "All" else arr
    
    # Build title
    if dep == "All" and arr == "All":
        title = "Aircraft Analysis: All Airports"
    elif dep == "All":
        title = f"Aircraft Analysis: All → {arr}"
    elif arr == "All":
        title = f"Aircraft Analysis: {dep} → All"
    else:
        title = f"Aircraft Analysis: {dep} → {arr}"
    
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
    fig1 = px.line(hourly_df, x="hour", y="avg_delay",
                labels={"hour": "Hour of Day", "avg_delay": "Avg Delay (min)"})
    fig1.update_traces(line_color=get_airport_color(origin))
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Average Departure Delay by Month")
    monthly_df = get_monthly_delay_stats(origin_param)
    fig2 = px.bar(monthly_df, x="month", y="avg_delay",
                 labels={"month": "Month", "avg_delay": "Avg Delay (min)"})
    fig2.update_traces(marker_color=get_airport_color(origin))
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Weather Impact on Delays")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Precipitation vs Avg Departure Delay**")
        precip_df = get_precipitation_delay_stats(origin_param)
        fig3 = px.bar(precip_df, x="precipitation", y="avg_delay",
                   labels={"precipitation": "Precipitation (inches)", "avg_delay": "Avg Delay (min)"})
        fig3.update_traces(marker_color=get_airport_color(origin))
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        st.markdown("**Visibility vs Avg Departure Delay**")
        visib_df = get_visibility_delay_stats(origin_param)
        fig4 = px.line(visib_df, x="visibility", y="avg_delay",
                    labels={"visibility": "Visibility (miles)", "avg_delay": "Avg Delay (min)"},
                    markers=True)
        fig4.update_traces(line_color=get_airport_color(origin), marker_color=get_airport_color(origin))
        st.plotly_chart(fig4, use_container_width=True,)


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
    inbound_df = get_daily_inbound_log(day, month, dest=origin_param).style.map(style_airport_names, subset=["destination"])
    st.dataframe(inbound_df, use_container_width=True)

    st.subheader("Outbound Flights")
    outbound_df = get_daily_outbound_log(day, month, origin_param).style.map(style_airport_names, subset=["origin"])
    st.dataframe(outbound_df, use_container_width=True)
