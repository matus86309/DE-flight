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
    get_daily_insights_summary,
    get_daily_hourly_profile,
    get_daily_carrier_mix,
    get_distinct_origins,
    get_distinct_destinations,
    get_filtered_overview_metrics,
    get_filtered_flights_page,
    get_airline_frequency,
    get_hourly_delay_stats,
    get_monthly_delay_stats,
    get_airport_overview_stats,
    get_monthly_flight_volume,
    get_distance_distribution,
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
    options=["Airport Overview", "Daily Statistics", "Flight Analysis"],
    icons=["map", "calendar-day", "graph-up"],
    orientation="horizontal",
    styles={
        "container": {"padding": "0", "background-color": "#1e3a5f"},
        "icon": {"color": "#aac8f0"},
        "nav-link": {"color": "#cde", "font-size": "0.95rem", "padding": "0.6rem 1.5rem"},
        "nav-link-selected": {"background-color": "#2e5f9e", "color": "white", "font-weight": "600"},
    },
)


# ── PAGE 1: Airport Overview ─────────────────────────────────────────────────
if page == "Airport Overview":
    origins = get_distinct_origins()

    st.sidebar.header("Filters")
    origin = st.sidebar.selectbox("Airport", ["All"] + origins)
    origin_param = None if origin == "All" else origin
    title = "Airport Overview — All Airports" if origin == "All" else f"Airport Overview — {origin}"

    st.title(title)

    overview_stats = get_airport_overview_stats(origin_param)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Flights", f"{overview_stats['total_flights']:,}")
    col2.metric("Airlines", f"{overview_stats['total_airlines']:,}")
    col3.metric("Avg Distance (mi)", f"{overview_stats['avg_distance']:.1f}")

    col4, col5, col6 = st.columns(3)
    col4.metric("Destinations", f"{overview_stats['unique_destinations']:,}")
    col5.metric("Most Visited", overview_stats["most_visited"])
    col6.metric("Least Visited", overview_stats["least_visited"])

    st.subheader("Yearly Traffic Overview (12-Month Aggregate)")
    agg_col1, agg_col2 = st.columns(2)

    with agg_col1:
        monthly_volume_df = get_monthly_flight_volume(origin_param)
        fig_monthly_volume = px.bar(
            monthly_volume_df,
            x="month",
            y="flights",
            labels={"month": "Month", "flights": "Flights"},
        )
        fig_monthly_volume.update_traces(marker_color=get_airport_color(origin))
        st.plotly_chart(fig_monthly_volume, use_container_width=True)

    with agg_col2:
        distance_dist_df = get_distance_distribution(origin_param)
        fig_distance_hist = px.histogram(
            distance_dist_df,
            x="distance",
            nbins=40,
            labels={"distance": "Flight Distance (mi)", "count": "Flights"},
        )
        fig_distance_hist.update_traces(marker_color=get_airport_color(origin))
        st.plotly_chart(fig_distance_hist, use_container_width=True)

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

    st.subheader("Average Departure Delay by Airline")
    airport_delay_df = get_carrier_delay(origin=origin_param)
    airport_fig = px.bar(
        airport_delay_df,
        x="name",
        y="avg_delay",
        labels={"name": "Airline", "avg_delay": "Avg Delay (min)"},
    )
    airport_fig.update_layout(xaxis_tickangle=-45)
    airport_fig.update_traces(marker_color=get_airport_color(origin))
    st.plotly_chart(airport_fig, use_container_width=True)


    st.subheader("Aircraft Analysis")
    aircraft_col1, aircraft_col2 = st.columns(2)

    with aircraft_col1:
        st.markdown("**Manufacturers**")
        st.dataframe(
            get_top_manufacturers(origin_airport=origin_param),
            use_container_width=True,
            hide_index=True,
        )

    with aircraft_col2:
        st.markdown("**Plane Type Distribution**")
        traj = get_flight_trajectory(origin_param, None)
        if not traj:
            st.info("No flights found for this route.")
        else:
            traj_df = pd.DataFrame(traj.items(), columns=["Aircraft Type", "Flights"])
            st.dataframe(traj_df, use_container_width=True, hide_index=True)



