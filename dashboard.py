import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from streamlit_option_menu import option_menu

from parts.DE_extract import (
    connection,
    get_carrier_delay,
    get_flight_trajectory,
    get_top_manufacturers,
    get_daily_statistics,
    get_daily_outbound_log,
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
    st.markdown("<style>[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)

    st.title("NYC Flights — Overview (2023)")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Flights", f"{pd.read_sql('SELECT COUNT(*) FROM flights;', connection).iloc[0, 0]:,}")
    col2.metric("Unique Destinations", f"{pd.read_sql('SELECT COUNT(DISTINCT dest) FROM flights;', connection).iloc[0, 0]:,}")
    col3.metric("Airlines", f"{pd.read_sql('SELECT COUNT(DISTINCT carrier) FROM flights;', connection).iloc[0, 0]:,}")

    st.subheader("Average Departure Delay by Airline")
    delay_df = get_carrier_delay()
    fig = px.bar(delay_df, x="name", y="avg_delay",
                 labels={"name": "Airline", "avg_delay": "Avg Delay (min)"})
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


# ── PAGE 2: Airport Stats ─────────────────────────────────────────────────────
elif page == "Airport Stats":
    origins = pd.read_sql("SELECT DISTINCT origin FROM flights ORDER BY origin;", connection)["origin"].tolist()
    dests = pd.read_sql("SELECT DISTINCT dest FROM flights ORDER BY dest;", connection)["dest"].tolist()

    st.sidebar.header("Search")
    dep = st.sidebar.selectbox("Departure Airport", origins)
    arr = st.sidebar.selectbox("Arrival Airport", dests)

    st.title(f"Flights: {dep} → {arr}")

    st.subheader("Plane Type Distribution")
    traj = get_flight_trajectory(dep, arr)
    if not traj:
        st.info("No flights found for this route.")
    else:
        st.dataframe(pd.DataFrame(traj.items(), columns=["Type", "Count"]), use_container_width=True)

    st.subheader(f"Top 5 Manufacturers flying to {arr}")
    st.dataframe(get_top_manufacturers(arr), use_container_width=True)


# ── PAGE 3: Delay Analysis ────────────────────────────────────────────────────
elif page == "Delay Analysis":
    origins = pd.read_sql("SELECT DISTINCT origin FROM flights ORDER BY origin;", connection)["origin"].tolist()

    st.sidebar.header("Search")
    origin = st.sidebar.selectbox("Departure Airport", origins)

    st.title(f"Delay Analysis — {origin}")

    st.subheader("Average Departure Delay by Hour of Day")
    hourly_df = pd.read_sql(f"""
        SELECT hour, AVG(dep_delay) AS avg_delay
        FROM flights WHERE dep_delay IS NOT NULL AND origin = '{origin}'
        GROUP BY hour ORDER BY hour;
    """, connection)
    st.plotly_chart(
        px.line(hourly_df, x="hour", y="avg_delay",
                labels={"hour": "Hour of Day", "avg_delay": "Avg Delay (min)"}),
        use_container_width=True,
    )

    st.subheader("Average Departure Delay by Month")
    monthly_df = pd.read_sql(f"""
        SELECT month, AVG(dep_delay) AS avg_delay
        FROM flights WHERE dep_delay IS NOT NULL AND origin = '{origin}'
        GROUP BY month ORDER BY month;
    """, connection)
    st.plotly_chart(
        px.bar(monthly_df, x="month", y="avg_delay",
               labels={"month": "Month", "avg_delay": "Avg Delay (min)"}),
        use_container_width=True,
    )

    st.subheader("Weather Impact on Delays")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Precipitation vs Avg Departure Delay**")
        precip_df = pd.read_sql(f"""
            SELECT ROUND(w.precip, 1) AS precipitation,
                   AVG(f.dep_delay)   AS avg_delay
            FROM flights f
            JOIN weather w ON f.origin = w.origin
                AND f.month = w.month
                AND f.day   = w.day
                AND f.hour  = w.hour
            WHERE f.dep_delay IS NOT NULL
                AND w.precip IS NOT NULL
                AND f.origin = '{origin}'
            GROUP BY ROUND(w.precip, 1)
            ORDER BY precipitation;
        """, connection)
        st.plotly_chart(
            px.bar(precip_df, x="precipitation", y="avg_delay",
                   labels={"precipitation": "Precipitation (inches)", "avg_delay": "Avg Delay (min)"}),
            use_container_width=True,
        )

    with col2:
        st.markdown("**Visibility vs Avg Departure Delay**")
        visib_df = pd.read_sql(f"""
            SELECT ROUND(w.visib) AS visibility,
                   AVG(f.dep_delay) AS avg_delay
            FROM flights f
            JOIN weather w ON f.origin = w.origin
                AND f.month = w.month
                AND f.day   = w.day
                AND f.hour  = w.hour
            WHERE f.dep_delay IS NOT NULL
                AND w.visib IS NOT NULL
                AND f.origin = '{origin}'
            GROUP BY ROUND(w.visib)
            ORDER BY visibility;
        """, connection)
        st.plotly_chart(
            px.line(visib_df, x="visibility", y="avg_delay",
                    labels={"visibility": "Visibility (miles)", "avg_delay": "Avg Delay (min)"},
                    markers=True),
            use_container_width=True,
        )


# ── PAGE 4: Daily Statistics ──────────────────────────────────────────────────
elif page == "Daily Statistics":
    origins = pd.read_sql("SELECT DISTINCT origin FROM flights ORDER BY origin;", connection)["origin"].tolist()

    st.sidebar.header("Search")
    origin = st.sidebar.selectbox("Airport", origins)
    date = st.sidebar.date_input(
        "Date",
        value=datetime.date(2023, 1, 1),
        min_value=datetime.date(2023, 1, 1),
        max_value=datetime.date(2023, 12, 31),
    )
    month, day = date.month, date.day

    st.title(f"Daily Statistics — {origin}, {date.strftime('%B %d, %Y')}")

    st.dataframe(get_daily_statistics(day, month, origin), use_container_width=True)

    st.subheader("Outbound Flights")
    st.dataframe(get_daily_outbound_log(day, month, origin), use_container_width=True)
