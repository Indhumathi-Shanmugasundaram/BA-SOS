import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error

st.title("Battery Storage Inputs & LCOS Calculator")

# LCOS calculation function (moved from separate model file)
def calculate_lcos(
    capital_cost,
    o_and_m_pct,
    storage_duration,
    roundtrip_efficiency,
    depth_of_discharge,
    storage_cycles_per_year,
    cycle_life
):
    """
    Calculates the Levelized Cost of Storage (LCOS)

    Parameters are expected in proper units:
    - capital_cost: INR/kWh
    - o_and_m_pct: in decimal (e.g. 0.01 for 1%)
    - storage_duration: hours
    - roundtrip_efficiency: in decimal
    - depth_of_discharge: in decimal
    - storage_cycles_per_year: number
    - cycle_life: number

    Returns:
    - LCOS in INR/kWh
    """
    try:
        o_and_m_cost = capital_cost * o_and_m_pct * storage_duration
        total_energy_throughput = (
            storage_cycles_per_year * depth_of_discharge * roundtrip_efficiency * cycle_life
        )
        lcos = (capital_cost + o_and_m_cost) / total_energy_throughput
        return round(lcos, 2)
    except Exception as e:
        return f"LCOS calculation error: {e}"

# Database connection function with hardcoded credentials
def create_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='*******', #Enter password
            database='imdb'
        )
        return connection
    except Error as e:
        st.error(f"Error connecting to MySQL Database: {e}")
        return None

# Function to save inputs to database
def save_inputs(project_id, run_number, capex, o_and_m_pct, storage_duration, efficiency, dod, cycles_per_year, cycle_life):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
            # Use INSERT ... ON DUPLICATE KEY UPDATE to handle existing records
            query = """
            INSERT INTO besos_lcos_in (
                project_id, run_number, battery_pack_capital_cost, o_and_m_pct, 
                storage_duration, roundtrip_efficiency, depth_of_discharge, 
                cycles_per_year, cycle_life
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                battery_pack_capital_cost = VALUES(battery_pack_capital_cost),
                o_and_m_pct = VALUES(o_and_m_pct),
                storage_duration = VALUES(storage_duration),
                roundtrip_efficiency = VALUES(roundtrip_efficiency),
                depth_of_discharge = VALUES(depth_of_discharge),
                cycles_per_year = VALUES(cycles_per_year),
                cycle_life = VALUES(cycle_life)
            """
            values = (project_id, run_number, capex, o_and_m_pct, storage_duration, 
                     efficiency, dod, cycles_per_year, cycle_life)
            
            cursor.execute(query, values)
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Error as e:
            st.error(f"Error saving inputs to database: {e}")
            if connection:
                connection.close()
            return False
    return False

# Function to save output to database
def save_output(project_id, run_number, lcos_value):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
            # Use INSERT ... ON DUPLICATE KEY UPDATE to handle existing records
            query = """
            INSERT INTO besos_lcos_out (
                project_id, run_number, lcos_value
            ) VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                lcos_value = VALUES(lcos_value)
            """
            values = (project_id, run_number, lcos_value)
            
            cursor.execute(query, values)
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Error as e:
            st.error(f"Error saving output to database: {e}")
            if connection:
                connection.close()
            return False
    return False

# Get project_id and run_number from session state (captured from previous pages)
if 'project_id' not in st.session_state:
    st.error("Project ID not found. Please go back to the Configure Optimizer page.")
    st.stop()
if 'run_number' not in st.session_state:
    st.error("Run number not found. Please go back to the Configure Optimizer page.")
    st.stop()

project_id = st.session_state.project_id
run_number = st.session_state.run_number

# Display project information
st.info(f"**Project ID:** {project_id} | **Run Number:** {run_number}")

# Sample battery storage inputs
storage_data = {
    "Parameter": [
        "Battery pack capital cost (INR/kWh)",
        "O&M cost (% of capex per year)",
        "Storage duration (hr)",
        "Roundtrip Efficiency (%)",
        "Depth of Discharge (%)",
        "Cycles per Year",
        "Cycle Life (cycles)"
    ],
    "Value": [20000, 1, 4, 97, 80, 730, 4000]
}

# Display editable AgGrid-style table
st.subheader("Battery Storage Assumptions")
storage_df = pd.DataFrame(storage_data)
storage_df.set_index("Parameter", inplace=True)
storage_df["Value"] = st.data_editor(storage_df["Value"])

# Extract values
capex = float(storage_df.loc["Battery pack capital cost (INR/kWh)", "Value"])
o_and_m_pct = float(storage_df.loc["O&M cost (% of capex per year)", "Value"]) / 100
storage_duration = float(storage_df.loc["Storage duration (hr)", "Value"])
efficiency = float(storage_df.loc["Roundtrip Efficiency (%)", "Value"]) / 100
dod = float(storage_df.loc["Depth of Discharge (%)", "Value"]) / 100
cycles_per_year = float(storage_df.loc["Cycles per Year", "Value"])
cycle_life = float(storage_df.loc["Cycle Life (cycles)", "Value"])

st.markdown(
    """
    <style>
    .stButton > button {
        background-color: #0066cc;
        color: white;
        float: right;
        margin-right: 0;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

if st.button("Calculate LCOS"):
    # Calculate LCOS
    result = calculate_lcos(
        capital_cost=capex,
        o_and_m_pct=o_and_m_pct,
        storage_duration=storage_duration,
        roundtrip_efficiency=efficiency,
        depth_of_discharge=dod,
        storage_cycles_per_year=cycles_per_year,
        cycle_life=cycle_life
    )
    
    # Save inputs to database
    input_saved = save_inputs(
        project_id=project_id,
        run_number=run_number,
        capex=capex,
        o_and_m_pct=o_and_m_pct,
        storage_duration=storage_duration,
        efficiency=efficiency,
        dod=dod,
        cycles_per_year=cycles_per_year,
        cycle_life=cycle_life
    )
    
    if input_saved:
        # Save output to database
        output_saved = save_output(
            project_id=project_id,
            run_number=run_number,
            lcos_value=result
        )
        
        if output_saved:
            st.success("Data saved successfully to database!")
        else:
            st.error("Failed to save output to database")
    else:
        st.error("Failed to save inputs to database")

    # Display result
    st.subheader("Levelized Cost of Storage")
    st.metric("LCOS (INR/kWh)", value=result)