# ── PAGE 2: Daily Statistics ─────────────────────────────────────────────────
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

    st.subheader("Daily Insights")
    daily_insights = get_daily_insights_summary(day, month, origin_param)
    col1, col2, col3 = st.columns(3)
    col1.metric("On-Time Rate", f"{daily_insights['on_time_pct']:.1f}%")
    col2.metric("Avg Dep Delay", f"{daily_insights['avg_dep_delay']:.1f} min")
    col3.metric("Avg Arr Delay", f"{daily_insights['avg_arr_delay']:.1f} min")
    col4, col5, col6 = st.columns(3)
    col4.metric("Active Airlines", f"{daily_insights['active_airlines']:,}")
    col5.metric("Most Visited", stats_dict["Most Visited"])
    col6.metric("Least Visited", stats_dict["Least Visited"])

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown("**Flights by Hour**")
        hourly_profile_df = get_daily_hourly_profile(day, month, origin_param)
        if hourly_profile_df.empty:
            st.info("No hourly data available for this selection.")
        else:
            hourly_fig = px.bar(
                hourly_profile_df,
                x="hour",
                y="flights",
                labels={"hour": "Hour", "flights": "Flights"},
            )
            hourly_fig.update_traces(marker_color=get_airport_color(origin))
            st.plotly_chart(hourly_fig, use_container_width=True)

    with chart_col2:
        st.markdown("**Airline Mix (Selected Day)**")
        carrier_mix_df = get_daily_carrier_mix(day, month, origin_param)
        if carrier_mix_df.empty:
            st.info("No carrier data available for this selection.")
        else:
            carrier_mix_top = carrier_mix_df.head(8)
            mix_fig = px.pie(
                carrier_mix_top,
                values="flights",
                names="airline",
                hole=0.45,
            )
            st.plotly_chart(mix_fig, use_container_width=True)

    st.subheader("Inbound Flights")
    inbound_df = get_daily_inbound_log(day, month, dest=origin_param).rename(
        columns={"origin": "From", "destination": "To", "carrier": "Carrier", "flight": "Flight"}
    )
    inbound_df = inbound_df.style.map(style_airport_names, subset=["To"])
    st.dataframe(inbound_df, use_container_width=True)

    st.subheader("Outbound Flights")
    outbound_df = get_daily_outbound_log(day, month, origin_param).rename(
        columns={"origin": "From", "destination": "To", "carrier": "Carrier", "flight": "Flight"}
    )
    outbound_df = outbound_df.style.map(style_airport_names, subset=["From"])
    st.dataframe(outbound_df, use_container_width=True)


