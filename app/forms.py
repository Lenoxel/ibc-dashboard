import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def get_gspread_client():
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    return gspread.authorize(credentials)


@st.cache_data(ttl=60)
def get_google_form():
    client = get_gspread_client()
    sheet = client.open_by_url(st.secrets["google"]["sheet_url"]).sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)
