# project_summary.py
import streamlit as st
import pandas as pd
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='*******', #Enter password
        database='imdb'
    )

# --- Fetch project summary data with optional filters ---
def get_project_summary(project_type=None, project_name=None):
    query = """
        SELECT 
            project_id, project_name, project_type, 
            construction_year, operation_year, 
            state, district, site_name, status
        FROM project_config
        WHERE (%s IS NULL OR project_type = %s)
        AND (%s IS NULL OR project_name LIKE %s)
    """
    conn = get_connection()
    cursor = conn.cursor()
    name_like = f"%{project_name}%" if project_name else None
    cursor.execute(query, (project_type, project_type, name_like, name_like))
    results = cursor.fetchall()
    conn.close()
    return results

# --- Fetch project types from DB ---
def fetch_project_types():
    query = "SELECT type FROM project_types"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    types = [row[0] for row in cursor.fetchall()]
    conn.close()
    return types

# --- Fetch all project names for suggestions ---
def fetch_project_names():
    query = "SELECT DISTINCT project_name FROM project_config"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return names

# --- Convert results to DataFrame ---
def build_dataframe(rows):
    columns = ["Project Id", "Project Name", "Project Type", 
               "Construction Year", "Operation Year", 
               "State", "District", "Site", "Status"]
    return pd.DataFrame(rows, columns=columns)

# --- Main UI ---
st.set_page_config(page_title="Project Summary", layout="wide")

# Custom CSS
st.markdown("""
    <style>
        .stApp { max-width: 100%; }
        .block-container { max-width: 100%; padding-top: 3rem; padding-bottom: 1rem; }
        /* Modify sidebar button style */
        .stButton button { background-color: #0068C9; color: white; border: none; padding: 8px 12px; border-radius: 4px; text-align: left; width: 100%; }
        .project-id-link { color: #0068C9; font-weight: 600; text-decoration: underline; cursor: pointer; }
        /* Fix search button width */
        .search-button button { width: auto !important; }
        /* Customize table appearance */
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 14px; }
        th { background-color: #f0f0f0 !important; color: #000; font-weight: 600; padding: 10px; border: 1px solid #dee2e6; text-align: left; }
        td { padding: 10px; border: 1px solid #dee2e6; text-align: left; }
        tr:hover { color: #FFCC00; }
        /* Download button styling */
        .download-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background-color: #4CAF50;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            text-decoration: none;
            font-size: 14px;
            margin-top: 10px;
            border: none;
            cursor: pointer;
        }
        .download-btn:hover {
            background-color: #45a049;
        }
    </style>
""", unsafe_allow_html=True)

# Header and title
st.markdown("""
    <h3 style='margin-bottom: 0;'>Project Summary</h3>
""", unsafe_allow_html=True)


# Search bar with filters
project_types = fetch_project_types()
project_types.insert(0, "--Select--")
project_names = fetch_project_names()

with st.container():
    # st.markdown("##### Search Criteria")
    col1, col2, col3 = st.columns([2, 4, 2])
    with col1:
        selected_type = st.selectbox("Project Type", options=project_types, key="project_type_select")
    with col2:
        selected_name = st.text_input("Project Name")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        # Make search button smaller using custom CSS class
        search_clicked = st.button("Search", key="search_btn", use_container_width=False)
        st.markdown('<style>.stButton button#search_btn { width: auto !important; }</style>', unsafe_allow_html=True)

# Create Project Button (smaller size)
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("Create Project", key="create_project_btn", use_container_width=False):
        st.session_state.project_id = None
        st.session_state.page = "project_config"
        # Use the correct path format for Streamlit navigation to the project config page
        st.switch_page("pages/2_Project_configuration.py")
    st.markdown('<style>.stButton button#create_project_btn { width: auto !important; }</style>', unsafe_allow_html=True)

# Filter results if search was triggered
filtered_rows = get_project_summary(
    project_type=None if selected_type == "--Select--" else selected_type,
    project_name=None if selected_name == "" else selected_name
)
df = build_dataframe(filtered_rows)

# Display table using st.dataframe for interactive features
if not df.empty:
    # Display the interactive dataframe
    st.dataframe(df, use_container_width=True, hide_index=True)
    
else:
    st.info("No matching projects found.")

st.caption(f"Showing 1 to {len(df)} of {len(df)} entries")

# Add JavaScript to handle redirection after session state is set
st.markdown("""
<script>
// Listen for session state changes
window.addEventListener('message', function(event) {
    if (event.data.type === 'streamlit:componentReady') {
        // Component is ready, now we can listen for session state changes
        const data = event.data.data;
        if (data && data.project_id) {
            // Redirect to the configuration page
            window.location.href = 'pages/2_Project_configuration';
        }
    }
});
</script>
""", unsafe_allow_html=True)