# ── PAGE 3: Flight Analysis ──────────────────────────────────────────────────
elif page == "Flight Analysis":
    st.sidebar.header("Filters")
    
    origins = get_distinct_origins()
    destinations = get_distinct_destinations()

    filter_col1, filter_col2 = st.sidebar.columns(2)
    selected_origin = filter_col1.selectbox(
        "From",
        ["All"] + origins,
        index=0,
    )

    selected_destination = filter_col2.selectbox(
        "To",
        ["All"] + destinations,
        index=0,
    )

    date_col1, date_col2 = st.sidebar.columns(2)
    start_date = date_col1.date_input(
        "Start",
        value=datetime.date(2023, 1, 1),
        min_value=datetime.date(2023, 1, 1),
        max_value=datetime.date(2023, 12, 31),
    )

    end_date = date_col2.date_input(
        "End",
        value=datetime.date(2023, 12, 31),
        min_value=datetime.date(2023, 1, 1),
        max_value=datetime.date(2023, 12, 31),
    )

    if end_date < start_date:
        st.sidebar.error("End date must be after start date.")
        st.stop()

    st.title("NYC Flights — Flight Analysis (2023)")

    origin_param = selected_origin if selected_origin != "All" else None
    destination_param = selected_destination if selected_destination != "All" else None

    overview_stats = get_filtered_overview_metrics(
        origin=origin_param,
        dest=destination_param,
        date_start=start_date.isoformat(),
        date_end=end_date.isoformat(),
    )
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Flights", f"{overview_stats['total_flights']:,}")
    col2.metric("Airlines", f"{overview_stats['total_airlines']:,}")
    col3.metric("Avg Distance (mi)", f"{overview_stats['avg_distance']:.1f}")
    col4.metric("Destinations", f"{overview_stats['unique_destinations']:,}")


    st.subheader("Flights")
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([2.5, 1.3, 1, 1])
    with ctrl_col1:
        search_term = st.text_input("Search", "", placeholder="carrier, airline, airport, flight no., tailnum")
    with ctrl_col2:
        sort_by = st.selectbox(
            "Sort by",
            ["flight_date", "origin", "destination", "airline", "carrier", "flight", "dep_delay", "arr_delay", "distance"],
            index=0,
        )
    with ctrl_col3:
        sort_order = st.selectbox("Order", ["DESC", "ASC"], index=0)
    with ctrl_col4:
        page_size = st.selectbox("Rows per page", [25, 50, 100], index=0)

    if "flight_analysis_page" not in st.session_state:
        st.session_state.flight_analysis_page = 1

    current_page = int(st.session_state.flight_analysis_page)

    flights_df, total_rows = get_filtered_flights_page(
        origin=origin_param,
        dest=destination_param,
        date_start=start_date.isoformat(),
        date_end=end_date.isoformat(),
        search_term=search_term.strip() or None,
        sort_by=sort_by,
        sort_order=sort_order,
        page=current_page,
        page_size=page_size,
    )

    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    if current_page > total_pages:
        st.session_state.flight_analysis_page = total_pages
        current_page = total_pages
        flights_df, total_rows = get_filtered_flights_page(
            origin=origin_param,
            dest=destination_param,
            date_start=start_date.isoformat(),
            date_end=end_date.isoformat(),
            search_term=search_term.strip() or None,
            sort_by=sort_by,
            sort_order=sort_order,
            page=current_page,
            page_size=page_size,
        )

    flights_df = flights_df.style.map(style_airport_names, subset=["From"])
    st.dataframe(flights_df, use_container_width=True, hide_index=True)

    pag_col1, pag_col2, pag_col3 = st.columns([1, 3, 1])
    with pag_col1:
        if st.button("Previous", use_container_width=True, disabled=current_page <= 1):
            st.session_state.flight_analysis_page = current_page - 1
            st.rerun()
    with pag_col2:
        st.markdown(f"<div style='text-align:center; padding-top: 0.35rem; font-size: 0.95rem;'>Page <strong>{current_page}</strong> of <strong>{total_pages}</strong>  •  {total_rows:,} flights</div>", unsafe_allow_html=True)
    with pag_col3:
        if st.button("Next", use_container_width=True, disabled=current_page >= total_pages):
            st.session_state.flight_analysis_page = current_page + 1
            st.rerun()

    st.subheader("Airline Frequency")
    airline_freq_df = get_airline_frequency(
        origin=origin_param,
        dest=destination_param,
        date_start=start_date.isoformat(),
        date_end=end_date.isoformat(),
    )
    st.dataframe(airline_freq_df, use_container_width=True, hide_index=True)

    st.subheader("Aircraft Analysis")
    aircraft_col1, aircraft_col2 = st.columns(2)

    with aircraft_col1:
        st.markdown("**Manufacturers**")
        st.dataframe(
            get_top_manufacturers(destination_airport=destination_param, origin_airport=origin_param),
            use_container_width=True,
            hide_index=True,
        )

    with aircraft_col2:
        st.markdown("**Plane Type Distribution**")
        traj = get_flight_trajectory(origin_param, destination_param)
        if not traj:
            st.info("No flights found for this route.")
        else:
            traj_df = pd.DataFrame(traj.items(), columns=["Aircraft Type", "Flights"])
            st.dataframe(traj_df, use_container_width=True, hide_index=True)

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
