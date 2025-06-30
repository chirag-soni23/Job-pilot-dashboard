import os
import time
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

load_dotenv()
API = os.getenv("API_BASE") or st.secrets.get("API_BASE");
print(API)

st.set_page_config(
    page_title="Job Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        section.main > div {padding-top: 2rem;}
        .stMetric {text-align:center;}
        .metric-label {font-size:0.9rem;color:#888;}
        .metric-value {font-size:2rem;font-weight:700;margin:0;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Job‑Portal Analytics")


def save_token(tok: str):
    st.session_state["jwt"] = tok
    st.cache_data.clear()


def fetch(path: str, tries: int = 3):
    url = f"{API}{path}"
    for _ in range(tries):
        try:
            r = requests.get(url, headers=HEAD, cookies=COOKIE, timeout=30)
            if r.ok:
                return r.json()
            time.sleep(1)
        except requests.Timeout:
            time.sleep(2)
    return []


@st.cache_data(ttl=300, show_spinner=False)
def load_all():
    return fetch("/user/getall"), fetch("/job/getall"), fetch("/apply/getall")


with st.sidebar:
    st.header("🔐 Login")
    if "jwt" in st.session_state:
        st.success("Logged in ✅")
        if st.button("Logout"):
            st.session_state.pop("jwt")
            st.rerun()
    else:
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            try:
                r = requests.post(
                    f"{API}/user/login",
                    json={"email": email, "password": pwd},
                    timeout=30,
                )
                if r.ok:
                    token = r.json().get("token") or r.cookies.get("token")
                    if token:
                        save_token(token)
                        st.rerun()
                    else:
                        st.error("Token na mila 😔")
                else:
                    st.error(f"Login failed ({r.status_code})")
            except Exception as e:
                st.error(f"Error: {e}")

# ─── Auth Guard ───────────────────────────────────────────────────────────────
if "jwt" not in st.session_state:
    st.stop()

token = st.session_state["jwt"]
HEAD = {"Authorization": f"Bearer {token}"}
COOKIE = {"token": token}

# ─── Data Load ────────────────────────────────────────────────────────────────
users, jobs, apps = load_all()

df_users = pd.DataFrame(users)
df_jobs = pd.DataFrame(jobs)
df_apps = pd.DataFrame(apps)

# ─── Top Metrics ──────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("👥 Users", f"{len(df_users):,}")
c2.metric("💼 Jobs", f"{len(df_jobs):,}")
c3.metric("📑 Applications", f"{len(df_apps):,}")
st.divider()


st.sidebar.subheader("📅 Date Filter")
if not df_apps.empty and "createdAt" in df_apps.columns:
    df_apps["date"] = pd.to_datetime(df_apps["createdAt"]).dt.date
    min_d, max_d = df_apps["date"].min(), df_apps["date"].max()
    date_range = st.sidebar.date_input("Range", (min_d, max_d))
    if len(date_range) == 2:
        start, end = date_range
        df_apps = df_apps[(df_apps["date"] >= start) & (df_apps["date"] <= end)]


tab1, tab2, tab3, tab4 = st.tabs(
    ["User Roles", "Job Types", "Apps per Company", "Apps Over Time"]
)

with tab1:
    role_counts = df_users["role"].fillna("unknown").value_counts()
    if not role_counts.empty:
        fig = px.pie(
            role_counts,
            names=role_counts.index,
            values=role_counts.values,
            title="Users by Role",
            hole=0.4,
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    type_counts = df_jobs["type"].fillna("unknown").value_counts()
    if not type_counts.empty:
        fig = px.bar(
            type_counts,
            x=type_counts.index,
            y=type_counts.values,
            title="Jobs by Type",
            text_auto=True,
        )
        fig.update_layout(xaxis_title="", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    company_counts = (
        df_apps["job"]
        .apply(lambda j: j.get("company", "Unknown") if isinstance(j, dict) else "Unknown")
        .value_counts()
    )
    if not company_counts.empty:
        fig = px.bar(
            company_counts,
            y=company_counts.index,
            x=company_counts.values,
            title="Applications per Company",
            orientation="h",
            text_auto=True,
        )
        fig.update_layout(xaxis_title="Count", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    if not df_apps.empty:
        df_apps["date"] = pd.to_datetime(df_apps.get("createdAt"))
        daily = df_apps.groupby(df_apps["date"].dt.date).size().reset_index(name="count")
        fig = px.line(
            daily,
            x="date",
            y="count",
            markers=True,
            title="Applications Over Time",
        )
        fig.update_layout(xaxis_title="", yaxis_title="Applications")
        st.plotly_chart(fig, use_container_width=True)
