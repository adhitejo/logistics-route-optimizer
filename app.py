import streamlit as st
import requests
import folium
import math
import pandas as pd
from datetime import datetime, timedelta
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection

# ------------------------------------------
# CONFIG & DATABASE CONNECTION
# ------------------------------------------
st.set_page_config(page_title="Logistic Enterprise System", layout="wide")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Helper function to safely read Google Sheets
def load_data(sheet_url):
    try:
        return conn.read(spreadsheet=sheet_url, ttl=0)
    except Exception:
        return pd.DataFrame()

# URLs Google Sheets Database
URL_VEHICLES = "https://docs.google.com/spreadsheets/d/12DUIfV9cD-qh507CdWQAlN62wnF5jVvn5eD5-9kJcek/edit"
URL_DRIVERS = "https://docs.google.com/spreadsheets/d/1aD4TnY5FBZ5zJ3GmZ7QMw8vGCkc3GNyeeNKXNobkr48/edit"
URL_ORDERS = "https://docs.google.com/spreadsheets/d/18vRdScdK_b5TEfSBxgyDu0LlwsKZN22GG5af8QMhB_M/edit"
URL_SETTLEMENTS = "https://docs.google.com/spreadsheets/d/1aWtn2ehrQ99eKqeHof2tVQkxAPj00JuSqUZRTaoBFac/edit"

# Load Initial Dataframe
df_vehicles = load_data(URL_VEHICLES)
df_drivers = load_data(URL_DRIVERS)
df_orders = load_data(URL_ORDERS)
df_settlements = load_data(URL_SETTLEMENTS)

# Master Fuel Ratio & Pricing
RASIO_BBM_ID = {
    "Blindvan": 12.0, "Granmax Box": 11.0,
    "CDE": 7.5, "CDE L": 7.25, "CDE Pendingin": 6.5, "CDE L Pendingin": 6.25,
    "CDD": 7.0, "CDD L": 6.5, "CDD Pendingin": 6.0, "CDD L Pendingin": 5.5,
    "Fuso": 4.0, "Tronton Wingbox": 3.0
}
HARGA_SOLAR_IDR = 6800

# Helper Functions (Ge
