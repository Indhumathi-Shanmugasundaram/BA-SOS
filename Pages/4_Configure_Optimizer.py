import streamlit as st
import mysql.connector
from datetime import datetime
import os
import pandas as pd
import sys
import math
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'optimization'))
from optimization.capacity_planning_lp import optimize_generation_capacity

default_inputs = {
    "Parameter": [
        "System Capital Cost (Per KW)", "Capital Subsidy (Per KW)", "Plant Size (KW)",
        "Project Life of Plant (Years)", "Capacity Utilization Factor (%)", "Auxiliary Consumption (%)",
        "Discount Rate (%)", "Equity (%)", "Return on Equity (%)", "Loan Tenure (years)",
        "Moratorium (years)", "Interest on Loan (%)", "Operation and Maintenance Expenses in year 1 (%)",
        "Annual increase in Operation and Maintenance expenses (%)", "Insurance(%) of depreciated asset value)",
        "Working Capital - O & M (months)", "Working Capital - Receivables (months)",
        "Interest on Working Capital (%)", "n1 years", "Depreciation rate for the first n1 years (%)",
        "Percentage of capital cost on which depreciation applies (%)",
        "Annual Solar Panel Degradation (%)", "Grid Availability Factor (%)", "Inverter/Turbine Capacity(in kw)"
    ],
    "Solar": [33500, 0, 1000, 25, 19, 0, 9.53, 30, 17.60, 10, 1, 10.55, 1.40, 5.72, 0.35, 1, 2, 11.55, 25, 3.60, 95, 2, 95, 1000],
    "Wind": [52500, 0, 1000, 25, 29.15, 0, 9.53, 30, 17.60, 10, 1, 10.55, 0.968, 5.72, 0.64, 1, 2, 11.55, 25, 3.60, 85, 0, 95, 1000]
}

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
    cursor.execute("SELECT project_id FROM project_config WHERE status = 'C'")
    projects = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return projects

