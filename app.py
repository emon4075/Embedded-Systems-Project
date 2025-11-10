import streamlit as st
import requests
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

AIO_USERNAME = os.getenv("AIO_USERNAME", st.secrets.get("AIO_USERNAME", "emon4075"))
AIO_KEY = os.getenv("AIO_KEY", st.secrets.get("AIO_KEY", None))

# Feed Configuration
TEMP_FEED_KEY = "temperature"
HUMID_FEED_KEY = "humidity"
LIMIT = 500

# Fetch Feed Data
@st.cache_data(ttl=600)
def get_feed_data(feed_key, limit=LIMIT):
    url = f"https://io.adafruit.com/api/v2/{AIO_USERNAME}/feeds/{feed_key}/data"
    headers = {"X-AIO-Key": AIO_KEY}
    params = {"limit": limit}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data for {feed_key}: {e}")
        return None

# ⚙️ Process Feed Data
def process_data(data):
    times, values = [], []
    for entry in data:
        try:
            dt = datetime.datetime.fromisoformat(entry["created_at"].replace("Z", "+00:00"))
            times.append(dt)
            values.append(float(entry["value"]))
        except Exception as e:
            st.warning(f"Skipping invalid entry: {entry} — {e}")
    return (
        pd.DataFrame({"time": times, "value": values})
        .sort_values("time")
        .reset_index(drop=True)
    )

# 📊 Main Dashboard Function
def create_dashboard():
    st.set_page_config(layout="wide", page_title="DHT11 Dashboard", page_icon="📈")
    st.title("🌡️💧 ESP32 DHT11 Temperature and Humidity Dashboard")

    st.markdown(
        "Real-time data from ESP32 via Adafruit IO. "
        "Visualized using Matplotlib + Streamlit."
    )

    # Sidebar
    st.sidebar.header("Settings")
    st.sidebar.write(f"Showing last {LIMIT} data points")

    theme = st.sidebar.radio("Select Plot Theme", ["Light", "Dark"], index=0)
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Theme
    plt.style.use("Solarize_Light2" if theme == "Light" else "dark_background")

    # Debug Info (optional)
    with st.sidebar.expander("🔍 Debug Info"):
        st.write("Username:", AIO_USERNAME)
        st.write("Key loaded:", "✅ Yes" if AIO_KEY else "❌ Missing")

    # Fetch & Process Data
    temp_data_raw = get_feed_data(TEMP_FEED_KEY)
    humid_data_raw = get_feed_data(HUMID_FEED_KEY)

    if temp_data_raw is None or humid_data_raw is None:
        st.error("Unable to fetch data from Adafruit IO. Check your credentials or network.")
        return

    temp_df = process_data(temp_data_raw or [])
    humid_df = process_data(humid_data_raw or [])

    if temp_df.empty and humid_df.empty:
        st.warning("No valid data available. Ensure your ESP32 is uploading to Adafruit IO.")
        return

    # Plot
    st.subheader("📊 Temperature and Humidity Over Time")

    fig, ax1 = plt.subplots(figsize=(12, 6))

    if not temp_df.empty:
        ax1.plot(
            temp_df["time"],
            temp_df["value"],
            color="red",
            label="Temperature (°C)",
            marker="o",
        )
        ax1.set_xlabel("Time (UTC)")
        ax1.set_ylabel("Temperature (°C)", color="red")
        ax1.tick_params(axis="y", labelcolor="red")
        ax1.set_ylim(20, 50)
        ax1.grid(True, linestyle="--", alpha=0.6)

    ax2 = ax1.twinx()
    if not humid_df.empty:
        ax2.plot(
            humid_df["time"],
            humid_df["value"],
            color="blue",
            label="Humidity (%)",
            marker="x",
        )
        ax2.set_ylabel("Humidity (%)", color="blue")
        ax2.tick_params(axis="y", labelcolor="blue")
        ax2.set_ylim(60, 90)

    ax1.set_title("ESP32 DHT11 Sensor Readings Over Time", fontsize=16, fontweight="bold")

    formatter = mdates.DateFormatter("%Y-%m-%d %H:%M")
    ax1.xaxis.set_major_formatter(formatter)
    fig.autofmt_xdate()

    lines = ax1.get_lines() + ax2.get_lines()
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, loc="upper left", frameon=True)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    # Raw Data Tables
    st.subheader("📄 Raw Data")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🌡️ Temperature")
        st.dataframe(temp_df.set_index("time").sort_index(ascending=False), height=300)

    with col2:
        st.markdown("### 💧 Humidity")
        st.dataframe(humid_df.set_index("time").sort_index(ascending=False), height=300)

    st.markdown("")
    st.caption("Data Source: Adafruit IO")

if __name__ == "__main__":
    create_dashboard()
