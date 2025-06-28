import os, requests, pandas as pd, matplotlib.pyplot as plt, streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("API_BASE", "https://jobpilot-gqgi.onrender.com/api")



# ─── Streamlit page 
st.set_page_config(page_title="Job Dashboard", layout="wide")
st.title("📊 Job‑Portal Analytics")

# ─── helper: store token + clear cache -------------------------------------
def set_token(tok: str):
    st.session_state["jwt"] = tok
    st.cache_data.clear()

# ─── Sidebar login/logout --------------------------------------------------
with st.sidebar:
    st.header("🔐 Login")
    if "jwt" in st.session_state:
        st.success("Logged in")
        if st.button("Logout"):
            st.session_state.pop("jwt")
    else:
        email    = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            try:
                r = requests.post(f"{API_BASE}/user/login",
                                  json={"email": email, "password": password},
                                  timeout=10)
                if r.status_code == 200:
                    token = r.json().get("token") or r.cookies.get("token")
                    if token:
                        set_token(token)
                        st.experimental_rerun()
                    else:
                        st.error("Token not found in response")
                else:
                    st.error(f"Login failed ({r.status_code})")
            except Exception as e:
                st.error(f"Error: {e}")

# stop if not authenticated
if "jwt" not in st.session_state:
    st.stop()

token   = st.session_state["jwt"]
HEADERS = {"Authorization": f"Bearer {token}"}
COOKIES = {"token": token}

# ─── safe GET --------------------------------------------------------------
def safe_get(path: str):
    try:
        res = requests.get(f"{API_BASE}{path}", headers=HEADERS,
                           cookies=COOKIES, timeout=10)
        if res.status_code == 200:
            return res.json()
        st.warning(f"{path} → {res.status_code}")
    except Exception as e:
        st.warning(f"{path} error: {e}")
    return []

@st.cache_data(ttl=300, show_spinner="🔄 Loading…")
def fetch_all(tok):
    return (
        safe_get("/user/getall"),
        safe_get("/job/getall"),
        safe_get("/apply/getall"),
    )

users, jobs, apps = fetch_all(token)

# ─── Stat cards ------------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Users", len(users))
c2.metric("Jobs",  len(jobs))
c3.metric("Applications", len(apps))
st.divider()

# ─── Chart 1: Users by Role -------------------------------------------------
role_counts = pd.Series([u.get("role", "unknown") for u in users]).value_counts()
if not role_counts.empty:
    fig, ax = plt.subplots()
    ax.pie(role_counts, labels=role_counts.index,
           autopct="%1.0f%%", startangle=140)
    ax.set_title("Users by Role"); ax.axis("equal")
    st.pyplot(fig)

# ─── Chart 2: Jobs by Type --------------------------------------------------
type_counts = pd.Series([j.get("type", "unknown") for j in jobs]).value_counts()
if not type_counts.empty:
    fig, ax = plt.subplots()
    ax.bar(type_counts.index, type_counts.values, color="skyblue")
    ax.set_title("Jobs by Type")
    ax.set_xlabel("Type"); ax.set_ylabel("Count")
    st.pyplot(fig)

# ─── Chart 3: Applications per Company -------------------------------------
comp_counts = pd.Series(
    [a.get("job", {}).get("company", "Unknown") for a in apps]
).value_counts()
if not comp_counts.empty:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh(comp_counts.index, comp_counts.values, color="coral")
    ax.set_title("Applications per Company")
    ax.set_xlabel("Applications")
    st.pyplot(fig)

# ─── Chart 4: Applications Over Time ---------------------------------------
date_counts = (
    pd.Series([a.get("createdAt", "")[:10] for a in apps if a.get("createdAt")])
    .value_counts()
    .sort_index()
)
if not date_counts.empty:
    date_counts.index = pd.to_datetime(date_counts.index)
    fig, ax = plt.subplots()
    ax.plot(date_counts.index, date_counts.values, marker="o")
    ax.set_title("Applications Over Time")
    ax.set_xlabel("Date"); ax.set_ylabel("Applications")
    fig.autofmt_xdate()
    st.pyplot(fig)
