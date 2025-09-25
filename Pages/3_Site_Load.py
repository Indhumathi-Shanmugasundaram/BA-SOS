import streamlit as st
import mysql.connector
import pandas as pd
import io

def find_column_flexible(df, target_names):
    """
    Find column that matches any of the target names (case insensitive)
    Args:
        df: pandas DataFrame
        target_names: list of possible column names to match
    Returns:
        actual column name if found, None otherwise
    """
    df_columns_lower = [col.lower().strip() for col in df.columns]
    target_names_lower = [name.lower().strip() for name in target_names]
    
    for target in target_names_lower:
        for i, col_lower in enumerate(df_columns_lower):
            if target in col_lower or col_lower in target:
                return df.columns[i]
    return None

def validate_file_columns(file, filename, required_cols_sets):
    """
    Validate that uploaded file contains required columns
    Args:
        file: uploaded file object
        filename: name of the file
        required_cols_sets: list of tuples, each containing possible column names for a required field
    Returns:
        tuple: (is_valid, error_message, dataframe)
    """
    try:
        file.seek(0)
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        missing_columns = []
        for col_set in required_cols_sets:
            if not find_column_flexible(df, col_set):
                missing_columns.append(f"'{'/'.join(col_set)}'")
        
        if missing_columns:
            error_msg = f"Missing required columns: {', '.join(missing_columns)}. Available columns: {', '.join(df.columns.tolist())}"
            return False, error_msg, None
        
        file.seek(0)
        return True, "", df
    except Exception as e:
        return False, f"Error reading file: {str(e)}", None

st.set_page_config(
    page_title="Site Load Details",
    layout="wide",
    initial_sidebar_state="expanded"
)
if "page" not in st.session_state:
    st.session_state.page = "project_load"

if st.session_state.page == "optimizer":
    st.switch_page("pages/4_Optimize.py")
    
