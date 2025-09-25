import streamlit as st
import mysql.connector
from datetime import datetime
import os
import sys

def nav_to(page):
    st.session_state.page = page

# Initialize page in session state if not present
if "page" not in st.session_state:
    st.session_state.page = "project_config"

# Check which page to display and import the appropriate module
if st.session_state.page == "3_Site_Load":
    import sys
    import importlib.util
    sys.path.append(os.path.dirname(__file__))
    
    # Use importlib to import a module with a name that starts with a number
    site_load_path = os.path.join(os.path.dirname(__file__), "3_Site_Load.py")
    spec = importlib.util.spec_from_file_location("site_load_module", site_load_path)
    site_load_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(site_load_module)
    
    st.stop()

def get_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='*******', #Enter password
        database='imdb'
    )

# Fetch dropdown values
def fetch_options(query):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    options = [row[0] for row in cursor.fetchall()]
    conn.close()
    return options

def fetch_state_name_code_map():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, code FROM states")
    result = cursor.fetchall()
    conn.close()
    return {name: code for name, code in result}

def project_exists(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM project_config WHERE project_id = %s", (project_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def insert_project(data):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO project_config (
            project_id, project_name, project_type, project_description,
            construction_year, operation_year, wind, solar, battery, hybrid,
            site_name, site_address, country, state, district, latitude, longitude, status, created
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    # Convert empty latitude/longitude to None
    processed_data = list(data)
    for i in [15, 16]:  # indices for latitude and longitude
        if processed_data[i] == '':
            processed_data[i] = None
    
    cursor.execute(query, tuple(processed_data))
    conn.commit()
    conn.close()

def update_project(data):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        UPDATE project_config SET
            project_name = %s,
            project_type = %s,
            project_description = %s,
            construction_year = %s,
            operation_year = %s,
            wind = %s,
            solar = %s,
            battery = %s,
            hybrid = %s,
            site_name = %s,
            site_address = %s,
            country = %s,
            state = %s,
            district = %s,
            latitude = %s,
            longitude = %s,
            status = %s,
            modified = %s
        WHERE project_id = %s
    """
    # Convert empty latitude/longitude to None
    processed_data = list(data)
    for i in [14, 15]:  # indices for latitude and longitude in update data
        if processed_data[i] == '':
            processed_data[i] = None
    
    cursor.execute(query, tuple(processed_data))
    conn.commit()
    conn.close()


st.header("Project Configuration")

# Fetch dropdown data
project_types = fetch_options("SELECT type FROM project_types")
years = [str(y) for y in range(2022, 2032)]
states = fetch_options("SELECT name FROM states")
state_code_map = fetch_state_name_code_map()

# Session state init
if "selected_state" not in st.session_state:
    st.session_state.selected_state = states[0]
if "show_modify_prompt" not in st.session_state:
    st.session_state.show_modify_prompt = False
if "pending_data" not in st.session_state:
    st.session_state.pending_data = None
if "show_save_reminder" not in st.session_state:
    st.session_state.show_save_reminder = False
if "project_saved" not in st.session_state:
    st.session_state.project_saved = False
if "modal_action" not in st.session_state:
    st.session_state.modal_action = None

# CSS styling
st.markdown("""
<style>
    .stApp {
        max-width: 100%;
    }
    .block-container {
        max-width: 100%;
        padding-top: 3rem;
        padding-bottom: 1rem;
    }
    .stForm {
        width: 100%;
        padding: 0;
        border-radius: 0;
    }
    .stTextArea textarea {
        min-height: 80px;
        max-height: 80px;
    }
    h1, h2 {
        font-size: 1.75rem;
        margin-bottom: 1rem;
        overflow-wrap: break-word;
    }
    div[data-testid="stForm"] {
        padding: 0 !important;
    }
    button[kind="secondaryFormSubmit"] {
        background-color: #f0f2f6;
        color: #31333F;
    }
    button[kind="primaryFormSubmit"] {
        background-color: #0068C9;
        color: white;
    }
    .stButton button {
        background-color: #0068C9;
        color: white;
        width: 100%;
    }
    div[data-testid="stSidebar"] {
        background-color: #0068C9;
        color: white;
    }
    div[data-testid="stSidebar"] button {
        background-color: transparent;
        color: white;
        border: none;
        text-align: left;
        padding: 10px;
    }
    /* Prevent text wrapping in input boxes */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    /* Custom dialog styling */
    .dialog-container {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    }
    .dialog-content {
        background-color: white;
        padding: 20px;
        border-radius: 5px;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
        max-width: 500px;
        width: 100%;
    }
    .dialog-title {
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .dialog-buttons {
        display: flex;
        justify-content: flex-end;
        margin-top: 15px;
        gap: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Project form
with st.form("project_form", border=False):
    st.markdown("### Project Details")
    col1, col2, col3 = st.columns([0.9, 1.3, 0.9])
    with col1:
        project_id = st.text_input("Project ID *")#, value="ISN-ETS: SECI-2023-TN000020"
        project_type = st.selectbox("Project Type *", project_types)
    with col2:
        project_name = st.text_input("Project Name *")#, value="Supply of 800 MW FDP ISTSconnected (RE) Power Projects"
        project_description = st.text_area("Project Description", height=80)#, value="Supply of 800 MW Firm and Dispatchable Power from ISTSconnected Renewable Energy (RE) Power Projects in India."
    with col3:
        construction_year = st.selectbox("Construction Year *", years)
        operation_year = st.selectbox("Operation Year *", years)

    st.markdown("### RE Component")
    re_cols = st.columns(4)
    with re_cols[0]: wind = st.checkbox("Wind", value=True)
    with re_cols[1]: solar = st.checkbox("Solar", value=True)
    with re_cols[2]: battery = st.checkbox("Battery", value=True)
    with re_cols[3]: hybrid = st.checkbox("Hybrid", value=False)

    st.markdown("### Site Information")
    site_col1, site_col2, site_col3, site_col4 = st.columns(4)
    with site_col1: site_name = st.text_input("Site Name", value="Kathura")
    with site_col2: site_address = st.text_input("Site Address")
    with site_col3: country = st.selectbox("Country", ["India"], index=0)
    with site_col4: st.session_state.selected_state = st.selectbox("State", states, key="state_select")

    site_row2_col1, site_row2_col2, site_row2_col3, site_row2_col4 = st.columns(4)
    with site_row2_col1: district = st.text_input("District")
    # Validate latitude and longitude to accept only numeric values
    with site_row2_col2: 
        latitude = st.text_input("Latitude", help="Enter a decimal or integer value")
        if latitude and not (latitude.replace('.', '', 1).replace('-', '', 1).isdigit() or latitude == ''):
            st.error("Latitude must be a numeric value")
    with site_row2_col3: 
        longitude = st.text_input("Longitude", help="Enter a decimal or integer value")
        if longitude and not (longitude.replace('.', '', 1).replace('-', '', 1).isdigit() or longitude == ''):
            st.error("Longitude must be a numeric value")

    # Button layout with Save and Confirm
    save_col1, save_col2, save_col3 = st.columns([6, 1, 1])
    with save_col2:
        save_button = st.form_submit_button("**Save**", use_container_width=True, type="primary")
    with save_col3:
        confirm_button = st.form_submit_button("**Confirm**", use_container_width=True, type="primary")

    # Helper function to validate input fields
    def validate_input():
        # Validate mandatory fields
        if not project_id or not project_name or not project_type or not construction_year or not operation_year:
            st.error("Please fill in all mandatory fields: Project ID, Name, Type, Construction & Operation Year.")
            return False
        # Validate latitude and longitude format (no need for duplicate message)
        elif (latitude and not latitude.replace('.', '', 1).replace('-', '', 1).isdigit()) or \
             (longitude and not longitude.replace('.', '', 1).replace('-', '', 1).isdigit()):
            return False
        return True

    # Save button logic
    if save_button:
        if validate_input():
            # Check if project exists
            if project_exists(project_id):
                # Update existing project
                update_data = (
                    project_name, project_type, project_description,
                    construction_year, operation_year, int(wind), int(solar), int(battery), int(hybrid),
                    site_name, site_address, country, st.session_state.selected_state, district,
                    latitude, longitude, "O", datetime.now(), project_id
                )
                update_project(update_data)
                st.success("Project updated successfully!")
            else:
                # Insert new project
                insert_data = (
                    project_id, project_name, project_type, project_description,
                    construction_year, operation_year, int(wind), int(solar), int(battery), int(hybrid),
                    site_name, site_address, country, st.session_state.selected_state, district,
                    latitude, longitude, "O", datetime.now()
                )
                insert_project(insert_data)
                st.success("Project configuration saved successfully!")
            
            st.session_state.project_saved = True
    
    # Confirm button logic            
    if confirm_button:
        if not st.session_state.project_saved:
            st.warning("Please save the project before confirming.")
            st.session_state.show_save_reminder = True
        else:
            # Update the project status to 'C' (confirmed)
            confirm_data = (
                project_name, project_type, project_description,
                construction_year, operation_year, int(wind), int(solar), int(battery), int(hybrid),
                site_name, site_address, country, st.session_state.selected_state, district,
                latitude, longitude, "C", datetime.now(), project_id
            )
            update_project(confirm_data)
            st.success("Project confirmed successfully!")
            st.session_state.project_saved = False

# Show save reminder as a proper modal if needed
if st.session_state.show_save_reminder:
    reminder_modal_html = """
    <div class="dialog-container" id="reminder-dialog">
        <div class="dialog-content">
            <div class="dialog-title">Save Required</div>
            <p>Please save the project before confirming.</p>
            <div class="dialog-buttons">
                <button onclick="dismissReminder()" style="background-color: #0068C9; color: white; border: none; padding: 5px 10px; border-radius: 3px;">OK</button>
            </div>
        </div>
    </div>
    
    <script>
        function dismissReminder() {
            const data = {
                dismissed: true
            };
            
            // Send message to Streamlit
            const stringifiedData = JSON.stringify(data);
            
            window.parent.postMessage({
                type: "streamlit:setComponentValue",
                value: stringifiedData
            }, "*");
            
            // Remove the dialog
            document.getElementById('reminder-dialog').style.display = 'none';
        }
    </script>
    """
    
    # Use Streamlit component for modal
    reminder_response = st.components.v1.html(reminder_modal_html, height=0)
    
    # Handle response
    if reminder_response:
        try:
            response_data = eval(reminder_response)
            if response_data.get('dismissed'):
                st.session_state.show_save_reminder = False
                st.rerun()
        except:
            pass
    
    # # Fallback button
    # if st.button("Dismiss Warning"):
    #     st.session_state.show_save_reminder = False
    #     st.rerun()