import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from urllib.parse import quote

# ---------------------------
# Streamlit Setup
# ---------------------------
st.set_page_config(layout="wide")
st.title("Keboola Project User Manager")

# ---------------------------
# Load API Token and Org ID from Secrets
# ---------------------------
if "api_token" not in st.session_state:
    st.session_state.api_token = st.secrets.get("keboola_api_token", "")
if "org_id" not in st.session_state:
    st.session_state.org_id = st.secrets.get("keboola_org_id", "")

# ---------------------------
# Sidebar: Environment Configuration
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
if st.session_state.audit_logs is None:
    st.session_state.audit_logs = []

# ---------------------------
# Sidebar Inputs for Token and Org ID
# ---------------------------
st.session_state.api_token = st.sidebar.text_input("Keboola API Token", type="password", value=st.session_state.api_token)
st.session_state.org_id = st.sidebar.text_input("Organization ID", value=st.session_state.org_id)
check_token = st.sidebar.button("Check Token")
load_users_trigger = st.sidebar.button("Load Users")

# ---------------------------
# Token Verification
# ---------------------------
headers = {
    "X-KBC-ManageApiToken": st.session_state.api_token,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

if check_token and st.session_state.api_token:
    verify_url = f"{MANAGEMENT_API}/manage/tokens/verify"
    st.sidebar.code(f"GET {verify_url}", language="http")
    res = requests.get(verify_url, headers=headers)
    if res.ok:
        owner = res.json().get("owner", {}).get("name", "Unknown")
        st.sidebar.success(f"✅ Token valid for: {owner}")
    else:
        st.sidebar.error("❌ Invalid token")
        st.sidebar.code(f"Status Code: {res.status_code}\n{res.text}")

# ---------------------------
# API Data Fetching Functions
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
# Load Users from All Projects
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

if st.session_state.df_users is None:
    st.warning("Click 'Load Users' to fetch project and user data.")
    st.stop()

# ---------------------------
# Tabs: Overview and User Removal
# ---------------------------
query_params = st.query_params
selected_from_url = query_params.get("email", [None])[0]

df_users = st.session_state.df_users
projects = st.session_state.projects

tab1, tab2 = st.tabs(["Overview", "User Removal"])

# ---------------------------
# Overview Tab
# ---------------------------
with tab1:
    st.caption(f"Connected to: {api_host}")
    st.write(f"Loaded **{len(df_users)}** user assignments from **{len(projects)}** projects in org `{st.session_state.org_id}`.")

    st.download_button(
        "Download User-Project Mapping as CSV",
        data=df_users.to_csv(index=False),
        file_name="keboola_users_projects.csv"
    )

    role_icons = {
        "Share": "🤝",
        "Admin": "🛠️",
        "Guest": "👤",
        "ReadOnly": "👁️"
    }

    proj_id_to_name = {p["id"]: p["name"] for p in projects}
    proj_ids = sorted(proj_id_to_name.keys())
    proj_id_links = {
        pid: f'<a href="{api_host}/admin/projects/{pid}" title="{proj_id_to_name[pid]}" target="_blank">{pid}</a>'
        for pid in proj_ids
    }

    users = sorted(df_users["email"].unique())
    email_links = {
        email: f'<a href="?email={quote(email)}">{email}</a>' for email in users
    }

    matrix_data = []
    for user in users:
        row = []
        for pid in proj_ids:
            entry = df_users[(df_users["email"] == user) & (df_users["project_id"] == pid)]
            if not entry.empty:
                role = entry["role"].iloc[0]
                icon = role_icons.get(role, "❓")
                cell = f'<span title="{role}">{icon}</span>'
            else:
                cell = ""
            row.append(cell)
        matrix_data.append(row)

    matrix_df = pd.DataFrame(matrix_data,
                             index=[email_links[e] for e in users],
                             columns=[proj_id_links[pid] for pid in proj_ids])

    st.markdown("### User Role Matrix")
    st.write("Hover over icons to see role tooltips. Click emails or project IDs to explore.")
    st.write(matrix_df.to_html(escape=False), unsafe_allow_html=True)

# ---------------------------
# User Removal Tab
# ---------------------------
with tab2:
    emails = sorted(df_users["email"].unique())
    default_index = emails.index(selected_from_url) if selected_from_url in emails else 0
    selected_email = st.selectbox("Select user by email", emails, index=default_index)
    user_projects = df_users[df_users["email"] == selected_email]

    st.subheader(f"Projects for {selected_email}")
    selected_projects = st.multiselect(
        "Select projects to remove this user from:",
        user_projects["project"].tolist()
    )

    if st.button("Remove Selected Access", disabled=not selected_projects):
        for proj_name in selected_projects:
            proj_row = user_projects[user_projects["project"] == proj_name].iloc[0]
            proj_id = proj_row["project_id"]
            user_id = proj_row["user_id"]
            delete_url = f"{MANAGEMENT_API}/manage/projects/{proj_id}/users/{user_id}"
            res = requests.delete(delete_url, headers=headers)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            safe_headers = {k: ("***" if "Token" in k else v) for k, v in headers.items()}

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

    if st.session_state.audit_logs:
        st.subheader("Audit Log")
        for entry in reversed(st.session_state.audit_logs):
            st.text(entry)
