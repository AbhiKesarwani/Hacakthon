import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_squared_error

# Load dataset efficiently
DATA_PATH = "updated_data.csv"
if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH, parse_dates=['Date'], dayfirst=True, usecols=[
        'Date', 'Route_ID', 'Seats_Booked', 'Fuel_Consumption_Liters', 'Total_Seats', 'Ticket_Price'
    ])
    if df.empty:
        st.error("❌ Dataset is empty. Please upload valid data.")
        st.stop()
else:
    st.error("❌ Dataset not found. Please upload a valid file.")
    st.stop()

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Dataset", "EDA", "Demand Forecasting", "Upload Data"])

# Home Page
if page == "Home":
    st.title("🚌 GSRTC Data-Driven Insights Dashboard")
    st.write("""
    ## 🚀 Problem Statement
    GSRTC currently operates with fragmented data across multiple departments, leading to inefficiencies in decision-making, inaccurate demand forecasting, and suboptimal resource utilization.

    ## ⚠️ Challenges
    - Lack of a centralized data platform
    - Inefficient scheduling and resource allocation
    - Difficulty in predicting passenger demand
    - High operational costs due to fuel inefficiencies

    ## 🎯 Expected Outcomes
    - A unified data platform integrating multiple data sources
    - Improved decision-making with real-time insights
    - Accurate demand forecasting to optimize scheduling
    - Enhanced customer satisfaction with better service planning
    """)

# Dataset Page
elif page == "Dataset":
    st.title("📂 Dataset Overview")
    st.write("""
    ### 🔍 About the Dataset
    - **Synthetic Data** designed to simulate real-world GSRTC operations.
    - Includes details about bus trips, fuel consumption, occupancy rates, delays, ticket prices, and more.
    - Helps in **resource allocation, demand forecasting, and operational efficiency**.

    ### 📊 Sample Data:
    """)

    st.dataframe(df, height=400, width=1000)  # Enables scrolling in both directions
    st.download_button("⬇️ Download Dataset", df.to_csv(index=False), "dataset.csv", "text/csv")

# EDA Portal
elif page == "EDA":
    st.title("📈 Exploratory Data Analysis")
    st.write("Below are key insights from our Power BI analysis.")

    st.image("gsrtc_dashboard.png", caption="📊 GSRTC Power BI Dashboard")
    st.image("avg_fuel_consumption.png", caption="⛽ Average Fuel Consumption")
    st.image("avg_profit_per_trip_by_route.png", caption="💰 Avg Profit Per Trip by Route")
    st.image("seats_booked_by_destination.png", caption="🛋️ Seats Booked by Destination")
    st.image("seats_booked_per_month.png", caption="📆 Seats Booked Per Month")
    st.image("total_trips_by_delay_status.png", caption="⏳ Total Trips by Delay Status")
    st.image("total_trips_by_delay_occupancy.png", caption="🚌 Total Trips by Delay & Occupancy")

# Demand Forecasting Portal
elif page == "Demand Forecasting":
    st.title("📊 Passenger Demand Forecasting")
    st.write("Using SARIMA model to predict future passenger demand.")

    # Preprocessing
    df_daily = df.groupby('Date').agg({'Seats_Booked': 'sum'}).reset_index().sort_values(by='Date')

    # ADF Test Function
    def adf_test(series):
        result = adfuller(series)
        return result[1]  # Return p-value

    # Check Stationarity
    p_value = adf_test(df_daily["Seats_Booked"])
    if p_value > 0.05:
        df_daily["Seats_Booked_Diff"] = df_daily["Seats_Booked"].diff().dropna()
        st.write("❌ Data is NOT stationary. Applied differencing.")
    else:
        st.write("✅ Data is stationary. No differencing applied.")

    # Train-Test Split
    train_size = int(len(df_daily) * 0.8)
    train, test = df_daily[:train_size], df_daily[train_size:]

    # SARIMA Model Training (Cached for Speed)
    @st.cache_resource
    def train_sarima(train_data):
        model = SARIMAX(train_data, order=(1, 1, 1), seasonal_order=(1, 1, 1, 60))
        return model.fit()

    sarima_result = train_sarima(train['Seats_Booked'])

    # Forecast Test Data
    test_forecast = sarima_result.get_forecast(steps=len(test))
    test_forecast_mean = test_forecast.predicted_mean

    # Model Evaluation
    rmse = np.sqrt(mean_squared_error(test['Seats_Booked'], test_forecast_mean))
    st.write(f"📊 **SARIMA Model RMSE:** {rmse:.2f}")

    # User Input for Future Forecasting
    future_steps = st.slider("📅 Select Forecast Duration (Days)", min_value=7, max_value=90, value=30)
    
    # Future Demand Forecast
    sarima_forecast_next = sarima_result.forecast(steps=future_steps)

    # Create Future Dates
    future_dates = pd.date_range(start=df_daily['Date'].iloc[-1] + pd.Timedelta(days=1), periods=future_steps)

    # Visualization
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df_daily['Date'], df_daily['Seats_Booked'], label="Actual Data", color="blue")
    ax.plot(df_daily['Date'][:len(train)], sarima_result.fittedvalues, label="Fitted Values", linestyle="dotted", color="orange")
    ax.plot(df_daily['Date'][len(train):], test_forecast_mean, label="Test Forecast", linestyle="dashed", color="green")
    ax.plot(future_dates, sarima_forecast_next, label=f"Next {future_steps} Days Forecast", linestyle="dashed", color="red")
    ax.set_xlabel("Date")
    ax.set_ylabel("Seats Booked")
    ax.set_title("📈 SARIMA Model - Demand Forecasting")
    ax.legend()
    ax.grid()
    
    st.pyplot(fig)

    # Display Insights
    st.subheader("🔎 Key Insights")
    peak_demand = sarima_forecast_next.max()
    low_demand = sarima_forecast_next.min()
    
    st.write(f"✔️ **Highest Predicted Demand:** {peak_demand:.0f} seats")
    st.write(f"⚠️ **Lowest Predicted Demand:** {low_demand:.0f} seats")
    st.write("🚀 **Business Impact:** This forecast helps in optimizing fleet allocation, fuel efficiency, and revenue planning.")

# Data Upload Portal
elif page == "Upload Data":
    st.title("📤 Upload New Data")
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        new_data = pd.read_csv(uploaded_file)
        if set(new_data.columns) == set(df.columns):
            new_data.to_csv(DATA_PATH, mode='a', header=False, index=False)
            st.success("✅ Data successfully uploaded and merged!")
        else:
            st.error("❌ Column mismatch! Ensure the uploaded file has the same structure as the dataset.")