st.markdown("""
<style>
    div.stButton > button {
        background-color: #0066cc;
        color: white;
    }
    div.stButton > button:hover {
        background-color: #004c99;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state.page = "project_load"

def get_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='*******', #Enter password
        database='imdb'
    )

def get_project_ids():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT project_id FROM project_config WHERE status = 'c'")
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids

def get_project_description(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT project_description FROM project_config WHERE project_id = %s", (project_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else ""

def validate_wind_entries(entries):
    errors = {}
    for idx, entry in enumerate(entries):
        entry_errors = {}
        
        if not any([entry.get("manufacturer", ""), entry.get("model", ""), entry.get("capacity", ""), entry.get("filename", "")]):
            continue

        if not entry.get("manufacturer", "").strip():
            entry_errors["manufacturer"] = "Manufacturer is required"
        
        if not entry.get("model", "").strip():
            entry_errors["model"] = "Model is required"
        
        if not entry.get("capacity", "").strip():
            entry_errors["capacity"] = "Capacity is required"
        else:
            try:
                capacity = float(entry["capacity"])
                if capacity <= 0:
                    entry_errors["capacity"] = "Capacity must be a positive number"
            except ValueError:
                entry_errors["capacity"] = "Capacity must be a numeric value"


        if not entry.get("filename"):
            if st.session_state["wind_invalid_files"][idx]:
                entry_errors["filename"] = "Invalid file type. Only CSV or Excel files are allowed"
            else:
                entry_errors["filename"] = "Please upload a file"


        if entry_errors:
            errors[idx] = entry_errors
    return errors

def validate_solar_entries(entries):
    errors = {}
    for idx, entry in enumerate(entries):
        entry_errors = {}
        
        if not any([entry.get("manufacturer", ""), entry.get("model", ""), entry.get("capacity", ""), entry.get("filename", "")]):
            continue

        if not entry.get("manufacturer", "").strip():
            entry_errors["manufacturer"] = "Manufacturer is required"
        
        if not entry.get("model", "").strip():
            entry_errors["model"] = "Model is required"
        
        if not entry.get("capacity", "").strip():
            entry_errors["capacity"] = "Capacity is required"
        else:
            try:
                capacity = float(entry["capacity"])
                if capacity <= 0:
                    entry_errors["capacity"] = "Capacity must be a positive number"
            except ValueError:
                entry_errors["capacity"] = "Capacity must be a numeric value"

        if not entry.get("filename"):
            entry_errors["filename"] = "File is required"
        elif not entry["filename"].lower().endswith(('.csv', '.xlsx')):
            entry_errors["filename"] = "Only CSV or Excel files are allowed"

        if entry_errors:
            errors[idx] = entry_errors
    return errors

def validate_battery_entries(entries):
    errors = {}
    for idx, entry in enumerate(entries):
        entry_errors = {}
        
        if not any([entry.get("manufacturer", ""), entry.get("model", ""), entry.get("capacity", ""), entry.get("filename", "")]):
            continue

        if not entry.get("manufacturer", "").strip():
            entry_errors["manufacturer"] = "Manufacturer is required"
        
        if not entry.get("model", "").strip():
            entry_errors["model"] = "Model is required"
        
        if not entry.get("capacity", "").strip():
            entry_errors["capacity"] = "Capacity is required"
        else:
            try:
                capacity = float(entry["capacity"])
                if capacity <= 0:
                    entry_errors["capacity"] = "Capacity must be a positive number"
            except ValueError:
                entry_errors["capacity"] = "Capacity must be a numeric value"

        if not entry.get("filename"):
            entry_errors["filename"] = "File is required"
        elif not entry["filename"].lower().endswith(('.csv', '.xlsx')):
            entry_errors["filename"] = "Only CSV or Excel files are allowed"

        if entry_errors:
            errors[idx] = entry_errors
    return errors

def validate_demand_entries(entries):
    errors = {}
    for idx, entry in enumerate(entries):
        entry_errors = {}
        
        if not any([entry.get("manufacturer", ""), entry.get("model", ""), entry.get("capacity", ""), entry.get("filename", "")]):
            continue

        if not entry.get("manufacturer", "").strip():
            entry_errors["manufacturer"] = "Manufacturer is required"
        
        if not entry.get("model", "").strip():
            entry_errors["model"] = "Model is required"
        
        if not entry.get("capacity", "").strip():
            entry_errors["capacity"] = "Capacity is required"
        else:
            try:
                capacity = float(entry["capacity"])
                if capacity <= 0:
                    entry_errors["capacity"] = "Capacity must be a positive number"
            except ValueError:
                entry_errors["capacity"] = "Capacity must be a numeric value"

        if not entry.get("filename"):
            entry_errors["filename"] = "File is required"
        elif not entry["filename"].lower().endswith(('.csv', '.xlsx')):
            entry_errors["filename"] = "Only CSV or Excel files are allowed"

        if entry_errors:
            errors[idx] = entry_errors
    return errors

def get_next_profile_id():
    """Generate next profile ID by finding max ID across all profile tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    max_ids = []
    tables = ['wind_profile', 'solar_profile', 'battery_profile', 'demand_profile']
    
    for table in tables:
        cursor.execute(f"SELECT IFNULL(MAX(id), 0) FROM {table}")
        max_id = cursor.fetchone()[0]
        max_ids.append(max_id)
    
    conn.close()
    return max(max_ids) + 1

def save_all_profiles(project_id, wind_entries, solar_entries, battery_entries, demand_entries):
    errors = []
    success_messages = []
    
    if not project_id:
        return ["No project ID selected"], []
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        profile_id = st.session_state.profile_id
        
        wind_has_data = False
        for idx, entry in enumerate(wind_entries):
            if any([entry.get("manufacturer", ""), entry.get("model", ""), entry.get("capacity", ""), entry.get("filename", "")]):
                wind_has_data = True
                cursor.execute("""
                    INSERT INTO wind_profile (id, project_id, manufacturer, model, capacity_mwh, file_name)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    profile_id,
                    project_id,
                    entry.get("manufacturer", "") or None,
                    entry.get("model", "") or None,
                    float(entry["capacity"]) if entry.get("capacity") else None,
                    entry.get("filename", "") or None
                ))
                
                if entry.get("file"):
                    entry["file"].seek(0)
                    if entry["filename"].lower().endswith('.csv'):
                        df = pd.read_csv(entry["file"])
                    else:
                        df = pd.read_excel(entry["file"])
                    
                    datetime_col = find_column_flexible(df, ['datetime', 'date', 'time', 'timestamp', 'hour'])
                    generation_col = find_column_flexible(df, ['generation', 'gen', 'power', 'output'])
                    
                    if datetime_col and generation_col:
                        for _, row in df.iterrows():
                            try:
                                timestamp = pd.to_datetime(row[datetime_col])
                                generation = float(row[generation_col])
                                cursor.execute("""
                                    INSERT INTO wind_profile_data (project_id, profile_id, timestamp, generation)
                                    VALUES (%s, %s, %s, %s)
                                """, (project_id, profile_id, timestamp, generation))
                            except (ValueError, TypeError, pd.errors.ParserError) as e:
                                print(f"Skipping invalid row in wind data: {e}")
                                continue
        
        if not wind_has_data:
            cursor.execute("""
                INSERT INTO wind_profile (id, project_id, manufacturer, model, capacity_mwh, file_name)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (profile_id, project_id, None, None, None, None))
            
            cursor.execute("""
                INSERT INTO wind_profile_data (project_id, profile_id, timestamp, generation)
                VALUES (%s, %s, %s, %s)
            """, (project_id, profile_id, None, None))
        
        solar_has_data = False
        for idx, entry in enumerate(solar_entries):
            if any([entry.get("manufacturer", ""), entry.get("model", ""), entry.get("capacity", ""), entry.get("filename", "")]):
                solar_has_data = True
                cursor.execute("""
                    INSERT INTO solar_profile (id, project_id, manufacturer, model, capacity_mwh, file_name)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    profile_id,
                    project_id,
                    entry.get("manufacturer", "") or None,
                    entry.get("model", "") or None,
                    float(entry["capacity"]) if entry.get("capacity") else None,
                    entry.get("filename", "") or None
                ))
                
                if entry.get("file"):
                    entry["file"].seek(0)
                    if entry["filename"].lower().endswith('.csv'):
                        df = pd.read_csv(entry["file"])
                    else:
                        df = pd.read_excel(entry["file"])
                    
                    datetime_col = find_column_flexible(df, ['datetime', 'date', 'time', 'timestamp', 'hour'])
                    generation_col = find_column_flexible(df, ['generation', 'gen', 'power', 'output'])
                    
                    if datetime_col and generation_col:
                        for _, row in df.iterrows():
                            try:
                                timestamp = pd.to_datetime(row[datetime_col])
                                generation = float(row[generation_col])
                                cursor.execute("""
                                    INSERT INTO solar_profile_data (project_id, profile_id, timestamp, generation)
                                    VALUES (%s, %s, %s, %s)
                                """, (project_id, profile_id, timestamp, generation))
                            except (ValueError, TypeError, pd.errors.ParserError) as e:
                                print(f"Skipping invalid row in solar data: {e}")
                                continue
        
        if not solar_has_data:
            cursor.execute("""
                INSERT INTO solar_profile (id, project_id, manufacturer, model, capacity_mwh, file_name)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (profile_id, project_id, None, None, None, None))
            
            cursor.execute("""
                INSERT INTO solar_profile_data (project_id, profile_id, timestamp, generation)
                VALUES (%s, %s, %s, %s)
            """, (project_id, profile_id, None, None))
        
        battery_has_data = False
        for idx, entry in enumerate(battery_entries):
            if any([entry.get("manufacturer", ""), entry.get("model", ""), entry.get("capacity", ""), entry.get("filename", "")]):
                battery_has_data = True
                cursor.execute("""
                    INSERT INTO battery_profile (id, project_id, manufacturer, model, capacity_mwh, file_name)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    profile_id,
                    project_id,
                    entry.get("manufacturer", "") or None,
                    entry.get("model", "") or None,
                    float(entry["capacity"]) if entry.get("capacity") else None,
                    entry.get("filename", "") or None
                ))
                
                if entry.get("file"):
                    entry["file"].seek(0)
                    if entry["filename"].lower().endswith('.csv'):
                        df = pd.read_csv(entry["file"])
                    else:
                        df = pd.read_excel(entry["file"])
                    
                    datetime_col = find_column_flexible(df, ['datetime', 'date', 'time', 'timestamp', 'hour'])
                    generation_col = find_column_flexible(df, ['generation', 'gen', 'power', 'output', 'capacity'])
                    
                    if datetime_col and generation_col:
                        for _, row in df.iterrows():
                            try:
                                timestamp = pd.to_datetime(row[datetime_col])
                                generation = float(row[generation_col])
                                cursor.execute("""
                                    INSERT INTO battery_profile_data (project_id, profile_id, timestamp, generation)
                                    VALUES (%s, %s, %s, %s)
                                """, (project_id, profile_id, timestamp, generation))
                            except (ValueError, TypeError, pd.errors.ParserError) as e:
                                print(f"Skipping invalid row in battery data: {e}")
                                continue
        
        if not battery_has_data:
            cursor.execute("""
                INSERT INTO battery_profile (id, project_id, manufacturer, model, capacity_mwh, file_name)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (profile_id, project_id, None, None, None, None))
            
            cursor.execute("""
                INSERT INTO battery_profile_data (project_id, profile_id, timestamp, generation)
                VALUES (%s, %s, %s, %s)
            """, (project_id, profile_id, None, None))
        
        demand_has_data = False
        for idx, entry in enumerate(demand_entries):
            if entry.get("filename", ""):
                demand_has_data = True
                cursor.execute("""
                    INSERT INTO demand_profile (id, project_id, file_name)
                    VALUES (%s, %s, %s)
                """, (profile_id, project_id, entry.get("filename", "") or None))
                
                if entry.get("file"):
                    entry["file"].seek(0)
                    if entry["filename"].lower().endswith('.csv'):
                        df = pd.read_csv(entry["file"])
                    else:
                        df = pd.read_excel(entry["file"])
                    
                    datetime_col = find_column_flexible(df, ['hour', 'datetime', 'date', 'time', 'timestamp'])
                    demand_col = find_column_flexible(df, ['demand', 'load', 'consumption', 'usage'])
                    
                    if datetime_col and demand_col:
                        for _, row in df.iterrows():
                            try:
                                timestamp = pd.to_datetime(row[datetime_col])
                                demand = float(row[demand_col])
                                cursor.execute("""
                                    INSERT INTO demand_profile_data (project_id, profile_id, timestamp, demand)
                                    VALUES (%s, %s, %s, %s)
                                """, (project_id, profile_id, timestamp, demand))
                            except (ValueError, TypeError, pd.errors.ParserError) as e:
                                print(f"Skipping invalid row in demand data: {e}")
                                continue
        
        if not demand_has_data:
            cursor.execute("""
                INSERT INTO demand_profile (id, project_id, file_name)
                VALUES (%s, %s, %s)
            """, (profile_id, project_id, None))
            
            cursor.execute("""
                INSERT INTO demand_profile_data (project_id, profile_id, timestamp, demand)
                VALUES (%s, %s, %s, %s)
            """, (project_id, profile_id, None, None))
        
        conn.commit()
        success_messages.append("All profiles saved successfully!")
    except Exception as e:
        conn.rollback()
        errors.append(f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()
    
    return errors, success_messages

for key in ["wind_model_sets", "solar_model_sets", "battery_model_sets", "demand_model_sets"]:
    if key not in st.session_state:
        if key == "demand_model_sets":
            st.session_state[key] = [{
                "filename": "",
                "file": None
            }]
        else:
            st.session_state[key] = [{
                "manufacturer": "",
                "model": "",
                "capacity": "",
                "filename": "",
                "file": None
            }]

for key in ["wind_errors", "solar_errors", "battery_errors", "demand_errors"]:
    if key not in st.session_state:
        st.session_state[key] = {}

st.session_state["wind_invalid_files"] = [False] * len(st.session_state["wind_model_sets"])
st.session_state["solar_invalid_files"] = [False] * len(st.session_state["solar_model_sets"])
st.session_state["battery_invalid_files"] = [False] * len(st.session_state["battery_model_sets"])
st.session_state["demand_invalid_files"] = [False] * len(st.session_state["demand_model_sets"])

def add_model_set(key):
    st.session_state[key].append({
        "manufacturer": "",
        "model": "",
        "capacity": "",
        "filename": "",
        "file": None
    })
    if key == "wind_model_sets":
        st.session_state["wind_invalid_files"].append(False)
    elif key == "solar_model_sets":
        st.session_state["solar_invalid_files"].append(False)
    elif key == "battery_model_sets":
        st.session_state["battery_invalid_files"].append(False)

def delete_model_set(index, key):
    if len(st.session_state[key]) > 1:
        st.session_state[key].pop(index)
        if key == "wind_model_sets" and index in st.session_state["wind_errors"]:
            del st.session_state["wind_errors"][index]
            st.session_state["wind_invalid_files"].pop(index)
        elif key == "solar_model_sets" and index in st.session_state["solar_errors"]:
            del st.session_state["solar_errors"][index]
            st.session_state["solar_invalid_files"].pop(index)
        elif key == "battery_model_sets" and index in st.session_state["battery_errors"]:
            del st.session_state["battery_errors"][index]
            st.session_state["battery_invalid_files"].pop(index)

def add_demand_set():
    st.session_state["demand_model_sets"].append({
        "filename": "",
        "file": None
    })
    st.session_state["demand_invalid_files"].append(False)

def delete_demand_set(index):
    if len(st.session_state["demand_model_sets"]) > 1:
        st.session_state["demand_model_sets"].pop(index)
        if index in st.session_state["demand_errors"]:
            del st.session_state["demand_errors"][index]
        st.session_state["demand_invalid_files"].pop(index)

st.title("Site Load Details")

col1, col2, col3 = st.columns(3)
with col1:
    project_ids = get_project_ids()
    selected_project_id = st.selectbox("Project ID", project_ids)
with col2:
    description = get_project_description(selected_project_id)
    st.text_input("Project Description", value=description, disabled=True)
with col3:
    if "profile_id" not in st.session_state:
        st.session_state.profile_id = get_next_profile_id()
    st.text_input("Current Profile ID", value=str(st.session_state.profile_id), disabled=True)

tabs = st.tabs(["Wind Load Profile", "Solar Load Profile", "Battery", "Demand"])

with tabs[0]:
    st.markdown("### Wind Model Details")
    
    for idx, entry in enumerate(st.session_state["wind_model_sets"]):
        if idx > 0:
            st.markdown("---")
            
        col1, col2, col3 = st.columns(3)
        with col1:
            manufacturer = st.text_input(f"Manufacturer {idx+1} (Wind)", value=entry["manufacturer"], key=f"wind_manufacturer_{idx}")
            if idx in st.session_state["wind_errors"] and "manufacturer" in st.session_state["wind_errors"][idx]:
                st.error(st.session_state["wind_errors"][idx]["manufacturer"])
        with col2:
            model = st.text_input(f"Model {idx+1} (Wind)", value=entry["model"], key=f"wind_model_{idx}")
            if idx in st.session_state["wind_errors"] and "model" in st.session_state["wind_errors"][idx]:
                st.error(st.session_state["wind_errors"][idx]["model"])
        with col3:
            capacity = st.text_input(f"Capacity {idx+1} in MWh (Wind)", value=entry["capacity"], key=f"wind_capacity_{idx}")
            if idx in st.session_state["wind_errors"] and "capacity" in st.session_state["wind_errors"][idx]:
                st.error(st.session_state["wind_errors"][idx]["capacity"])

        st.session_state["wind_model_sets"][idx]["manufacturer"] = manufacturer
        st.session_state["wind_model_sets"][idx]["model"] = model
        st.session_state["wind_model_sets"][idx]["capacity"] = capacity

        file_col1, file_col2, file_col3 = st.columns([3, 2, 2])
        with file_col1:
            uploaded = st.file_uploader(f"Upload CSV {idx+1} (Wind)", type=["csv", "xlsx"], key=f"wind_file_{idx}")
            st.caption("📋 File should contain columns: 'datetime/hour' and 'generation'")
            if uploaded is None:
                st.session_state["wind_model_sets"][idx]["filename"] = ""
                st.session_state["wind_model_sets"][idx]["file"] = None
                st.session_state["wind_invalid_files"][idx] = False
            else:
                try:
                    valid_extensions = ['.csv', '.xlsx']
                    if not any(uploaded.name.lower().endswith(ext) for ext in valid_extensions):
                        st.error(f"Error: Only CSV or Excel files are allowed. You uploaded {uploaded.name}")
                        st.session_state["wind_invalid_files"][idx] = True
                        st.session_state["wind_model_sets"][idx]["filename"] = ""
                        st.session_state["wind_model_sets"][idx]["file"] = None
                    else:
                        content = uploaded.read()
                        file_obj = io.BytesIO(content)
                        
                        # Validate columns
                        required_cols = [
                            ['datetime', 'date', 'time', 'timestamp', 'hour'],
                            ['generation', 'gen', 'power', 'output']
                        ]
                        is_valid, error_msg, _ = validate_file_columns(file_obj, uploaded.name, required_cols)
                        
                        if not is_valid:
                            st.error(f"Column validation error: {error_msg}")
                            st.session_state["wind_invalid_files"][idx] = True
                            st.session_state["wind_model_sets"][idx]["filename"] = ""
                            st.session_state["wind_model_sets"][idx]["file"] = None
                        else:
                            st.session_state["wind_model_sets"][idx]["filename"] = uploaded.name
                            st.session_state["wind_model_sets"][idx]["file"] = file_obj
                            st.session_state["wind_invalid_files"][idx] = False
                except Exception as e:
                    st.error(f"Invalid file: {e}")
                    st.session_state["wind_invalid_files"][idx] = True
                    st.session_state["wind_model_sets"][idx]["filename"] = ""
                    st.session_state["wind_model_sets"][idx]["file"] = None
            if idx in st.session_state["wind_errors"] and "filename" in st.session_state["wind_errors"][idx]:
                st.error(st.session_state["wind_errors"][idx]["filename"])

        with file_col2:
            st.text_input(f"File Name {idx+1}", value=entry["filename"], key=f"wind_filename_{idx}", disabled=True)


        with file_col3:
            if entry["file"]:
                st.download_button(
                    label="Download",
                    data=entry["file"],
                    file_name=entry["filename"],
                    mime="text/csv",
                    key=f"wind_download_{idx}"
                )
        
        if entry["file"]:
            try:
                entry["file"].seek(0)
                if entry["filename"].lower().endswith('.csv'):
                    df = pd.read_csv(entry["file"])
                else:
                    df = pd.read_excel(entry["file"])
                st.dataframe(df.head(10), use_container_width=True, hide_index=True)
                entry["file"].seek(0)
            except Exception as e:
                st.error(f"Error previewing file: {e}")


        if idx > 0 and st.button("Delete", key=f"wind_delete_{idx}"):
            delete_model_set(idx, "wind_model_sets")
            st.rerun()

    col_space, btn_container = st.columns([3, 1])
    with btn_container:
        btn_container = st.columns([1])[0]

with tabs[1]:
    st.markdown("### Solar Model Details")
    for idx, entry in enumerate(st.session_state["solar_model_sets"]):
        if idx > 0:
            st.markdown("---")
            
        col1, col2, col3 = st.columns(3)
        with col1:
            manufacturer = st.text_input(f"Manufacturer {idx+1} (Solar)", value=entry["manufacturer"], key=f"solar_manufacturer_{idx}")
            if idx in st.session_state["solar_errors"] and "manufacturer" in st.session_state["solar_errors"][idx]:
                st.error(st.session_state["solar_errors"][idx]["manufacturer"])
        with col2:
            model = st.text_input(f"Model {idx+1} (Solar)", value=entry["model"], key=f"solar_model_{idx}")
            if idx in st.session_state["solar_errors"] and "model" in st.session_state["solar_errors"][idx]:
                st.error(st.session_state["solar_errors"][idx]["model"])
        with col3:
            capacity = st.text_input(f"Capacity {idx+1} in MWh (Solar)", value=entry["capacity"], key=f"solar_capacity_{idx}")
            if idx in st.session_state["solar_errors"] and "capacity" in st.session_state["solar_errors"][idx]:
                st.error(st.session_state["solar_errors"][idx]["capacity"])

        st.session_state["solar_model_sets"][idx]["manufacturer"] = manufacturer
        st.session_state["solar_model_sets"][idx]["model"] = model
        st.session_state["solar_model_sets"][idx]["capacity"] = capacity

        file_col1, file_col2, file_col3 = st.columns([3, 2, 2])
        with file_col1:
            uploaded = st.file_uploader(f"Upload CSV {idx+1} (Solar)", type=["csv", "xlsx"], key=f"solar_file_{idx}")
            st.caption("📋 File should contain columns: 'datetime/hour' and 'generation'")
            if uploaded is None:
                st.session_state["solar_model_sets"][idx]["filename"] = ""
                st.session_state["solar_model_sets"][idx]["file"] = None
                st.session_state["solar_invalid_files"][idx] = False
            else:
                try:
                    valid_extensions = ['.csv', '.xlsx']
                    if not any(uploaded.name.lower().endswith(ext) for ext in valid_extensions):
                        st.error(f"Error: Only CSV or Excel files are allowed. You uploaded {uploaded.name}")
                        st.session_state["solar_invalid_files"][idx] = True
                        st.session_state["solar_model_sets"][idx]["filename"] = ""
                        st.session_state["solar_model_sets"][idx]["file"] = None
                    else:
                        content = uploaded.read()
                        file_obj = io.BytesIO(content)
                        
                        # Validate columns
                        required_cols = [
                            ['datetime', 'date', 'time', 'timestamp', 'hour'],
                            ['generation', 'gen', 'power', 'output']
                        ]
                        is_valid, error_msg, _ = validate_file_columns(file_obj, uploaded.name, required_cols)
                        
                        if not is_valid:
                            st.error(f"Column validation error: {error_msg}")
                            st.session_state["solar_invalid_files"][idx] = True
                            st.session_state["solar_model_sets"][idx]["filename"] = ""
                            st.session_state["solar_model_sets"][idx]["file"] = None
                        else:
                            st.session_state["solar_model_sets"][idx]["filename"] = uploaded.name
                            st.session_state["solar_model_sets"][idx]["file"] = file_obj
                            st.session_state["solar_invalid_files"][idx] = False
                except Exception as e:
                    st.error(f"Invalid file: {e}")
                    st.session_state["solar_invalid_files"][idx] = True
                    st.session_state["solar_model_sets"][idx]["filename"] = ""
                    st.session_state["solar_model_sets"][idx]["file"] = None

            if idx in st.session_state["solar_errors"] and "filename" in st.session_state["solar_errors"][idx]:
                st.error(st.session_state["solar_errors"][idx]["filename"])

        with file_col2:
            st.text_input(f"File Name {idx+1}", value=entry["filename"], key=f"solar_filename_{idx}", disabled=True)


        with file_col3:
            if entry["file"]:
                st.download_button(
                    label="Download",
                    data=entry["file"],
                    file_name=entry["filename"],
                    mime="text/csv",
                    key=f"solar_download_{idx}"
                )

        if entry["file"]:
            try:
                entry["file"].seek(0)
                if entry["filename"].lower().endswith('.csv'):
                    df = pd.read_csv(entry["file"])
                else:
                    df = pd.read_excel(entry["file"])
                st.dataframe(df.head(10), use_container_width=True, hide_index=True)
                entry["file"].seek(0)
            except Exception as e:
                st.error(f"Error previewing file: {e}")

        if idx > 0 and st.button("Delete", key=f"solar_delete_{idx}"):
            delete_model_set(idx, "solar_model_sets")
            st.rerun()

    col_space, btn_container = st.columns([3, 1])
    with btn_container:
        btn_container = st.columns([1])[0]

with tabs[2]:
    st.markdown("### Battery Model Details")
    for idx, entry in enumerate(st.session_state["battery_model_sets"]):
        if idx > 0:
            st.markdown("---")
            
        col1, col2, col3 = st.columns(3)
        with col1:
            manufacturer = st.text_input(f"Manufacturer {idx+1} (Battery)", value=entry["manufacturer"], key=f"battery_manufacturer_{idx}")
            if idx in st.session_state["battery_errors"] and "manufacturer" in st.session_state["battery_errors"][idx]:
                st.error(st.session_state["battery_errors"][idx]["manufacturer"])
        with col2:
            model = st.text_input(f"Model {idx+1} (Battery)", value=entry["model"], key=f"battery_model_{idx}")
            if idx in st.session_state["battery_errors"] and "model" in st.session_state["battery_errors"][idx]:
                st.error(st.session_state["battery_errors"][idx]["model"])
        with col3:
            capacity = st.text_input(f"Capacity {idx+1} in MWh (Battery)", value=entry["capacity"], key=f"battery_capacity_{idx}")
            if idx in st.session_state["battery_errors"] and "capacity" in st.session_state["battery_errors"][idx]:
                st.error(st.session_state["battery_errors"][idx]["capacity"])

        st.session_state["battery_model_sets"][idx]["manufacturer"] = manufacturer
        st.session_state["battery_model_sets"][idx]["model"] = model
        st.session_state["battery_model_sets"][idx]["capacity"] = capacity

        file_col1, file_col2, file_col3 = st.columns([3, 2, 2])
        with file_col1:
            uploaded = st.file_uploader(f"Upload CSV {idx+1} (Battery)", type=["csv", "xlsx"], key=f"battery_file_{idx}")
            st.caption("📋 File should contain columns: 'datetime/hour' and 'generation'")
            if uploaded is None:
                st.session_state["battery_model_sets"][idx]["filename"] = ""
                st.session_state["battery_model_sets"][idx]["file"] = None
                st.session_state["battery_invalid_files"][idx] = False
            else:
                try:
                    valid_extensions = ['.csv', '.xlsx']
                    if not any(uploaded.name.lower().endswith(ext) for ext in valid_extensions):
                        st.error(f"Error: Only CSV or Excel files are allowed. You uploaded {uploaded.name}")
                        st.session_state["battery_invalid_files"][idx] = True
                        st.session_state["battery_model_sets"][idx]["filename"] = ""
                        st.session_state["battery_model_sets"][idx]["file"] = None
                    else:
                        content = uploaded.read()
                        file_obj = io.BytesIO(content)
                        
                        # Validate columns
                        required_cols = [
                            ['datetime', 'date', 'time', 'timestamp', 'hour'],
                            ['generation', 'gen', 'power', 'output', 'capacity']
                        ]
                        is_valid, error_msg, _ = validate_file_columns(file_obj, uploaded.name, required_cols)
                        
                        if not is_valid:
                            st.error(f"Column validation error: {error_msg}")
                            st.session_state["battery_invalid_files"][idx] = True
                            st.session_state["battery_model_sets"][idx]["filename"] = ""
                            st.session_state["battery_model_sets"][idx]["file"] = None
                        else:
                            st.session_state["battery_model_sets"][idx]["filename"] = uploaded.name
                            st.session_state["battery_model_sets"][idx]["file"] = file_obj
                            st.session_state["battery_invalid_files"][idx] = False
                except Exception as e:
                    st.error(f"Invalid file: {e}")
                    st.session_state["battery_invalid_files"][idx] = True
                    st.session_state["battery_model_sets"][idx]["filename"] = ""
                    st.session_state["battery_model_sets"][idx]["file"] = None

            if idx in st.session_state["battery_errors"] and "filename" in st.session_state["battery_errors"][idx]:
                st.error(st.session_state["battery_errors"][idx]["filename"])

        with file_col2:
            st.text_input(f"File Name {idx+1}", value=entry["filename"], key=f"battery_filename_{idx}", disabled=True)


        with file_col3:
            if entry["file"]:
                st.download_button(
                    label="Download",
                    data=entry["file"],
                    file_name=entry["filename"],
                    mime="text/csv",
                    key=f"battery_download_{idx}"
                )
                
        if entry["file"]:
            try:
                entry["file"].seek(0)
                if entry["filename"].lower().endswith('.csv'):
                    df = pd.read_csv(entry["file"])
                else:  # Excel file
                    df = pd.read_excel(entry["file"])
                st.dataframe(df.head(10), use_container_width=True, hide_index=True)
                entry["file"].seek(0)
            except Exception as e:
                st.error(f"Error previewing file: {e}")

        if idx > 0 and st.button("Delete", key=f"battery_delete_{idx}"):
            delete_model_set(idx, "battery_model_sets")
            st.rerun()

    col_space, btn_container = st.columns([3, 1])
    with btn_container:
        btn_container = st.columns([1])[0]

with tabs[3]:
    st.markdown("### Demand Details")
    for idx, entry in enumerate(st.session_state["demand_model_sets"]):
        if idx > 0:
            st.markdown("---")
            
        file_col1, file_col2, file_col3 = st.columns([3, 2, 2])
        with file_col1:
            uploaded = st.file_uploader(f"Upload Demand CSV {idx+1}", type=["csv", "xlsx"], key=f"demand_file_{idx}")
            st.caption("📋 File should contain columns: 'Hour/datetime' and 'Demand'")
            if uploaded is None:
                st.session_state["demand_model_sets"][idx]["filename"] = ""
                st.session_state["demand_model_sets"][idx]["file"] = None
                st.session_state["demand_invalid_files"][idx] = False
            else:
                try:
                    valid_extensions = ['.csv', '.xlsx']
                    if not any(uploaded.name.lower().endswith(ext) for ext in valid_extensions):
                        st.error(f"Error: Only CSV or Excel files are allowed. You uploaded {uploaded.name}")
                        st.session_state["demand_invalid_files"][idx] = True
                        st.session_state["demand_model_sets"][idx]["filename"] = ""
                        st.session_state["demand_model_sets"][idx]["file"] = None
                    else:
                        content = uploaded.read()
                        file_obj = io.BytesIO(content)
                        
                        # Validate columns
                        required_cols = [
                            ['hour', 'datetime', 'date', 'time', 'timestamp'],
                            ['demand', 'load', 'consumption', 'usage']
                        ]
                        is_valid, error_msg, _ = validate_file_columns(file_obj, uploaded.name, required_cols)
                        
                        if not is_valid:
                            st.error(f"Column validation error: {error_msg}")
                            st.session_state["demand_invalid_files"][idx] = True
                            st.session_state["demand_model_sets"][idx]["filename"] = ""
                            st.session_state["demand_model_sets"][idx]["file"] = None
                        else:
                            st.session_state["demand_model_sets"][idx]["filename"] = uploaded.name
                            st.session_state["demand_model_sets"][idx]["file"] = file_obj
                            st.session_state["demand_invalid_files"][idx] = False
                except Exception as e:
                    st.error(f"Invalid file: {e}")
                    st.session_state["demand_invalid_files"][idx] = True
                    st.session_state["demand_model_sets"][idx]["filename"] = ""
                    st.session_state["demand_model_sets"][idx]["file"] = None
            if idx in st.session_state["demand_errors"] and "filename" in st.session_state["demand_errors"][idx]:
                st.error(st.session_state["demand_errors"][idx]["filename"])

        with file_col2:
            st.text_input(f"File Name {idx+1}", value=entry["filename"], key=f"demand_filename_{idx}", disabled=True)

 
        with file_col3:
            if entry["file"]:
                st.download_button(
                    label="Download",
                    data=entry["file"],
                    file_name=entry["filename"],
                    mime="text/csv",
                    key=f"demand_download_{idx}"
                )

        if entry["file"]:
            try:
                entry["file"].seek(0)
                if entry["filename"].lower().endswith('.csv'):
                    df = pd.read_csv(entry["file"])
                else:  # Excel file
                    df = pd.read_excel(entry["file"])
                st.dataframe(df.head(10), use_container_width=True, hide_index=True)
                entry["file"].seek(0)
            except Exception as e:
                st.error(f"Error previewing file: {e}")

        if idx > 0 and st.button("Delete", key=f"demand_delete_{idx}"):
            delete_demand_set(idx)
            st.rerun()

    col_space, btn_container = st.columns([3, 1])
    with btn_container:
        btn_container = st.columns([1])[0]

def check_mandatory_files_uploaded():
    """Check if at least one demand file and at least one solar or wind file is uploaded"""
    demand_uploaded = False
    for entry in st.session_state["demand_model_sets"]:
        if entry.get("file") is not None:
            demand_uploaded = True
            break
    
    solar_or_wind_uploaded = False
    
    for entry in st.session_state["solar_model_sets"]:
        if entry.get("file") is not None:
            solar_or_wind_uploaded = True
            break
    
    # Check wind files if solar not found
    if not solar_or_wind_uploaded:
        for entry in st.session_state["wind_model_sets"]:
            if entry.get("file") is not None:
                solar_or_wind_uploaded = True
                break
    
    return demand_uploaded, solar_or_wind_uploaded

st.markdown("---")
col1, col2 = st.columns([3, 1])
with col2:
    if st.button("**Save All Profiles**", key="save_all_button", use_container_width=True):
        if not selected_project_id:
            st.error("Please select a Project ID")
        else:
            demand_uploaded, solar_or_wind_uploaded = check_mandatory_files_uploaded()
            
            if not demand_uploaded:
                st.warning("⚠️ Please upload demand file before saving.")
            elif not solar_or_wind_uploaded:
                st.warning("⚠️ Please upload at least one solar or wind profile file before saving.")
            else:
                st.session_state.profile_id = get_next_profile_id()
                
                errors, success_messages = save_all_profiles(
                    selected_project_id,
                    st.session_state["wind_model_sets"],
                    st.session_state["solar_model_sets"],
                    st.session_state["battery_model_sets"],
                    st.session_state["demand_model_sets"]
                )
                
                if errors:
                    for err in errors:
                        st.error(err)
                
                if success_messages:
                    for msg in success_messages:
                        st.success(msg)
                    