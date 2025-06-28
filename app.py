# dashboard.py
import os, time, requests, pandas as pd, matplotlib.pyplot as plt, streamlit as st
from dotenv import load_dotenv

load_dotenv()
API = os.getenv("API_BASE") or st.secrets.get("API_BASE", "http://localhost:5000/api")

st.set_page_config(page_title="Job Dashboard", layout="wide")
st.title("📊 Job‑Portal Analytics")

# ─── Token helper
def save_token(tok: str):
    st.session_state["jwt"] = tok
    st.cache_data.clear()

# ─── Sidebar login/logout
with st.sidebar:
    st.header("🔐 Login")
    if "jwt" in st.session_state:
        st.success("Logged in")
        if st.button("Logout"):
            st.session_state.pop("jwt")
            st.rerun()
    else:
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            try:
                r = requests.post(f"{API}/user/login",
                                  json={"email": email, "password": pwd},
                                  timeout=30)
                if r.status_code == 200:
                    token = r.json().get("token") or r.cookies.get("token")
                    if token:
                        save_token(token)
                        st.rerun()
                    else:
                        st.error("No token in response")
                else:
                    st.error(f"Login failed ({r.status_code})")
            except Exception as e:
                st.error(f"Error: {e}")

# ─── Stop if no token
if "jwt" not in st.session_state:
    st.stop()

token  = st.session_state["jwt"]
HEAD   = {"Authorization": f"Bearer {token}"}
COOKIE = {"token": token}

# ─── Safe GET with retry
def fetch(path, tries=3):
    url = f"{API}{path}"
    for _ in range(tries):
        try:
            r = requests.get(url, headers=HEAD, cookies=COOKIE, timeout=30)
            if r.status_code == 200:
                return r.json()
            st.warning(f"{path} → {r.status_code}")
            break
        except requests.Timeout:
            time.sleep(2)
    return []

@st.cache_data(ttl=300)
def load_all(tok):
    return fetch("/user/getall"), fetch("/job/getall"), fetch("/apply/getall")

users, jobs, apps = load_all(token)

# ─── Stats
c1, c2, c3 = st.columns(3)
c1.metric("Users", len(users))
c2.metric("Jobs",  len(jobs))
c3.metric("Applications", len(apps))
st.divider()

# ─── Chart functions
def pie(series, title):
    if not series.empty:
        fig, ax = plt.subplots()
        ax.pie(series, labels=series.index, autopct="%1.0f%%", startangle=140)
        ax.set_title(title)
        ax.axis("equal")
        st.pyplot(fig)

def bar(series, title):
    if not series.empty:
        fig, ax = plt.subplots()
        ax.bar(series.index, series.values, color="skyblue")
        ax.set_title(title)
        st.pyplot(fig)

def barh(series, title):
    if not series.empty:
        fig, ax = plt.subplots()
        ax.barh(series.index, series.values, color="coral")
        ax.set_title(title)
        st.pyplot(fig)

def line(series, title):
    if not series.empty:
        fig, ax = plt.subplots()
        ax.plot(series.index, series.values, marker="o")
        ax.set_title(title)
        fig.autofmt_xdate()
        st.pyplot(fig)

# ─── Charts
pie(pd.Series([u.get("role","unknown") for u in users]).value_counts(),
    "Users by Role")

bar(pd.Series([j.get("type","unknown") for j in jobs]).value_counts(),
    "Jobs by Type")

barh(pd.Series([a.get("job",{}).get("company","Unknown") for a in apps]).value_counts(),
     "Applications per Company")

dates = (pd.Series([a.get("createdAt","")[:10] for a in apps if a.get("createdAt")])
         .value_counts().sort_index())
dates.index = pd.to_datetime(dates.index)
line(dates, "Applications Over Time")