def get_next_run_number(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(run_number) FROM run_config WHERE project_id = %s", (project_id,))
    max_run = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    return 0 if max_run is None else max_run + 1

def save_general_inputs(project_id, run_number, tech_data, profile_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO Besos_gen_param_in (
            project_id, run_number, profile_id, technology, 
            system_capex, capex_subsidy, plant_size_kw,
            plant_life_years, cuf, aux_consumption,
            discount_rate, equity, return_on_equity,
            loan_tenure, moratorium, loan_interest,
            opex_year1, opex_growth, insurance,
            wc_om_months, wc_receivables_months, wc_interest,
            n1_years, depreciation_n1, depreciation_applicable_capex_pct,
            solar_degradation, grid_availability, inverter_turbine_capacity, run_date
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON DUPLICATE KEY UPDATE
            profile_id = VALUES(profile_id),
            system_capex = VALUES(system_capex),
            capex_subsidy = VALUES(capex_subsidy),
            plant_size_kw = VALUES(plant_size_kw),
            plant_life_years = VALUES(plant_life_years),
            cuf = VALUES(cuf),
            aux_consumption = VALUES(aux_consumption),
            discount_rate = VALUES(discount_rate),
            equity = VALUES(equity),
            return_on_equity = VALUES(return_on_equity),
            loan_tenure = VALUES(loan_tenure),
            moratorium = VALUES(moratorium),
            loan_interest = VALUES(loan_interest),
            opex_year1 = VALUES(opex_year1),
            opex_growth = VALUES(opex_growth),
            insurance = VALUES(insurance),
            wc_om_months = VALUES(wc_om_months),
            wc_receivables_months = VALUES(wc_receivables_months),
            wc_interest = VALUES(wc_interest),
            n1_years = VALUES(n1_years),
            depreciation_n1 = VALUES(depreciation_n1),
            depreciation_applicable_capex_pct = VALUES(depreciation_applicable_capex_pct),
            solar_degradation = VALUES(solar_degradation),
            grid_availability = VALUES(grid_availability),
            inverter_turbine_capacity = VALUES(inverter_turbine_capacity),
            run_date = VALUES(run_date)
    """
    
    solar_degradation_value = tech_data.get("solar_degradation", 0)
    inverter_turbine_capacity_value = tech_data.get("inverter_turbine_capacity", 1)
    
    values = (
        project_id, run_number, profile_id, tech_data["technology"],
        tech_data["system_capex"], tech_data["capex_subsidy"], tech_data["plant_size_kw"],
        tech_data["plant_life_years"], tech_data["cuf"], tech_data["aux_consumption"],
        tech_data["discount_rate"], tech_data["equity"], tech_data["return_on_equity"],
        tech_data["loan_tenure"], tech_data["moratorium"], tech_data["loan_interest"],
        tech_data["opex_year1"], tech_data["opex_growth"], tech_data["insurance"],
        tech_data["wc_om_months"], tech_data["wc_receivables_months"], tech_data["wc_interest"],
        tech_data["n1_years"], tech_data["depreciation_n1"], tech_data["depreciation_applicable_capex_pct"],
        solar_degradation_value, tech_data["grid_availability"], inverter_turbine_capacity_value, datetime.now()
    )
    
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

def save_tech_inputs(project_id, run_number, tech_data, profile_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO besos_re_tech_in (
            project_id, run_number, profile_id,
            wind_cuf, wind_grid, wind_deg,
            solar_cuf, solar_grid, solar_deg,
            battery_eff, battery_dod
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON DUPLICATE KEY UPDATE
            profile_id = VALUES(profile_id),
            wind_cuf = VALUES(wind_cuf),
            wind_grid = VALUES(wind_grid),
            wind_deg = VALUES(wind_deg),
            solar_cuf = VALUES(solar_cuf),
            solar_grid = VALUES(solar_grid),
            solar_deg = VALUES(solar_deg),
            battery_eff = VALUES(battery_eff),
            battery_dod = VALUES(battery_dod)
    """
    
    values = (
        project_id, run_number, profile_id,
        tech_data["wind_cuf"], tech_data["wind_grid"], tech_data["wind_deg"],
        tech_data["solar_cuf"], tech_data["solar_grid"], tech_data["solar_deg"],
        tech_data.get("battery_eff", 0), tech_data.get("battery_dod", 0)
    )
    
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

def save_economics_inputs(project_id, run_number, econ_data, profile_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO besos_re_economics_in (
            project_id, run_number, profile_id,
            wind_capex, wind_om,
            solar_capex, solar_om,
            battery_capex, battery_om,
            insurance
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON DUPLICATE KEY UPDATE
            profile_id = VALUES(profile_id),
            wind_capex = VALUES(wind_capex),
            wind_om = VALUES(wind_om),
            solar_capex = VALUES(solar_capex),
            solar_om = VALUES(solar_om),
            battery_capex = VALUES(battery_capex),
            battery_om = VALUES(battery_om),
            insurance = VALUES(insurance)
    """
    
    values = (
        project_id, run_number, profile_id,
        econ_data["wind_capex"], econ_data["wind_om"],
        econ_data["solar_capex"], econ_data["solar_om"],
        econ_data.get("battery_capex", 0), econ_data.get("battery_om", 0),
        econ_data["insurance"]
    )
    
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

def save_financials_inputs(project_id, run_number, fin_data, profile_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO besos_re_financials_in (
            project_id, run_number, profile_id,
            equity_pct, depreciation_year,
            ppa_price, loan_tenure,
            project_life, penalty,
            loan_interest, inflation_rate,
            excess_gen_price
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON DUPLICATE KEY UPDATE
            profile_id = VALUES(profile_id),
            equity_pct = VALUES(equity_pct),
            depreciation_year = VALUES(depreciation_year),
            ppa_price = VALUES(ppa_price),
            loan_tenure = VALUES(loan_tenure),
            project_life = VALUES(project_life),
            penalty = VALUES(penalty),
            loan_interest = VALUES(loan_interest),
            inflation_rate = VALUES(inflation_rate),
            excess_gen_price = VALUES(excess_gen_price)
    """
    
    values = (
        project_id, run_number, profile_id,
        fin_data["equity_pct"], fin_data["depreciation_year"],
        fin_data["ppa_price"], fin_data["loan_tenure"],
        fin_data["project_life"], fin_data["penalty"],
        fin_data["loan_interest"], fin_data["inflation_rate"],
        fin_data["excess_gen_price"]
    )
    
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

def save_run(project_id, run_number, run_date):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO run_config (project_id, run_number, run_date)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE run_date = VALUES(run_date)
    """
    if isinstance(run_date, datetime):
        formatted_date = run_date
    else:
        formatted_date = datetime.combine(run_date, datetime.min.time())
        
    cursor.execute(query, (project_id, run_number, formatted_date))
    conn.commit()
    cursor.close()
    conn.close()

def get_saved_general_inputs(project_id, run_number, technology):
    """
    Retrieves previously saved general inputs for a specific project, run, and technology
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT * FROM Besos_gen_param_in 
        WHERE project_id = %s AND run_number = %s AND technology = %s
    """
    
    cursor.execute(query, (project_id, run_number, technology))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result

def get_saved_tech_inputs(project_id, run_number):
    """
    Retrieves previously saved technical inputs for a specific project and run
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT * FROM besos_re_tech_in 
        WHERE project_id = %s AND run_number = %s
    """
    
    cursor.execute(query, (project_id, run_number))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result

def get_saved_economics_inputs(project_id, run_number):
    """
    Retrieves previously saved economics inputs for a specific project and run
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT * FROM besos_re_economics_in 
        WHERE project_id = %s AND run_number = %s
    """
    
    cursor.execute(query, (project_id, run_number))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result

def get_saved_financials_inputs(project_id, run_number):
    """
    Retrieves previously saved financials inputs for a specific project and run
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT * FROM besos_re_financials_in 
        WHERE project_id = %s AND run_number = %s
    """
    
    cursor.execute(query, (project_id, run_number))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result

def load_saved_inputs_to_session(project_id, run_number):
    """
    Load all previously saved inputs into session state for use in other pages
    """
    technologies = ["Solar", "Wind", "BESS"]
    general_inputs = {}
    
    for tech in technologies:
        tech_data = get_saved_general_inputs(project_id, run_number, tech)
        if tech_data:
            general_inputs[tech] = tech_data
    
    tech_inputs = get_saved_tech_inputs(project_id, run_number)
    
    economics_inputs = get_saved_economics_inputs(project_id, run_number)
    
    financials_inputs = get_saved_financials_inputs(project_id, run_number)

    if 'saved_project_inputs' not in st.session_state:
        st.session_state.saved_project_inputs = {}
        
    st.session_state.saved_project_inputs = {
        'project_id': project_id,
        'run_number': run_number,
        'general_inputs': general_inputs,
        'tech_inputs': tech_inputs,
        'economics_inputs': economics_inputs,
        'financials_inputs': financials_inputs
    }

    st.session_state['project_id'] = project_id
    st.session_state['run_number'] = run_number
    
    return True
def get_profile_data(project_id, profile_id):
    """
    Retrieve profile data for demand, solar, and wind generation
    Returns DataFrames with hourly data
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get demand data
    demand_query = """
        SELECT timestamp, demand 
        FROM demand_profile_data 
        WHERE project_id = %s AND profile_id = %s 
        ORDER BY timestamp
    """
    cursor.execute(demand_query, (project_id, profile_id))
    demand_data = cursor.fetchall()
    demand_df = pd.DataFrame(demand_data)
    
    # Get solar generation data
    solar_query = """
        SELECT timestamp, generation 
        FROM solar_profile_data 
        WHERE project_id = %s AND profile_id = %s 
        ORDER BY timestamp
    """
    cursor.execute(solar_query, (project_id, profile_id))
    solar_data = cursor.fetchall()
    solar_df = pd.DataFrame(solar_data)
    
    # Get wind generation data
    wind_query = """
        SELECT timestamp, generation 
        FROM wind_profile_data 
        WHERE project_id = %s AND profile_id = %s 
        ORDER BY timestamp
    """
    cursor.execute(wind_query, (project_id, profile_id))
    wind_data = cursor.fetchall()
    wind_df = pd.DataFrame(wind_data)
    
    cursor.close()
    conn.close()
    
    return demand_df, solar_df, wind_df

def save_plant_size(project_id, profile_id, run_number, technology, given_size, optimized_size):
    """Save plant size data to Plant_size table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO Plant_size (
            project_id, profile_id, run_number, technology, 
            given_plant_size, optimized_plant_size
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            given_plant_size = VALUES(given_plant_size),
            optimized_plant_size = VALUES(optimized_plant_size)
    """
    
    values = (project_id, profile_id, run_number, technology, given_size, optimized_size)
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

def run_capacity_optimization(project_id, profile_id, run_number, selected_technology):
    try:
        demand_df, solar_df, wind_df = get_profile_data(project_id, profile_id)
        
        if demand_df.empty:
            st.error("No demand data found for the selected profile.")
            return False
            
        # Check what profile data is available
        has_solar_data = not solar_df.empty
        has_wind_data = not wind_df.empty
        
        if not has_solar_data and not has_wind_data:
            st.error("No solar or wind generation profile data found.")
            return False
        
        # Prepare demand data for optimization
        demand_df_opt = demand_df.rename(columns={'demand': 'Demand'})
        demand_df_opt['Hour'] = range(len(demand_df_opt))
        
        # Get CUF values from GENERAL INPUTS (not tech inputs)
        solar_cuf_general = st.session_state.general_inputs.get("Solar", {}).get("cuf", 0) / 100 
        wind_cuf_general = st.session_state.general_inputs.get("Wind", {}).get("cuf", 0) / 100
        
        # Get given plant sizes
        solar_given_size = st.session_state.general_inputs.get("Solar", {}).get("plant_size_kw", 0)
        wind_given_size = st.session_state.general_inputs.get("Wind", {}).get("plant_size_kw", 0)
        
        # Initialize capacities
        solar_capacity = 0
        wind_capacity = 0
        
        # Apply technology selection logic
        if selected_technology == "Solar":
            # Only Solar optimization
            if not has_solar_data:
                st.error("Solar profile data not found but Solar technology selected.")
                return False
            solar_cuf = solar_cuf_general
            wind_cuf = 0  # Wind CUF set to 0 for Solar-only optimization
            st.write(f"Debug - Solar Only Mode: Solar CUF: {solar_cuf}")
            
        elif selected_technology == "Wind":
            # Only Wind optimization
            if not has_wind_data:
                st.error("Wind profile data not found but Wind technology selected.")
                return False
            solar_cuf = 0  # Solar CUF set to 0 for Wind-only optimization
            wind_cuf = wind_cuf_general
            st.write(f"Debug - Wind Only Mode: Wind CUF: {wind_cuf}")
            
        else:  # Hybrid mode
            # Both technologies optimization
            if not has_solar_data and not has_wind_data:
                st.error("Both solar and wind profile data required for Hybrid mode.")
                return False
            
            # Use available data and set CUF accordingly
            solar_cuf = solar_cuf_general if has_solar_data else 0
            wind_cuf = wind_cuf_general if has_wind_data else 0
            st.write(f"Debug - Hybrid Mode: Solar CUF: {solar_cuf}, Wind CUF: {wind_cuf}")
        
        # Run optimization
        solar_capacity, wind_capacity, _ = optimize_generation_capacity(demand_df_opt, solar_cuf, wind_cuf)

        return True
        
    except Exception as e:
        st.error(f"Error in capacity optimization: {str(e)}")
        return False

def get_optimized_plant_sizes(project_id, profile_id, selected_technology):
    try:
        demand_df, solar_df, wind_df = get_profile_data(project_id, profile_id)
        
        if demand_df.empty:
            return None, "No demand data found for the selected profile."
            
        has_solar_data = not solar_df.empty
        has_wind_data = not wind_df.empty
        
        if not has_solar_data and not has_wind_data:
            return None, "No solar or wind generation profile data found."
        
        # Convert demand from MW to kW
        demand_df_opt = demand_df.rename(columns={'demand': 'Demand'})
        demand_df_opt['Demand'] = demand_df_opt['Demand'] * 1000  # Convert MW to kW
        demand_df_opt['Hour'] = range(len(demand_df_opt))
        
        # Get CUF values from session state
        solar_cuf_general = st.session_state.general_inputs.get("Solar", {}).get("cuf", 0) / 100 
        wind_cuf_general = st.session_state.general_inputs.get("Wind", {}).get("cuf", 0) / 100
        
        # Get inverter/turbine capacities from session state
        solar_inverter_capacity = st.session_state.general_inputs.get("Solar", {}).get("inverter_turbine_capacity", 1)
        wind_turbine_capacity = st.session_state.general_inputs.get("Wind", {}).get("inverter_turbine_capacity", 1)
        
        # Set CUF based on selected technology
        if selected_technology == "Solar":
            solar_cuf = solar_cuf_general
            wind_cuf = 0
        elif selected_technology == "Wind":
            solar_cuf = 0
            wind_cuf = wind_cuf_general
        else:  # Hybrid
            solar_cuf = solar_cuf_general if has_solar_data else 0
            wind_cuf = wind_cuf_general if has_wind_data else 0
        
        # Run optimization
        solar_capacity, wind_capacity, _ = optimize_generation_capacity(demand_df_opt, solar_cuf, wind_cuf)
        
        # Calculate number of inverters and turbines
        solar_inverters = 0
        wind_turbines = 0
        
        if solar_capacity > 0 and solar_inverter_capacity > 0:
            solar_inverters = math.ceil(solar_capacity / solar_inverter_capacity)
        
        if wind_capacity > 0 and wind_turbine_capacity > 0:
            wind_turbines = math.ceil(wind_capacity / wind_turbine_capacity)
        
        return {
            'solar_capacity': solar_capacity,
            'wind_capacity': wind_capacity,
            'solar_inverters': solar_inverters,
            'wind_turbines': wind_turbines,
            'solar_inverter_capacity': solar_inverter_capacity,
            'wind_turbine_capacity': wind_turbine_capacity,
            'technology': selected_technology
        }, None
        
    except Exception as e:
        return None, f"Error in optimization: {str(e)}"

def calculate_cuf_from_profiles(project_id, profile_id):
    """Calculate CUF based on uploaded generation profiles"""
    try:
        demand_df, solar_df, wind_df = get_profile_data(project_id, profile_id)
        
        results = {
            'solar_cuf': 0.0,
            'wind_cuf': 0.0,
            'solar_available': False,
            'wind_available': False,
            'total_hours': 0
        }
        
        # Calculate Solar CUF
        if not solar_df.empty:
            results['solar_available'] = True
            total_hours = len(solar_df)
            results['total_hours'] = total_hours
            
            # Assuming generation is normalized (0-1) or percentage, convert to actual generation
            # Total energy = sum of generation values (assuming 1 kW installed capacity)
            total_energy = solar_df['generation'].sum()
            
            # CUF = Total Energy Generated / (Installed Capacity * Total Hours)
            # For normalized data with 1 kW capacity: CUF = total_energy / total_hours
            results['solar_cuf'] = (total_energy / total_hours) * 100 if total_hours > 0 else 0.0
        
        # Calculate Wind CUF
        if not wind_df.empty:
            results['wind_available'] = True
            total_hours = len(wind_df)
            results['total_hours'] = total_hours
            
            # Same calculation for wind
            total_energy = wind_df['generation'].sum()
            results['wind_cuf'] = (total_energy / total_hours) * 100 if total_hours > 0 else 0.0
        
        return results, None
        
    except Exception as e:
        return None, f"Error calculating CUF: {str(e)}"

def save_optimized_plant_sizes(project_id, profile_id, run_number, optimization_results):
    """
    Save optimized plant sizes to Plant_size table
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get current given plant sizes from session state
        solar_given_size = st.session_state.general_inputs.get("Solar", {}).get("plant_size_kw", 0)
        wind_given_size = st.session_state.general_inputs.get("Wind", {}).get("plant_size_kw", 0)
        
        # Save solar capacity
        query = """
            INSERT INTO Plant_size (
                project_id, profile_id, run_number, technology, 
                given_plant_size, optimized_plant_size
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                given_plant_size = VALUES(given_plant_size),
                optimized_plant_size = VALUES(optimized_plant_size)
        """
        
        # Save Solar
        cursor.execute(query, (
            project_id, profile_id, run_number, "Solar", 
            solar_given_size, optimization_results['solar_capacity']
        ))
        
        # Save Wind
        cursor.execute(query, (
            project_id, profile_id, run_number, "Wind", 
            wind_given_size, optimization_results['wind_capacity']
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        st.error(f"Error saving optimized plant sizes: {str(e)}")
        return False

def convert_inputs_to_dataframe():
    parameter_list = default_inputs["Parameter"]
    
    solar_values = []
    wind_values = []
    
    db_column_to_param = {
        "system_capex": "System Capital Cost (Per KW)",
        "capex_subsidy": "Capital Subsidy (Per KW)",
        "plant_size_kw": "Plant Size (KW)",
        "plant_life_years": "Project Life of Plant (Years)",
        "cuf": "Capacity Utilization Factor (%)",
        "aux_consumption": "Auxiliary Consumption (%)",
        "discount_rate": "Discount Rate (%)",
        "equity": "Equity (%)",
        "return_on_equity": "Return on Equity (%)",
        "loan_tenure": "Loan Tenure (years)",
        "moratorium": "Moratorium (years)",
        "loan_interest": "Interest on Loan (%)",
        "opex_year1": "Operation and Maintenance Expenses in year 1 (%)",
        "opex_growth": "Annual increase in Operation and Maintenance expenses (%)",
        "insurance": "Insurance(%) of depreciated asset value)",
        "wc_om_months": "Working Capital - O & M (months)",
        "wc_receivables_months": "Working Capital - Receivables (months)",
        "wc_interest": "Interest on Working Capital (%)",
        "n1_years": "n1 years",
        "depreciation_n1": "Depreciation rate for the first n1 years (%)",
        "depreciation_applicable_capex_pct": "Percentage of capital cost on which depreciation applies (%)",
        "solar_degradation": "Annual Solar Panel Degradation (%)",
        "grid_availability": "Grid Availability Factor (%)",
        "inverter_turbine_capacity": "Inverter/Turbine Capacity(in kw)"
    }
    
    for i, param in enumerate(parameter_list):
        db_col = None
        for col, p in db_column_to_param.items():
            if p == param:
                db_col = col
                break
        
        if db_col:
            # Get values from session state or use defaults
            solar_val = st.session_state.general_inputs.get("Solar", {}).get(db_col, default_inputs["Solar"][i])
            wind_val = st.session_state.general_inputs.get("Wind", {}).get(db_col, default_inputs["Wind"][i])
            
            solar_values.append(solar_val)
            wind_values.append(wind_val)
        else:
            # Use default values if no database column mapping exists
            solar_values.append(default_inputs["Solar"][i])
            wind_values.append(default_inputs["Wind"][i])
    
    # Return only Solar and Wind data
    df = {
        "Parameter": parameter_list,
        "Solar": solar_values,
        "Wind": wind_values
    }
    
    return df

st.set_page_config(page_title="Optimizer Summary", layout="wide")
st.title("Optimizer Summary")

def get_project_name(project_id):
    """Retrieve project name from project_config table based on project_id"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT project_name FROM project_config WHERE project_id = %s", (project_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else ""

# --- Project Info ---
st.subheader("Project Details")
col1, col2, col3, col4, col5 = st.columns([1.2, 2, 0.8, 0.8, 0.8])
with col1:
    project_ids = get_project_ids()
    project_id = st.selectbox("Project Id *", project_ids, on_change=None)
    
    if 'project_name' not in st.session_state:
        st.session_state.project_name = ""
    
    if project_id:
        project_name_from_db = get_project_name(project_id)
        st.session_state.project_name = project_name_from_db

with col2:
    project_name = st.text_input("Project Name", value=st.session_state.project_name, disabled=True)

with col3:
    # Get profile_id from session state (from previous page)
    profile_id = st.session_state.get('profile_id', None)
    if profile_id is None:
        profile_id = st.session_state.get('selected_profile_id', None)
    
    profile_display = str(profile_id) if profile_id is not None else "Not Selected"
    st.text_input("Profile ID", value=profile_display, disabled=True, key="profile_id_display")
    
with col4:
    if 'current_run_number' not in st.session_state:
        st.session_state.current_run_number = get_next_run_number(project_id) if project_id else 0
    
    # Update run number if project changes
    if 'last_project_id' not in st.session_state:
        st.session_state.last_project_id = project_id
    elif st.session_state.last_project_id != project_id:
        st.session_state.current_run_number = get_next_run_number(project_id) if project_id else 0
        st.session_state.last_project_id = project_id
    
    st.text_input("Run#", value=str(st.session_state.current_run_number), disabled=True, key="run_number_display")
    run_number = st.session_state.current_run_number
    
with col5:
    run_date_input = st.date_input("Date", datetime.today(), key="run_date_input")
    run_date = datetime.combine(run_date_input, datetime.min.time())

if 'general_inputs' not in st.session_state:
    st.session_state.general_inputs = {
        'Solar': {},
        'Wind': {}
    }
if 'tech_inputs' not in st.session_state:
    st.session_state.tech_inputs = {}
if 'economics_inputs' not in st.session_state:
    st.session_state.economics_inputs = {}
if 'financials_inputs' not in st.session_state:
    st.session_state.financials_inputs = {}
if 'inputs_saved' not in st.session_state:
    st.session_state.inputs_saved = False

if 'selected_technology' not in st.session_state:
    st.session_state.selected_technology = "Hybrid"

selected_technology = st.selectbox(
    "Select Technology", 
    ["Hybrid", "Solar", "Wind"], 
    key="selected_technology"
)

# Create tabs based on technology selection
if selected_technology == "Solar":
    tabs = st.tabs(["Solar General Inputs", "RE Technical", "Economics", "Financials"])
elif selected_technology == "Wind":
    tabs = st.tabs(["Wind General Inputs", "RE Technical", "Economics", "Financials"])
else:  # Hybrid
    tabs = st.tabs(["Solar General Inputs", "Wind General Inputs", "RE Technical", "Economics", "Financials"])

# --- General Inputs ---
param_to_db_column = {
    "System Capital Cost (Per KW)": "system_capex",
    "Capital Subsidy (Per KW)": "capex_subsidy",
    "Plant Size (KW)": "plant_size_kw",
    "Project Life of Plant (Years)": "plant_life_years",
    "Capacity Utilization Factor (%)": "cuf",
    "Auxiliary Consumption (%)": "aux_consumption",
    "Discount Rate (%)": "discount_rate",
    "Equity (%)": "equity",
    "Return on Equity (%)": "return_on_equity",
    "Loan Tenure (years)": "loan_tenure",
    "Moratorium (years)": "moratorium",
    "Interest on Loan (%)": "loan_interest",
    "Operation and Maintenance Expenses in year 1 (%)": "opex_year1",
    "Annual increase in Operation and Maintenance expenses (%)": "opex_growth",
    "Insurance(%) of depreciated asset value)": "insurance",
    "Working Capital - O & M (months)": "wc_om_months",
    "Working Capital - Receivables (months)": "wc_receivables_months",
    "Interest on Working Capital (%)": "wc_interest",
    "n1 years": "n1_years",
    "Depreciation rate for the first n1 years (%)": "depreciation_n1",
    "Percentage of capital cost on which depreciation applies (%)": "depreciation_applicable_capex_pct",
    "Annual Solar Panel Degradation (%)": "solar_degradation",
    "Grid Availability Factor (%)": "grid_availability",
    "Inverter/Turbine Capacity(in kw)": "inverter_turbine_capacity"
}

common_params = [
    "System Capital Cost (Per KW)", 
    "Capital Subsidy (Per KW)", 
    "Plant Size (KW)",
    "Project Life of Plant (Years)", 
    "Capacity Utilization Factor (%)", 
    "Auxiliary Consumption (%)",
    "Discount Rate (%)", 
    "Equity (%)", 
    "Return on Equity (%)", 
    "Loan Tenure (years)",
    "Moratorium (years)", 
    "Interest on Loan (%)", 
    "Operation and Maintenance Expenses in year 1 (%)",
    "Annual increase in Operation and Maintenance expenses (%)", 
    "Insurance(%) of depreciated asset value)",
    "Working Capital - O & M (months)", 
    "Working Capital - Receivables (months)",
    "Interest on Working Capital (%)", 
    "n1 years", 
    "Depreciation rate for the first n1 years (%)",
    "Percentage of capital cost on which depreciation applies (%)",
    "Grid Availability Factor (%)",
    "Inverter/Turbine Capacity(in kw)"
]

solar_params = common_params + ["Annual Solar Panel Degradation (%)"]
wind_params = common_params.copy()  # Wind uses common params only

if selected_technology == "Solar":
# Solar General Inputs Tab
    with tabs[0]:
        st.markdown("### Solar General Inputs")
        
        # Create 4 columns
        cols = st.columns(4)
        
        for i, param in enumerate(solar_params):
            param_index = default_inputs["Parameter"].index(param) if param in default_inputs["Parameter"] else -1
            default_val = str(default_inputs["Solar"][param_index]) if param_index >= 0 else "0"
            
            # Use modulo to cycle through columns
            col_index = i % 4
            
            with cols[col_index]:
                key = f"Solar_{param}"
                val = st.text_input(f"{param}", value=default_val, key=key)
                
                if param in param_to_db_column:
                    db_column = param_to_db_column[param]
                    try:
                        st.session_state.general_inputs["Solar"][db_column] = float(val)
                        # Set Wind values to 0
                        st.session_state.general_inputs["Wind"][db_column] = 0.0
                    except ValueError:
                        st.warning(f"Invalid input for Solar - {param}")

elif selected_technology == "Wind":
    with tabs[0]:
        st.markdown("### Wind General Inputs")
        
        cols = st.columns(4)
        
        for i, param in enumerate(wind_params):
            param_index = default_inputs["Parameter"].index(param) if param in default_inputs["Parameter"] else -1
            default_val = str(default_inputs["Wind"][param_index]) if param_index >= 0 else "0"
            
            # Use modulo to cycle through columns
            col_index = i % 4
            
            with cols[col_index]:
                key = f"Wind_{param}"
                val = st.text_input(f"{param}", value=default_val, key=key)
                
                if param in param_to_db_column:
                    db_column = param_to_db_column[param]
                    try:
                        st.session_state.general_inputs["Wind"][db_column] = float(val)
                        # Set Solar values to 0
                        st.session_state.general_inputs["Solar"][db_column] = 0.0 if db_column != "solar_degradation" else 0.0
                    except ValueError:
                        st.warning(f"Invalid input for Wind - {param}")

else:  # Hybrid
# Solar General Inputs Tab
    with tabs[0]:
        st.markdown("### Solar General Inputs")
        
        # Create 4 columns
        cols = st.columns(4)
        
        for i, param in enumerate(solar_params):
            param_index = default_inputs["Parameter"].index(param) if param in default_inputs["Parameter"] else -1
            default_val = str(default_inputs["Solar"][param_index]) if param_index >= 0 else "0"
            
            # Use modulo to cycle through columns
            col_index = i % 4
            
            with cols[col_index]:
                key = f"Solar_{param}"
                val = st.text_input(f"{param}", value=default_val, key=key)
                
                if param in param_to_db_column:
                    db_column = param_to_db_column[param]
                    try:
                        st.session_state.general_inputs["Solar"][db_column] = float(val)
                    except ValueError:
                        st.warning(f"Invalid input for Solar - {param}")
    
# Wind General Inputs Tab
    with tabs[1]:
        st.markdown("### Wind General Inputs")
        
        # Create 4 columns
        cols = st.columns(4)
        
        for i, param in enumerate(common_params):
            param_index = default_inputs["Parameter"].index(param) if param in default_inputs["Parameter"] else -1
            default_val = str(default_inputs["Wind"][param_index]) if param_index >= 0 else "0"
            
            # Use modulo to cycle through columns
            col_index = i % 4
            
            with cols[col_index]:
                key = f"Wind_{param}"
                val = st.text_input(f"{param}", value=default_val, key=key)
                
                if param in param_to_db_column:
                    db_column = param_to_db_column[param]
                    try:
                        st.session_state.general_inputs["Wind"][db_column] = float(val)
                    except ValueError:
                        st.warning(f"Invalid input for Wind - {param}")

# --- RE Technical ---
tech_tab_index = 2 if selected_technology == "Hybrid" else 1

with tabs[tech_tab_index]:
    st.markdown("### RE Technical Inputs")
    
    tech_cols = st.columns(2)  # Changed from 3 to 2 columns (removed BESS)
    
    with tech_cols[0]:
        st.markdown("**RE Technical - Wind**")
        disabled_wind = selected_technology == "Solar"
        
        wind_cuf = st.text_input("Capacity Utilization Factor(%)", value="0" if disabled_wind else "29.7", key="wind_cuf", disabled=disabled_wind)
        wind_grid = st.text_input("Grid Availability Factor(%)", value="0" if disabled_wind else "95", key="wind_grid", disabled=disabled_wind) 
        wind_deg = st.text_input("Annual Degradation(%)", value="0" if disabled_wind else "0.3", key="wind_deg", disabled=disabled_wind)
        
        if not disabled_wind:
            st.session_state.tech_inputs["wind_cuf"] = float(wind_cuf)
            st.session_state.tech_inputs["wind_grid"] = float(wind_grid)
            st.session_state.tech_inputs["wind_deg"] = float(wind_deg)
        else:
            st.session_state.tech_inputs["wind_cuf"] = 0.0
            st.session_state.tech_inputs["wind_grid"] = 0.0
            st.session_state.tech_inputs["wind_deg"] = 0.0

    with tech_cols[1]:
        st.markdown("**RE Technical - Solar**")
        disabled_solar = selected_technology == "Wind"
        
        solar_cuf = st.text_input("Capacity Utilization Factor(%)", value="0" if disabled_solar else "22.3", key="solar_cuf", disabled=disabled_solar)
        solar_grid = st.text_input("Grid Availability Factor(%)", value="0" if disabled_solar else "98", key="solar_grid", disabled=disabled_solar)
        solar_deg = st.text_input("Annual Degradation(%)", value="0" if disabled_solar else "0.5", key="solar_deg", disabled=disabled_solar)
        
        if not disabled_solar:
            st.session_state.tech_inputs["solar_cuf"] = float(solar_cuf)
            st.session_state.tech_inputs["solar_grid"] = float(solar_grid)
            st.session_state.tech_inputs["solar_deg"] = float(solar_deg)
        else:
            st.session_state.tech_inputs["solar_cuf"] = 0.0
            st.session_state.tech_inputs["solar_grid"] = 0.0
            st.session_state.tech_inputs["solar_deg"] = 0.0

# --- Economics Tab ---
econ_tab_index = 3 if selected_technology == "Hybrid" else 2

with tabs[econ_tab_index]:
    st.markdown("### Economics Inputs")
    
    selected_tech = st.session_state.selected_technology
    
    econ_cols = st.columns(3)  # Keep 3 columns but remove BESS content

    with econ_cols[0]:
        disabled_wind = selected_tech == "Solar"
        wind_capex = st.text_input("Capital Cost - Wind (INR in Cr/MW)", value="0" if disabled_wind else "7.5", key="wind_capex", disabled=disabled_wind)
        wind_om = st.text_input("O&M - Wind (% of capital costs)", value="0" if disabled_wind else "1.5", key="wind_om", disabled=disabled_wind)
        
        if not disabled_wind:
            st.session_state.economics_inputs["wind_capex"] = float(wind_capex)
            st.session_state.economics_inputs["wind_om"] = float(wind_om)
        else:
            st.session_state.economics_inputs["wind_capex"] = 0.0
            st.session_state.economics_inputs["wind_om"] = 0.0

    with econ_cols[1]:
        disabled_solar = selected_tech == "Wind"
        solar_capex = st.text_input("Capital Cost - Solar (INR in Cr/MW)", value="0" if disabled_solar else "3.8", key="solar_capex", disabled=disabled_solar)
        solar_om = st.text_input("O&M - Solar (% of capital costs)", value="0" if disabled_solar else "0.75", key="solar_om", disabled=disabled_solar)
        
        if not disabled_solar:
            st.session_state.economics_inputs["solar_capex"] = float(solar_capex)
            st.session_state.economics_inputs["solar_om"] = float(solar_om)
        else:
            st.session_state.economics_inputs["solar_capex"] = 0.0
            st.session_state.economics_inputs["solar_om"] = 0.0

    with econ_cols[2]:
        insurance = st.text_input("Insurance (%)", value="0.5", key="insurance_econ")
        st.session_state.economics_inputs["insurance"] = float(insurance)

# --- Financials Tab ---
fin_tab_index = 4 if selected_technology == "Hybrid" else 3

with tabs[fin_tab_index]:
    st.markdown("### Financials Inputs")
    
    fin_cols = st.columns(3)
    
    with fin_cols[0]:
        equity_pct = st.text_input("Equity (%)", value="30", key="equity_pct")
        depreciation_year = st.text_input("Depreciation (Year)", value="13.91", key="depreciation_year")
        ppa_price = st.text_input("PPA Price (INR/MW)", value="2.8", key="ppa_price")
        
        st.session_state.financials_inputs["equity_pct"] = float(equity_pct)
        st.session_state.financials_inputs["depreciation_year"] = float(depreciation_year)
        st.session_state.financials_inputs["ppa_price"] = float(ppa_price)
        
    with fin_cols[1]:
        loan_tenure = st.text_input("Loan Tenure (Year)", value="10", key="loan_tenure_fin")
        project_life = st.text_input("Project Life (Year)", value="25", key="project_life_fin")
        penalty = st.text_input("Penalty (INR/MW)", value="0.5", key="penalty")
        
        st.session_state.financials_inputs["loan_tenure"] = float(loan_tenure)
        st.session_state.financials_inputs["project_life"] = float(project_life)
        st.session_state.financials_inputs["penalty"] = float(penalty)
        
    with fin_cols[2]:
        loan_interest = st.text_input("Interest on Loan (%)", value="10", key="loan_interest_fin")
        inflation_rate = st.text_input("Inflation Rate (%)", value="5", key="inflation_rate")
        excess_gen_price = st.text_input("Excess Generation Price (INR/MW)", value="2.4", key="excess_gen_price")
        
        st.session_state.financials_inputs["loan_interest"] = float(loan_interest)
        st.session_state.financials_inputs["inflation_rate"] = float(inflation_rate)
        st.session_state.financials_inputs["excess_gen_price"] = float(excess_gen_price)

# --- Run Optimizer Button ---
st.markdown("---")

# CUF Calculation Section
if 'calculated_cuf' in st.session_state:
    st.markdown("### Calculated CUF from Profiles")
    
    cuf_col1, cuf_col2, cuf_col3 = st.columns(3)
    
    with cuf_col1:
        if st.session_state.calculated_cuf.get('solar_available', False):
            st.metric(
                label="Solar CUF", 
                value=f"{st.session_state.calculated_cuf['solar_cuf']:.2f}%",
                help=f"Based on {st.session_state.calculated_cuf['total_hours']} hours of data"
            )
        else:
            st.metric(label="Solar CUF", value="No Data")
    
    with cuf_col2:
        if st.session_state.calculated_cuf.get('wind_available', False):
            st.metric(
                label="Wind CUF", 
                value=f"{st.session_state.calculated_cuf['wind_cuf']:.2f}%",
                help=f"Based on {st.session_state.calculated_cuf['total_hours']} hours of data"
            )
        else:
            st.metric(label="Wind CUF", value="No Data")
    
    with cuf_col3:
        st.metric(
            label="Data Period", 
            value=f"{st.session_state.calculated_cuf['total_hours']} hours"
        )
    
    st.markdown("---")

# Function to save all inputs
def save_all_inputs():
    if not project_id:
        st.error(" Please select a valid Project ID.")
        return False
    
    try:
        # Use the current run number instead of getting next run number
        current_run_number = run_number
        technologies = ["Solar", "Wind"]
        
        # Get profile_id from session state - try multiple possible keys
        profile_id = st.session_state.get('profile_id', None)
        if profile_id is None:
            profile_id = st.session_state.get('selected_profile_id', None)
        
        # Debug: Print profile_id to console (remove this line in production)
        print(f"Debug: Using profile_id: {profile_id}")
        
        # Save general inputs for each technology
        for tech in technologies:
            tech_data = st.session_state.general_inputs[tech].copy()
            tech_data["technology"] = tech
            
            if tech != "Solar" and "solar_degradation" not in tech_data:
                tech_data["solar_degradation"] = 0
                
            save_general_inputs(project_id, current_run_number, tech_data, profile_id)
        
        # Save technical inputs
        save_tech_inputs(project_id, current_run_number, st.session_state.tech_inputs, profile_id)
        
        # Save economics inputs
        save_economics_inputs(project_id, current_run_number, st.session_state.economics_inputs, profile_id)
        
        # Save financials inputs
        save_financials_inputs(project_id, current_run_number, st.session_state.financials_inputs, profile_id)
        
        # Save run configuration
        save_run(project_id, current_run_number, datetime.now())
        
        # Update the session state run number after successful save
        st.session_state.current_run_number = current_run_number
        
        st.session_state.inputs_saved = True
        return True
        
    except Exception as e:
        st.error(f"Error saving inputs: {str(e)}")
        return False

# Button layout
col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1, 1, 1])

with col2:
    st.markdown("""
    <style>
        div[data-testid="stButton"] button[kind="secondary"] {
            background-color: #6f42c1 !important;
            color: white !important;
            border: 1px solid #6f42c1 !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1rem !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
        }
        
        div[data-testid="stButton"] button[kind="secondary"]:hover {
            background-color: #5a2d91 !important;
            border-color: #5a2d91 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 8px rgba(111, 66, 193, 0.3) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    calculate_cuf_clicked = st.button(
        "Calculate CUF", 
        key="calculate_cuf",
        type="secondary",
        use_container_width=True
    )

with col3:
    st.markdown("""
    <style>
        div[data-testid="stButton"] button[kind="secondary"] {
            background-color: #17a2b8 !important;
            color: white !important;
            border: 1px solid #17a2b8 !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1rem !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
        }
        
        div[data-testid="stButton"] button[kind="secondary"]:hover {
            background-color: #138496 !important;
            border-color: #138496 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 8px rgba(23, 162, 184, 0.3) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    optimize_clicked = st.button(
        "Get Optimized Plant Size", 
        key="get_optimized_size",
        type="secondary",
        use_container_width=True
    )

with col4:
    st.markdown("""
    <style>
        div[data-testid="stButton"] button[kind="secondary"] {
            background-color: #28a745 !important;
            color: white !important;
            border: 1px solid #28a745 !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1rem !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
        }
        
        div[data-testid="stButton"] button[kind="secondary"]:hover {
            background-color: #218838 !important;
            border-color: #218838 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    save_clicked = st.button(
        "Save Inputs", 
        key="save_inputs",
        type="secondary",
        use_container_width=True
    )

with col5:
    st.markdown("""
    <style>
        div[data-testid="stButton"] button[kind="primary"] {
            background-color: #0066cc !important;
            color: white !important;
            border: 1px solid #0066cc !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1rem !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
        }
        
        div[data-testid="stButton"] button[kind="primary"]:hover {
            background-color: #004c99 !important;
            border-color: #004c99 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 8px rgba(0, 102, 204, 0.3) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    run_optimizer_clicked = st.button(
        "Run Optimizer", 
        key="run_optimizer",
        type="primary",
        use_container_width=True
    )
if calculate_cuf_clicked:
    profile_id = st.session_state.get('profile_id', None)
    if profile_id is None:
        profile_id = st.session_state.get('selected_profile_id', None)
    
    if profile_id is None:
        st.error("No profile ID found. Please select a profile first.")
    elif not project_id:
        st.error("Please select a valid Project ID.")
    else:
        with st.spinner("Calculating CUF from generation profiles..."):
            cuf_results, error_msg = calculate_cuf_from_profiles(project_id, profile_id)
            
            if error_msg:
                st.error(error_msg)
            else:
                st.session_state['calculated_cuf'] = cuf_results
                st.success("CUF calculation completed!")
                st.rerun()
                
if optimize_clicked:
    profile_id = st.session_state.get('profile_id', None)
    if profile_id is None:
        profile_id = st.session_state.get('selected_profile_id', None)
    
    if profile_id is None:
        st.error("No profile ID found. Please select a profile first.")
    elif not project_id:
        st.error("Please select a valid Project ID.")
    else:
        with st.spinner("Calculating optimized plant sizes..."):
            optimization_results, error_msg = get_optimized_plant_sizes(
                project_id, profile_id, selected_technology
            )
            
            if error_msg:
                st.error(error_msg)
            else:
                # Display results in a more comprehensive way
                st.success("Optimization completed!")
                
                # Create columns for better layout
                col_res1, col_res2, col_res3, col_res4, col_res5, col_res6 = st.columns([2, 2, 1.6, 1.6, 2, 2])
                with col_res1:
                    st.metric(
                        label="Optimized Solar Capacity", 
                        value=f"{optimization_results['solar_capacity']:.1f} kW"
                    )
                
                with col_res2:
                    st.metric(
                        label="Optimized Wind Capacity", 
                        value=f"{optimization_results['wind_capacity']:.1f} kW"
                    )
                
                with col_res3:
                    if optimization_results['solar_capacity'] > 0:
                        st.metric(
                            label="Solar Inverters Needed", 
                            value=f"{optimization_results['solar_inverters']} units",
                            help=f"Based on {optimization_results['solar_inverter_capacity']} kW per inverter"
                        )
                    else:
                        st.metric(
                            label="Solar Inverters Needed", 
                            value="0 units"
                        )
                
                with col_res4:
                    if optimization_results['wind_capacity'] > 0:
                        st.metric(
                            label="Wind Turbines Needed", 
                            value=f"{optimization_results['wind_turbines']} units",
                            help=f"Based on {optimization_results['wind_turbine_capacity']} kW per turbine"
                        )
                    else:
                        st.metric(
                            label="Wind Turbines Needed", 
                            value="0 units"
                        )
                
                # Calculate optimized generation per hour
                solar_cuf = st.session_state.general_inputs.get("Solar", {}).get("cuf", 0) / 100
                wind_cuf = st.session_state.general_inputs.get("Wind", {}).get("cuf", 0) / 100
                
                optimized_solar_generation = optimization_results['solar_capacity'] * solar_cuf
                optimized_wind_generation = optimization_results['wind_capacity'] * wind_cuf
                
                with col_res5:
                    st.metric(
                        label="Optimized Solar Generation", 
                        value=f"{optimized_solar_generation:.1f} kWh/hr",
                        help=f"Based on {optimization_results['solar_capacity']:.1f} kW × {solar_cuf*100:.1f}% CUF"
                    )
                
                with col_res6:
                    st.metric(
                        label="Optimized Wind Generation", 
                        value=f"{optimized_wind_generation:.1f} kWh/hr",
                        help=f"Based on {optimization_results['wind_capacity']:.1f} kW × {wind_cuf*100:.1f}% CUF"
                    )
                
                # Additional details in an expander
                with st.expander("Detailed Breakdown"):
                    detail_col1, detail_col2 = st.columns(2)
                    
                    with detail_col1:
                        if optimization_results['solar_capacity'] > 0:
                            st.write("**Solar Configuration:**")
                            st.write(f"- Total Capacity: {optimization_results['solar_capacity']:.2f} kW")
                            st.write(f"- Inverter Capacity: {optimization_results['solar_inverter_capacity']} kW each")
                            st.write(f"- Number of Inverters: {optimization_results['solar_inverters']} units")
                            st.write(f"- Total Inverter Capacity: {optimization_results['solar_inverters'] * optimization_results['solar_inverter_capacity']} kW")
                            
                            if optimization_results['solar_inverters'] * optimization_results['solar_inverter_capacity'] > optimization_results['solar_capacity']:
                                excess_solar = (optimization_results['solar_inverters'] * optimization_results['solar_inverter_capacity']) - optimization_results['solar_capacity']
                                st.write(f"- Excess Capacity: {excess_solar:.2f} kW")
                    
                    with detail_col2:
                        if optimization_results['wind_capacity'] > 0:
                            st.write("**Wind Configuration:**")
                            st.write(f"- Total Capacity: {optimization_results['wind_capacity']:.2f} kW")
                            st.write(f"- Turbine Capacity: {optimization_results['wind_turbine_capacity']} kW each")
                            st.write(f"- Number of Turbines: {optimization_results['wind_turbines']} units")
                            st.write(f"- Total Turbine Capacity: {optimization_results['wind_turbines'] * optimization_results['wind_turbine_capacity']} kW")
                            
                            if optimization_results['wind_turbines'] * optimization_results['wind_turbine_capacity'] > optimization_results['wind_capacity']:
                                excess_wind = (optimization_results['wind_turbines'] * optimization_results['wind_turbine_capacity']) - optimization_results['wind_capacity']
                                st.write(f"- Excess Capacity: {excess_wind:.2f} kW")
                
                # Save to database with current run number
                save_success = save_optimized_plant_sizes(
                    project_id, profile_id, run_number, optimization_results
                )
                
                if save_success:
                    st.info("Optimization results saved to database.")
                
                # Store in session state for potential use
                st.session_state['last_optimization'] = optimization_results

# Handle Save button click
if save_clicked:
    if save_all_inputs():
        st.success("All inputs saved successfully!")

if run_optimizer_clicked:
    if not st.session_state.inputs_saved:
        st.warning("Please save your inputs first before running the optimizer!")
        st.info("Click the 'Save Inputs' button to save your data.")
    else:
        profile_id = st.session_state.get('profile_id', None)
        if profile_id is None:
            profile_id = st.session_state.get('selected_profile_id', None)
        
        if profile_id is None:
            st.error("No profile ID found. Please select a profile first.")
        else:
            # Use the current run number from session state
            current_run_number = st.session_state.current_run_number
            
            st.session_state['project_id'] = project_id
            st.session_state['run_number'] = current_run_number
            st.session_state['inputs_df'] = convert_inputs_to_dataframe()
            st.session_state['optimizer_run_triggered'] = True
            
            st.session_state['current_project_inputs'] = {
                'project_id': project_id,
                'run_number': current_run_number,
                'general_inputs': st.session_state.general_inputs,
                'tech_inputs': st.session_state.tech_inputs,
                'economics_inputs': st.session_state.economics_inputs,
                'financials_inputs': st.session_state.financials_inputs
            }
            
            st.success(f"Starting optimizer with run number {current_run_number}...")
            
            optimization_success = run_capacity_optimization(
                project_id, profile_id, current_run_number, selected_technology
            )
            
            if optimization_success:
                # Increment run number for next use after successful run
                st.session_state.current_run_number += 1
                try:
                    st.switch_page("pages/5_LCOE_Outputs.py")
                except Exception as e:
                    st.error(f"Navigation failed. Error: {e}")