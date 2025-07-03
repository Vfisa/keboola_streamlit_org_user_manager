import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")
st.title("Keboola Project User Manager")

# ---------------------------
# Load from Streamlit Secrets (if available)
# ---------------------------

if "api_token" not in st.session_state:
    st.session_state.api_token = st.secrets.get("keboola_api_token", "")
if "org_id" not in st.session_state:
    st.session_state.org_id = st.secrets.get("keboola_org_id", "")


# ---------------------------
# Sidebar: Stack, Host, Token, Org ID
# ---------------------------

st.sidebar.header("Keboola Environment Settings")

stack_options = {
    "US Virginia (AWS)": "https://connection.keboola.com",
    "US Virginia (GCP)": "https://connection.us-east4.gcp.keboola.com",
    "EU Frankfurt (AWS)": "https://connection.eu-central-1.keboola.com",
    "EU Ireland (Azure)": "https://connection.north-europe.azure.keboola.com",
    "EU Frankfurt (GCP)": "https://connection.europe-west3.gcp.keboola.com",
    "Custom": "custom"
}

stack_choice = st.sidebar.selectbox("Choose Stack:", list(stack_options.keys()))

if stack_options[stack_choice] == "custom":
    api_host = st.sidebar.text_input("Custom API Host (include https://):", value="https://")
else:
    api_host = stack_options[stack_choice]

if not api_host.startswith("http"):
    st.sidebar.error("Invalid API Host URL")
    st.stop()

MANAGEMENT_API = api_host

# ---------------------------
# Session State Defaults
# ---------------------------

for key in ["api_token", "org_id", "projects", "df_users", "audit_logs"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key in ["api_token", "org_id"] else None
if "audit_logs" not in st.session_state or st.session_state.audit_logs is None:
    st.session_state.audit_logs = []

# ---------------------------
# Sidebar Inputs
# ---------------------------

#st.session_state.api_token = st.sidebar.text_input("Keboola API Token", type="password", value=st.session_state.api_token)
#st.session_state.org_id = st.sidebar.text_input("Organization ID", value=st.session_state.org_id)

st.session_state.api_token = st.sidebar.text_input(
    "Keboola API Token",
    type="password",
    value=st.session_state.api_token
)

st.session_state.org_id = st.sidebar.text_input(
    "Organization ID",
    value=st.session_state.org_id
)

check_token = st.sidebar.button("Check Token")
load_users_trigger = st.sidebar.button("Load Users")

headers = {
    "X-KBC-ManageApiToken": st.session_state.api_token,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# ---------------------------
# Token Verification
# ---------------------------

if check_token and st.session_state.api_token:
    verify_url = f"{MANAGEMENT_API}/manage/tokens/verify"
    st.sidebar.markdown("**Debug Info:**")
    st.sidebar.code(f"GET {verify_url}", language="http")

    res = requests.get(verify_url, headers=headers)
    if res.ok:
        token_info = res.json()
        owner = token_info.get("owner", {}).get("name", "Unknown")
        st.sidebar.success(f"✅ Token valid for: {owner}")
    else:
        st.sidebar.error("❌ Invalid token")
        st.sidebar.code(f"Status Code: {res.status_code}\n{res.text}")

# ---------------------------
# Data Fetching Functions
# ---------------------------

@st.cache_data(show_spinner=True)
def get_projects(org_id, headers):
    url = f"{MANAGEMENT_API}/manage/organizations/{org_id}/projects"
    res = requests.get(url, headers=headers)
    return res.json() if res.ok else []

@st.cache_data(show_spinner=True)
def get_users(project_id, headers):
    url = f"{MANAGEMENT_API}/manage/projects/{project_id}/users"
    res = requests.get(url, headers=headers)
    return res.json() if res.ok else []

# ---------------------------
# Load Data on Button Click
# ---------------------------

if load_users_trigger:
    if not st.session_state.api_token or not st.session_state.org_id:
        st.sidebar.warning("Please enter token and org ID.")
    else:
        with st.spinner("Loading projects and users..."):
            projects = get_projects(st.session_state.org_id, headers)
            all_users_data = []
            for proj in projects:
                users = get_users(proj["id"], headers)
                for user in users:
                    all_users_data.append({
                        "user_id": user.get("id"),
                        "email": user.get("email"),
                        "role": user.get("role"),
                        "project": proj["name"],
                        "project_id": proj["id"],
                        "organization_id": st.session_state.org_id,
                        "expires": user.get("expires"),
                        "created": user.get("created"),
                        "reason": user.get("reason") if user.get("reason") and "email" in user.get("reason") else None,
                        "invitor": user.get("invitor")["email"] if user.get("invitor") and "email" in user.get("invitor") else None,
                        "approver": user.get("approver")["email"] if user.get("approver") and "email" in user.get("approver") else None
})
            df_users = pd.DataFrame(all_users_data)
            st.session_state.projects = projects
            st.session_state.df_users = df_users

# ---------------------------
# Guard if Data Not Loaded
# ---------------------------

if st.session_state.df_users is None or st.session_state.projects is None:
    st.warning("Click 'Load Users' to fetch project and user data.")
    st.stop()

df_users = st.session_state.df_users

# ---------------------------
# Summary
# ---------------------------

st.caption(f"Connected to: {api_host}")
st.write(f"Loaded **{len(df_users)}** user assignments from **{len(st.session_state.projects)}** projects in org `{st.session_state.org_id}`.")

# ---------------------------
# Download CSV with Full Metadata
# ---------------------------

st.download_button(
    "Download User-Project Mapping as CSV",
    data=df_users.to_csv(index=False),
    file_name="keboola_users_projects.csv"
)

# ---------------------------
# User Access Manager
# ---------------------------

emails = df_users["email"].unique()
selected_email = st.selectbox("Select user by email", sorted(emails))
user_projects = df_users[df_users["email"] == selected_email]

st.subheader(f"Projects for {selected_email}")
selected_projects = st.multiselect(
    "Select projects to remove this user from:",
    user_projects["project"].tolist()
)

# ---------------------------
# Remove Selected User Access + Logging
# ---------------------------

if st.button("Remove Selected Access", disabled=not selected_projects):
    for proj_name in selected_projects:
        proj_row = user_projects[user_projects["project"] == proj_name].iloc[0]
        proj_id = proj_row["project_id"]
        user_id = proj_row["user_id"]
        delete_url = f"{MANAGEMENT_API}/manage/projects/{proj_id}/users/{user_id}"
        res = requests.delete(delete_url, headers=headers)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        safe_headers = {
            k: ("***" if "Token" in k else v) for k, v in headers.items()
        }

        if res.ok:
            msg = (
                f"[{timestamp}] ✅ Removed {selected_email} (ID: {user_id}) from {proj_name}\n"
                f"DELETE {delete_url}\n"
                f"Headers: {safe_headers}"
            )
            st.success(f"Removed from {proj_name}")
        else:
            msg = (
                f"[{timestamp}] ❌ Failed to remove {selected_email} (ID: {user_id}) from {proj_name} – {res.text}\n"
                f"DELETE {delete_url}\n"
                f"Headers: {safe_headers}"
            )
            st.error(f"Failed to remove from {proj_name}")

        st.session_state.audit_logs.append(msg)

# ---------------------------
# Audit Log Display
# ---------------------------

if st.session_state.audit_logs:
    st.subheader("Audit Log")
    for entry in reversed(st.session_state.audit_logs):
        st.text(entry)