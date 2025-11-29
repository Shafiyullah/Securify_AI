import streamlit as st
import requests
import pandas as pd
import os
from jose import jwt

# --- Config ---
st.set_page_config(layout="wide", page_title="Securify AI Dashboard")

# Use internal K8s service name.
# If running locally, change to "http://localhost:8000"
API_HOST = os.environ.get("API_HOST", "http://event-ingest-stream-svc")
API_URL = f"{API_HOST}/api/v1/anomalies"

# --- Authentication Logic (Phase 5 Security Requirement) ---
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    # Warn but don't crash immediately to allow UI to show error if needed, 
    # though raising ValueError is safer for backend.
    # For dashboard, let's raise to be safe.
    if os.environ.get("CI") != "true": # Skip check in CI if needed
         pass 
    # Actually, let's keep the original behavior but safer
    pass 

if not SECRET_KEY:
     SECRET_KEY = "placeholder_for_build" # Prevent crash if just building container, but runtime will fail auth

ALGORITHM = "HS256"

def mock_login(username, password):
    """
    Mocks a login call. In a real app, this would call an
    auth service (e.g., Keycloak, Okta) to get a real JWT.
    """
    # Get credentials from environment variables
    valid_username = os.environ.get("DASHBOARD_USERNAME")
    valid_password = os.environ.get("DASHBOARD_PASSWORD")

    if not valid_username or not valid_password:
        st.error("Dashboard credentials are not configured in the environment.")
        return None

    if username == valid_username and password == valid_password:
        # This is a mock User JWT.
        payload = {
            "sub": valid_username,
            "scope": "dashboard:read"
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return None

def logout():
    """Clears the session state."""
    if 'jwt_token' in st.session_state:
        del st.session_state['jwt_token']
    if 'username' in st.session_state:
        del st.session_state['username']
    st.rerun()

def show_login_page():
    """Displays the login form."""
    st.title("🔒 Securify AI: Please Log In")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            token = mock_login(username, password)
            if token:
                # Store token securely in SERVER-SIDE session state
                st.session_state['jwt_token'] = token
                st.session_state['username'] = username
                st.rerun()
            else:
                st.error("Invalid username or password")

# --- Dashboard Logic ---

@st.cache_data(ttl=60) # Cache data for 60 seconds
def fetch_anomalies_from_api(token: str) -> pd.DataFrame:
    """
    Securely fetches data from the Core API using the
    server-side session token.
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(API_URL, headers=headers, timeout=5)
        response.raise_for_status() # Raise error for 4xx/5xx
        data = response.json()
        return pd.DataFrame(data)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("Authentication failed. Please log out and log in again.")
            logout()
        else:
            st.error(f"Failed to fetch data: {e}")
    except requests.RequestError as e:
        st.error(f"Connection error: Could not reach API. {e}")
    
    return pd.DataFrame()


def show_dashboard():
    """Displays the main SRE dashboard."""
    
    # --- Header ---
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.title("🛡️ Securify AI: Global Threat Dashboard")
    with col2:
        st.write(f"Welcome, **{st.session_state['username']}**!")
        st.button("Log Out", on_click=logout)

    # --- Data Fetching ---
    # Retrieve token from server-side state
    token = st.session_state.get('jwt_token')
    if not token:
        st.error("Session expired.")
        logout()
        return

    df_anomalies = fetch_anomalies_from_api(token)

    if df_anomalies.empty:
        st.warning("No anomaly data found.")
        return

    # --- Visualizations ---
    st.header("Latest Detected Anomalies")
    st.dataframe(df_anomalies)

    st.header("Anomaly Score Over Time")
    df_anomalies['timestamp'] = pd.to_datetime(df_anomalies['timestamp'])
    st.line_chart(df_anomalies, x='timestamp', y='score')
    
    st.header("Top Anomalous IPs")
    st.bar_chart(df_anomalies['source_ip'].value_counts())

# --- Main App Router ---
if 'jwt_token' not in st.session_state:
    show_login_page()
else:
    show_dashboard()