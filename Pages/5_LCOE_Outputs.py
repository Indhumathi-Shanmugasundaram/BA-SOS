import streamlit as st
import pandas as pd
from datetime import datetime
import mysql.connector
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.gemini_validator import get_lcoe_interpretation_with_gemini

def get_param_value(inputs_df, param_name, tech, default=0):
    try:
        if isinstance(inputs_df.index, pd.Index) and param_name in inputs_df.index:
            return float(inputs_df.loc[param_name, tech])
        elif 'Parameter' in inputs_df.columns:
            param_row = inputs_df[inputs_df['Parameter'] == param_name]
            if not param_row.empty:
                return float(param_row.iloc[0][tech])
        
        param_index_map = {
            "System Capital Cost (Per KW)": 0,
            "Capital Subsidy (Per KW)": 1, 
            "Plant Size (KW)": 2,
            "Project Life of Plant (Years)": 3,
            "Capacity Utilization Factor (%)": 4,
            "Auxiliary Consumption (%)": 5,
            "Discount Rate (%)": 6,
            "Equity (%)": 7,
            "Return on Equity (%)": 8,
            "Loan Tenure (years)": 9,
            "Moratorium (years)": 10,
            "Interest on Loan (%)": 11,
            "Operation and Maintenance Expenses in year 1 (%)": 12,
            "Annual increase in Operation and Maintenance expenses (%)": 13,
            "Insurance(%) of depreciated asset value)": 14,
            "Working Capital - O & M (months)": 15,
            "Working Capital - Receivables (months)": 16,
            "Interest on Working Capital (%)": 17,
            "n1 years": 18,
            "Depreciation rate for the first n1 years (%)": 19,
            "Percentage of capital cost on which depreciation applies (%)": 20,
            "Annual Solar Panel Degradation (%)": 21,
            "Grid Availability Factor (%)": 22
        }
        if param_name in param_index_map:
            idx = param_index_map[param_name]
            return float(inputs_df.iloc[idx][tech])
        return default
    except Exception as e:
        return default

def handle_nan_value(value, default=0):
    try:
        if pd.isna(value) or (isinstance(value, float) and np.isnan(value)):
            return default
        return float(value)
    except:
        return default

def compute_debt_schedule(net_capex, equity_pct, interest_rate, loan_tenure, plant_life, moratorium=1):
    """
    Fixed version of debt schedule computation
    """
    loan_amount = net_capex * (1 - equity_pct)
    data = []
    
    for year in range(1, plant_life + 1):
        if year == 1:
            opening_balance = loan_amount
        else:
            opening_balance = data[year-2]['Debt closing balance']
        
        # Calculate interest BEFORE using it
        interest = opening_balance * interest_rate
        
        if year > moratorium and opening_balance > 0.001:
            principal_repayment = loan_amount / (loan_tenure - moratorium) if (loan_tenure - moratorium) > 0 else 0
        else:
            principal_repayment = 0
            
        closing_balance = max(0, opening_balance - principal_repayment)
        total_debt_service = interest + principal_repayment
        
        data.append({
            'Year': year,
            'Debt opening balance': round(opening_balance, 2),
            'Debt repayment': round(principal_repayment, 2),
            'Debt closing balance': round(closing_balance, 2),
            'Interest': round(interest, 2),
            'Total debt service': round(total_debt_service, 2)
        })
    
    df = pd.DataFrame(data)
    return df

def compute_working_capital(capex, o_and_m_pct, receivable_months, om_months, wc_interest_rate, plant_life, onm_growth_rate=0.0572, insurance_pct=0.0035, depreciation_annual=0, interest_payment=0, roe_cost=0):
    data = []
    for year in range(1, plant_life + 1):
        o_and_m_cost = capex * o_and_m_pct * ((1 + onm_growth_rate) ** (year - 1))
        om_wcap = o_and_m_cost / (12 / om_months) if om_months > 0 else 0
        interest_on_om_wcap = om_wcap * wc_interest_rate
        insurance_cost = capex * insurance_pct
        if receivable_months > 0:
            total_expenses = o_and_m_cost + insurance_cost + depreciation_annual + interest_payment + roe_cost + interest_on_om_wcap
            receivables_wcap = total_expenses / (12 / receivable_months)
        else:
            receivables_wcap = 0
            
        interest_on_receivables_wcap = receivables_wcap * wc_interest_rate
        total_working_capital = om_wcap + receivables_wcap
        total_interest_on_wc = interest_on_om_wcap + interest_on_receivables_wcap
        
        data.append({
            'Year': year,
            'Operation and Maintenance wcap': round(om_wcap, 2),
            'Interest on working capital - O&M': round(interest_on_om_wcap, 2),
            'Receivables wcap': round(receivables_wcap, 2),
            'Interest on receivables wcap': round(interest_on_receivables_wcap, 2),
            'Total Working Capital': round(total_working_capital, 2),
            'Interest on working capital': round(total_interest_on_wc, 2)
        })    
    df = pd.DataFrame(data)    
    return df

def calculate_lcoe(inputs_df, plant_life=25):
    cap_cost = inputs_df.loc[0, ["Solar", "Wind"]].astype(float)
    subsidy = inputs_df.loc[1, ["Solar", "Wind"]].astype(float)
    size = inputs_df.loc[2, ["Solar", "Wind"]].astype(float)
    project_life = inputs_df.loc[3, ["Solar", "Wind"]].astype(float)
    cuf = inputs_df.loc[4, ["Solar", "Wind"]].astype(float) / 100
    auxiliary_consumption = inputs_df.loc[5, ["Solar", "Wind"]].astype(float) / 100
    discount_rate = inputs_df.loc[6, ["Solar", "Wind"]].astype(float) / 100
    equity_pct = inputs_df.loc[7, ["Solar", "Wind"]].astype(float) / 100
    roe = inputs_df.loc[8, ["Solar", "Wind"]].astype(float) / 100
    loan_tenure = inputs_df.loc[9, ["Solar", "Wind"]].astype(float)
    moratorium = inputs_df.loc[10, ["Solar", "Wind"]].astype(float)
    loan_int_pct = inputs_df.loc[11, ["Solar", "Wind"]].astype(float) / 100
    onm_pct = inputs_df.loc[12, ["Solar", "Wind"]].astype(float) / 100
    onm_growth = inputs_df.loc[13, ["Solar", "Wind"]].astype(float) / 100
    insurance_pct = inputs_df.loc[14, ["Solar", "Wind"]].astype(float) / 100
    wc_om_months = inputs_df.loc[15, ["Solar", "Wind"]].astype(float)
    wc_receivables_months = inputs_df.loc[16, ["Solar", "Wind"]].astype(float)
    wc_interest = inputs_df.loc[17, ["Solar", "Wind"]].astype(float) / 100
    n1_years = inputs_df.loc[18, ["Solar", "Wind"]].astype(float)
    depr_rate = inputs_df.loc[19, ["Solar", "Wind"]].astype(float) / 100
    dep_cap_pct = inputs_df.loc[20, ["Solar", "Wind"]].astype(float) / 100
    solar_degradation = inputs_df.loc[21, ["Solar", "Wind"]].astype(float) / 100
    gaf = inputs_df.loc[22, ["Solar", "Wind"]].astype(float) / 100

    lcoe_results = {}
    capital_metrics = {}

    for tech in ["Solar", "Wind"]:
        plant_life_years = int(project_life[tech])
        gross_capital_cost = cap_cost[tech] * size[tech]
        net_capital_cost = (cap_cost[tech] - subsidy[tech]) * size[tech]
        equity = net_capital_cost * equity_pct[tech]
        debt = net_capital_cost - equity
        dep_first_nyear_gross_capex = gross_capital_cost * depr_rate[tech] * dep_cap_pct[tech]
        if n1_years[tech] < plant_life_years:
            dep_after_n1years_gross_capex = (gross_capital_cost * dep_cap_pct[tech] - dep_first_nyear_gross_capex * n1_years[tech]) / (plant_life_years - n1_years[tech])
        else:
            dep_after_n1years_gross_capex = 0
        dep_first_nyear_net_capex = net_capital_cost * depr_rate[tech] * dep_cap_pct[tech]
        if n1_years[tech] < plant_life_years:
            dep_after_n1years_net_capex = (net_capital_cost * dep_cap_pct[tech] - dep_first_nyear_net_capex * n1_years[tech]) / (plant_life_years - n1_years[tech])
        else:
            dep_after_n1years_net_capex = 0
        
        capital_metrics[tech] = {
            "Gross Capital Cost": round(gross_capital_cost, 2),
            "Net Capital Cost": round(net_capital_cost, 2),
            "Equity": round(equity, 2),
            "Debt": round(debt, 2),
            "Annual Depreciation for first n1 years (on gross capex)": round(dep_first_nyear_gross_capex, 2),
            "Annual Depreciation for after n1 years (on gross capex)": round(dep_after_n1years_gross_capex, 2),
            "Annual Depreciation for first n1 years (on net capex)": round(dep_first_nyear_net_capex, 2),
            "Annual Depreciation for after n1 years (on net capex)": round(dep_after_n1years_net_capex, 2),
        }
        
        total_discounted_cost = 0
        total_discounted_generation = 0
        
        current_asset_value = gross_capital_cost
        debt_closing_balance_prev = debt  # Initialize with full debt amount
        
        for year in range(1, plant_life_years + 1):
            if tech == "Solar":
                annual_degradation_factor = (1 - solar_degradation[tech]) ** (year - 1)
            else:
                annual_degradation_factor = 1
                
            gross_gen = size[tech] * cuf[tech] * gaf[tech] * 8760 * annual_degradation_factor
            net_gen = gross_gen * (1 - auxiliary_consumption[tech])
            onm_cost = gross_capital_cost * onm_pct[tech] * ((1 + onm_growth[tech]) ** (year - 1))
            
            if year <= n1_years[tech]:
                depreciation = dep_first_nyear_gross_capex
            else:
                depreciation = dep_after_n1years_gross_capex
                
            insurance_cost = current_asset_value * insurance_pct[tech]
            current_asset_value = max(0, current_asset_value - depreciation)

            if year == 1:
                debt_opening_balance = debt
            else:
                debt_opening_balance = debt_closing_balance_prev

            if year <= moratorium[tech]:
                debt_repayment = 0
            elif year <= (loan_tenure[tech] + moratorium[tech]):
                if debt_opening_balance > 0.001:
                    debt_repayment = debt / loan_tenure[tech] if loan_tenure[tech] > 0 else 0
                else:
                    debt_repayment = 0
            else:
                debt_repayment = 0

            interest_payment = debt_opening_balance * loan_int_pct[tech]
            debt_closing_balance = max(0, debt_opening_balance - debt_repayment)
            debt_closing_balance_prev = debt_closing_balance
            
            roe_cost = equity * roe[tech]
            
            # Calculate working capital using the corrected formulas
            # O&M Working Capital = onm_cost / (12 / wc_om_months)
            wc_om = onm_cost / (12 / wc_om_months[tech]) if wc_om_months[tech] > 0 else 0
            
            # Interest on O&M Working Capital
            wc_om_interest = wc_om * wc_interest[tech]
            
            # Receivables Working Capital
            if wc_receivables_months[tech] > 0:
                total_expenses = onm_cost + insurance_cost + depreciation + interest_payment + roe_cost + wc_om_interest
                wc_receivables = total_expenses / (12 / wc_receivables_months[tech])
            else:
                wc_receivables = 0
            
            # Interest on Receivables Working Capital
            wc_receivables_interest = wc_receivables * wc_interest[tech]
            
            # Total working capital interest cost
            wc_interest_cost = wc_om_interest + wc_receivables_interest
            
            total_annual_cost = onm_cost + insurance_cost + depreciation + interest_payment + wc_interest_cost + roe_cost   
            discount_factor = 1 / ((1 + discount_rate[tech]) ** (year - 1))
            total_discounted_cost += total_annual_cost * discount_factor
            total_discounted_generation += net_gen * discount_factor
            
        lcoe = total_discounted_cost / total_discounted_generation if total_discounted_generation > 0 else 0
        lcoe_results[tech] = round(lcoe, 4)
        
    return lcoe_results, capital_metrics

def compute_asset_depreciation(gross_capex, lcoe_breakdown_data, plant_life, tech):
    """
    Compute asset depreciation using gross capex and depreciation values from LCOE breakdown
    """
    data = []
    current_asset_value = gross_capex
    
    for year in range(1, plant_life + 1):
        # Add current year's asset value (opening balance)
        data.append({
            'Year': year,
            'Asset value': round(current_asset_value, 2)
        })
        
        # Get depreciation from LCOE breakdown for next year's calculation
        if not lcoe_breakdown_data.empty and len(lcoe_breakdown_data) >= year:
            year_data = lcoe_breakdown_data[lcoe_breakdown_data['Year'] == year]
            if not year_data.empty:
                depreciation = year_data.iloc[0]["Depreciation (on gross capital cost)"]
            else:
                depreciation = 0
        else:
            depreciation = 0
        
        # Update asset value for next iteration
        current_asset_value = max(0, current_asset_value - depreciation)
    
    df = pd.DataFrame(data)
    return df

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='*******', #Enter password
        database='imdb'
    )

def save_financial_data_to_db(project_id, run_number, solar_data, wind_data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now()
        
        # Save Solar Debt Data
        for i, row in solar_data['debt_df'].iterrows():
            if isinstance(i, str) and 'Year' in i:
                year = int(i.split()[1])
            else:
                year = int(i) + 1
            
            debt_query = """
            INSERT INTO besos_fin_analysis_solar_debt 
            (project_id, run_number, year, debt_opening_balance, debt_repayment, debt_closing_balance, interest, total_debt_service, calculated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            debt_opening_balance = %s,
            debt_repayment = %s,
            debt_closing_balance = %s,
            interest = %s,
            total_debt_service = %s,
            calculated_at = %s
            """
            cursor.execute(debt_query, (
                project_id, run_number, year,
                float(row.get('Debt opening balance', 0)),
                float(row.get('Debt repayment', 0)),
                float(row.get('Debt closing balance', 0)),
                float(row.get('Interest', 0)),
                float(row.get('Total debt service', 0)),
                current_time,
                float(row.get('Debt opening balance', 0)),
                float(row.get('Debt repayment', 0)),
                float(row.get('Debt closing balance', 0)),
                float(row.get('Interest', 0)),
                float(row.get('Total debt service', 0)),
                current_time
            ))
        
        # Save Solar Working Capital Data
        for i, row in solar_data['wc_df'].iterrows():
            if isinstance(i, str) and 'Year' in i:
                year = int(i.split()[1])
            else:
                year = int(i) + 1
            
            wc_query = """
            INSERT INTO besos_fin_analysis_solar_working_capital 
            (project_id, run_number, year, operation_maintenance_wcap, interest_on_wc_om, receivables_wcap, interest_on_receivables_wcap, total_working_capital, interest_on_working_capital, calculated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            operation_maintenance_wcap = %s,
            interest_on_wc_om = %s,
            receivables_wcap = %s,
            interest_on_receivables_wcap = %s,
            total_working_capital = %s,
            interest_on_working_capital = %s,
            calculated_at = %s
            """
            cursor.execute(wc_query, (
                project_id, run_number, year,
                float(row.get('Operation and Maintenance wcap', 0)),
                float(row.get('Interest on working capital - O&M', 0)),
                float(row.get('Receivables wcap', 0)),
                float(row.get('Interest on receivables wcap', 0)),
                float(row.get('Total Working Capital', 0)),
                float(row.get('Interest on working capital', 0)),
                current_time,
                float(row.get('Operation and Maintenance wcap', 0)),
                float(row.get('Interest on working capital - O&M', 0)),
                float(row.get('Receivables wcap', 0)),
                float(row.get('Interest on receivables wcap', 0)),
                float(row.get('Total Working Capital', 0)),
                float(row.get('Interest on working capital', 0)),
                current_time
            ))
        
        # Save Solar Asset Data
        for i, row in solar_data['asset_df'].iterrows():
            if isinstance(i, str) and 'Year' in i:
                year = int(i.split()[1])
            else:
                year = int(i) + 1
            
            asset_query = """
            INSERT INTO besos_fin_analysis_solar_asset 
            (project_id, run_number, year, asset_value, calculated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            asset_value = %s,
            calculated_at = %s
            """
            cursor.execute(asset_query, (
                project_id, run_number, year,
                float(row.get('Asset value', 0)),
                current_time,
                float(row.get('Asset value', 0)),
                current_time
            ))
        
        # Save Wind Debt Data
        for i, row in wind_data['debt_df'].iterrows():
            if isinstance(i, str) and 'Year' in i:
                year = int(i.split()[1])
            else:
                year = int(i) + 1
            
            debt_query = """
            INSERT INTO besos_fin_analysis_wind_debt 
            (project_id, run_number, year, debt_opening_balance, debt_repayment, debt_closing_balance, interest, total_debt_service, calculated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            debt_opening_balance = %s,
            debt_repayment = %s,
            debt_closing_balance = %s,
            interest = %s,
            total_debt_service = %s,
            calculated_at = %s
            """
            cursor.execute(debt_query, (
                project_id, run_number, year,
                float(row.get('Debt opening balance', 0)),
                float(row.get('Debt repayment', 0)),
                float(row.get('Debt closing balance', 0)),
                float(row.get('Interest', 0)),
                float(row.get('Total debt service', 0)),
                current_time,
                float(row.get('Debt opening balance', 0)),
                float(row.get('Debt repayment', 0)),
                float(row.get('Debt closing balance', 0)),
                float(row.get('Interest', 0)),
                float(row.get('Total debt service', 0)),
                current_time
            ))
        
        # Save Wind Working Capital Data
        for i, row in wind_data['wc_df'].iterrows():
            if isinstance(i, str) and 'Year' in i:
                year = int(i.split()[1])
            else:
                year = int(i) + 1
            
            wc_query = """
            INSERT INTO besos_fin_analysis_wind_working_capital 
            (project_id, run_number, year, operation_maintenance_wcap, interest_on_wc_om, receivables_wcap, interest_on_receivables_wcap, total_working_capital, interest_on_working_capital, calculated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            operation_maintenance_wcap = %s,
            interest_on_wc_om = %s,
            receivables_wcap = %s,
            interest_on_receivables_wcap = %s,
            total_working_capital = %s,
            interest_on_working_capital = %s,
            calculated_at = %s
            """
            cursor.execute(wc_query, (
                project_id, run_number, year,
                float(row.get('Operation and Maintenance wcap', 0)),
                float(row.get('Interest on working capital - O&M', 0)),
                float(row.get('Receivables wcap', 0)),
                float(row.get('Interest on receivables wcap', 0)),
                float(row.get('Total Working Capital', 0)),
                float(row.get('Interest on working capital', 0)),
                current_time,
                float(row.get('Operation and Maintenance wcap', 0)),
                float(row.get('Interest on working capital - O&M', 0)),
                float(row.get('Receivables wcap', 0)),
                float(row.get('Interest on receivables wcap', 0)),
                float(row.get('Total Working Capital', 0)),
                float(row.get('Interest on working capital', 0)),
                current_time
            ))
        
        # Save Wind Asset Data
        for i, row in wind_data['asset_df'].iterrows():
            if isinstance(i, str) and 'Year' in i:
                year = int(i.split()[1])
            else:
                year = int(i) + 1
            
            asset_query = """
            INSERT INTO besos_fin_analysis_wind_asset 
            (project_id, run_number, year, asset_value, calculated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            asset_value = %s,
            calculated_at = %s
            """
            cursor.execute(asset_query, (
                project_id, run_number, year,
                float(row.get('Asset value', 0)),
                current_time,
                float(row.get('Asset value', 0)),
                current_time
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Financial analysis data saved to database successfully"
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Detailed error: {error_details}")
        return False, f"Error saving financial analysis to database: {str(e)}"

st.set_page_config(page_title="General Outputs", layout="wide")
st.title("LCOE Analysis and Financial Insights")

project_id = None
if "current_project_inputs" in st.session_state and "project_id" in st.session_state["current_project_inputs"]:
    project_id = st.session_state["current_project_inputs"]["project_id"]
    st.session_state["current_project_id"] = project_id
else:
    optimizer_keys = ["optimizer_project_id", "selected_optimizer_project_id", "optimizer_selected_project"]
    for key in optimizer_keys:
        if key in st.session_state and st.session_state[key]:
            project_id = st.session_state[key]
            st.session_state["current_project_id"] = project_id
            break
    if not project_id:
        if "current_project_id" in st.session_state and st.session_state["current_project_id"]:
            project_id = st.session_state["current_project_id"]
        elif "selected_project_id" in st.session_state and st.session_state["selected_project_id"]:
            project_id = st.session_state["selected_project_id"]
            st.session_state["current_project_id"] = project_id
run_number = None
optimizer_run_keys = ["optimizer_current_run", "optimizer_run_id", "optimizer_latest_run", "optimizer_selected_run"]

if "current_project_inputs" in st.session_state and "run_number" in st.session_state["current_project_inputs"]:
    run_number = st.session_state["current_project_inputs"]["run_number"]
    st.session_state["run_number"] = run_number
    st.session_state["lcoe_run_number"] = run_number
    st.session_state["optimizer_run_number"] = run_number
    with st.expander("Project Information"):
        st.write("Current Project ID:", project_id if 'project_id' in locals() else st.session_state.get("current_project_id", "Not set"))
        st.write("Current Run Number:", run_number if 'run_number' in locals() else st.session_state.get("lcoe_run_number", "Not set"))
else:
    optimizer_run_keys = ["optimizer_current_run", "optimizer_run_id", "optimizer_latest_run", "optimizer_selected_run"]
    for key in optimizer_run_keys:
        if key in st.session_state and st.session_state[key]:
            run_number = st.session_state[key]
            break
    if not run_number:
        if "optimizer_run_number" in st.session_state:
            run_number = st.session_state["optimizer_run_number"]
        elif "run_number" in st.session_state:
            run_number = st.session_state["run_number"]
        else:
            run_number = 1

st.session_state["run_number"] = run_number
st.session_state["lcoe_run_number"] = run_number
st.session_state["optimizer_run_number"] = run_number
if f"lcoe_calculated_{project_id}_{run_number}" in st.session_state:
    del st.session_state[f"lcoe_calculated_{project_id}_{run_number}"]
if f"fin_data_saved_{project_id}_{run_number}" in st.session_state:
    del st.session_state[f"fin_data_saved_{project_id}_{run_number}"]
if "current_project_inputs" in st.session_state:
    project_inputs = st.session_state["current_project_inputs"]
    params = [
        "System Capital Cost (Per KW)", "Capital Subsidy (Per KW)", "Plant Size (KW)",
        "Project Life of Plant (Years)", "Capacity Utilization Factor (%)", "Auxiliary Consumption (%)",
        "Discount Rate (%)", "Equity (%)", "Return on Equity (%)", "Loan Tenure (years)",
        "Moratorium (years)", "Interest on Loan (%)", "Operation and Maintenance Expenses in year 1 (%)",
        "Annual increase in Operation and Maintenance expenses (%)", "Insurance(%) of depreciated asset value)",
        "Working Capital - O & M (months)", "Working Capital - Receivables (months)",
        "Interest on Working Capital (%)", "n1 years", "Depreciation rate for the first n1 years (%)",
        "Percentage of capital cost on which depreciation applies (%)",
        "Annual Solar Panel Degradation (%)", "Grid Availability Factor (%)"
    ]
    db_col_to_param_map = {
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
        "grid_availability": "Grid Availability Factor (%)"
    }
    general_inputs = project_inputs.get("general_inputs", {})
    solar_values = []
    wind_values = []
    bess_values = []
    defaults = {
        "Solar": [33500, 0, 1000, 25, 19, 0, 9.53, 30, 17.60, 10, 1, 10.55, 1.40, 5.72, 0.35, 1, 2, 11.55, 25, 3.60, 95, 2, 95], 
        "Wind": [52500, 0, 1000, 25, 29.15, 0, 9.53, 30, 17.60, 10, 1, 10.55, 0.968, 5.72, 0.64, 1, 2, 11.55, 25, 3.60, 85, 0, 95],
        "BESS": [20000, 0, 100, 25, 85, 0, 8, 30, 16, 10, 1, 10.5, 1, 5.72, 0.35, 1, 1, 10.5, 13, 5.28, 95, 0, 100]
    }
    for i, param in enumerate(params):
        db_col = None
        for col, p in db_col_to_param_map.items():
            if p == param:
                db_col = col
                break
        if db_col:
            solar_val = general_inputs.get("Solar", {}).get(db_col, defaults["Solar"][i])
            wind_val = general_inputs.get("Wind", {}).get(db_col, defaults["Wind"][i])
            bess_val = general_inputs.get("BESS", {}).get(db_col, defaults["BESS"][i])
            solar_values.append(solar_val)
            wind_values.append(wind_val)
            bess_values.append(bess_val)
        else:
            solar_values.append(defaults["Solar"][i])
            wind_values.append(defaults["Wind"][i])
            bess_values.append(defaults["BESS"][i])
    inputs_df = pd.DataFrame({
        "Parameter": params,
        "Solar": solar_values,
        "Wind": wind_values,
        "BESS": bess_values
    })
    # st.write("DEBUG: Input values being used:")
    # st.write(f"Solar System Capital Cost: {inputs_df.loc[0, 'Solar']}")
    # st.write(f"Solar Plant Size: {inputs_df.loc[2, 'Solar']}")
    # st.write(f"Wind System Capital Cost: {inputs_df.loc[0, 'Wind']}")
    # st.write(f"Wind Plant Size: {inputs_df.loc[2, 'Wind']}")
    # st.write(f"Expected Solar Gross Capital Cost: {float(inputs_df.loc[0, 'Solar']) * float(inputs_df.loc[2, 'Solar'])}")
    # st.write(f"Expected Wind Gross Capital Cost: {float(inputs_df.loc[0, 'Wind']) * float(inputs_df.loc[2, 'Wind'])}")
    st.session_state["inputs_df"] = inputs_df
    st.session_state["optimizer_run_triggered"] = False
else:
    st.error("No project inputs found in session state. Please go back to Optimizer page.")

if "inputs_df" not in st.session_state:
    st.warning("Please complete the Optimizer Inputs first.")
    if st.button("Go to Configure Optimizer"):
        st.switch_page("Pages/4_Configure_Optimizer.py")
    st.stop()
inputs_df = st.session_state["inputs_df"]
with st.expander("View Input Data"):
    st.dataframe(inputs_df, hide_index=True)
st.markdown("""
<style>
    div.stButton > button {
        background-color: #0066cc !important;
        color: white !important;
        border: none !important;
    }
    div.stButton > button:hover {
        background-color: #004c99 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

_, _, _, col_calc_button, col_ai_button = st.columns([4, 1, 1, 1, 1])

with col_calc_button:
    calculate_lcoe_clicked = st.button("Calculate LCOE", key="calculate_lcoe_btn")

with col_ai_button:
    check_ai_clicked = st.button("Get Analysis from AI", key="check_ai_btn", 
                            disabled=not ("lcoe_result" in st.session_state))
if calculate_lcoe_clicked:
    with st.spinner("Calculating LCOE..."):
        lcoe_results, capital_metrics = calculate_lcoe(inputs_df)    
    if lcoe_results['Solar'] != 'Error' and lcoe_results['Wind'] != 'Error':
        st.session_state["lcoe_result"] = pd.DataFrame([
            {"Technology": tech, "LCOE (INR/kWh)": val} for tech, val in lcoe_results.items()
        ])
        st.session_state["capital_metrics"] = capital_metrics        
        lcoe_df = st.session_state["lcoe_result"]
        st.session_state["solar_lcoe"] = lcoe_df[lcoe_df["Technology"] == "Solar"]["LCOE (INR/kWh)"].iloc[0] if not lcoe_df[lcoe_df["Technology"] == "Solar"].empty else 0
        st.session_state["wind_lcoe"] = lcoe_df[lcoe_df["Technology"] == "Wind"]["LCOE (INR/kWh)"].iloc[0] if not lcoe_df[lcoe_df["Technology"] == "Wind"].empty else 0        
        lcoe_key = f"lcoe_calculated_{project_id}_{run_number}"
        st.session_state[lcoe_key] = True            
        try:
            if "current_project_id" in st.session_state and st.session_state["current_project_id"]:
                project_id = st.session_state["current_project_id"]
            elif "selected_project_id" in st.session_state and st.session_state["selected_project_id"]:
                project_id = st.session_state["selected_project_id"]
                st.session_state["current_project_id"] = project_id
            else:
                st.error("No project ID found in session state. Please return to the previous page to select a project.")
                st.stop()            
            run_number = st.session_state["lcoe_run_number"]
            conn = get_db_connection()
            cursor = conn.cursor()            
            for tech, lcoe_value in lcoe_results.items():
                sql = """
                INSERT INTO besos_lcoe_results 
                (project_id, run_number, technology, lcoe_value, calculated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                lcoe_value = %s,
                calculated_at = %s
                """ 
                current_time = datetime.now()
                safe_lcoe_value = handle_nan_value(lcoe_value, default=0)
                cursor.execute(
                    sql, 
                    (
                        project_id,
                        run_number,
                        tech,
                        safe_lcoe_value,
                        current_time,
                        safe_lcoe_value,
                        current_time
                    )
                )            
            conn.commit()
            st.success("LCOE results saved to database")
            
            # Save general outputs (capital metrics) to database
            try:
                for tech in ["Solar", "Wind"]:
                    capital_data = capital_metrics[tech]
                    gen_out_sql = """
                    INSERT INTO besos_gen_out 
                    (project_id, run_number, technology, gross_capital_cost, net_capital_cost, 
                     equity, debt, annual_depreciation_first_n1_gross_capex, 
                     annual_depreciation_after_n1_gross_capex, annual_depreciation_first_n1_net_capex, 
                     annual_depreciation_after_n1_net_capex, calculated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    gross_capital_cost = %s,
                    net_capital_cost = %s,
                    equity = %s,
                    debt = %s,
                    annual_depreciation_first_n1_gross_capex = %s,
                    annual_depreciation_after_n1_gross_capex = %s,
                    annual_depreciation_first_n1_net_capex = %s,
                    annual_depreciation_after_n1_net_capex = %s,
                    calculated_at = %s
                    """
                    cursor.execute(gen_out_sql, (
                        project_id, run_number, tech,
                        float(capital_data["Gross Capital Cost"]),
                        float(capital_data["Net Capital Cost"]),
                        float(capital_data["Equity"]),
                        float(capital_data["Debt"]),
                        float(capital_data["Annual Depreciation for first n1 years (on gross capex)"]),
                        float(capital_data["Annual Depreciation for after n1 years (on gross capex)"]),
                        float(capital_data["Annual Depreciation for first n1 years (on net capex)"]),
                        float(capital_data["Annual Depreciation for after n1 years (on net capex)"]),
                        current_time,
                        # ON DUPLICATE KEY UPDATE values
                        float(capital_data["Gross Capital Cost"]),
                        float(capital_data["Net Capital Cost"]),
                        float(capital_data["Equity"]),
                        float(capital_data["Debt"]),
                        float(capital_data["Annual Depreciation for first n1 years (on gross capex)"]),
                        float(capital_data["Annual Depreciation for after n1 years (on gross capex)"]),
                        float(capital_data["Annual Depreciation for first n1 years (on net capex)"]),
                        float(capital_data["Annual Depreciation for after n1 years (on net capex)"]),
                        current_time
                    ))
                
                conn.commit()
                # st.success("General outputs saved to database")
                
            except Exception as e:
                st.error(f"Error saving general outputs to database: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
            
            with st.spinner("Calculating and saving LCOE breakdown..."):
                rows = []
                
                # Get plant life for each technology separately
                plant_life_solar = int(get_param_value(inputs_df, "Project Life of Plant (Years)", "Solar", 25))
                plant_life_wind = int(get_param_value(inputs_df, "Project Life of Plant (Years)", "Wind", 25))
                
                for tech in ["Solar", "Wind"]:
                    # Use technology-specific plant life
                    plant_life = plant_life_solar if tech == "Solar" else plant_life_wind
                    
                    # Get all parameters specific to the technology
                    cap_cost = get_param_value(inputs_df, "System Capital Cost (Per KW)", tech, 33500 if tech == "Solar" else 52500)
                    size = get_param_value(inputs_df, "Plant Size (KW)", tech, 1000 if tech == "Solar" else 1000)
                    cuf = get_param_value(inputs_df, "Capacity Utilization Factor (%)", tech, 19 if tech == "Solar" else 29.15) / 100
                    gaf = get_param_value(inputs_df, "Grid Availability Factor (%)", tech, 95) / 100
                    auxiliary = get_param_value(inputs_df, "Auxiliary Consumption (%)", tech, 0) / 100
                    onm_pct = get_param_value(inputs_df, "Operation and Maintenance Expenses in year 1 (%)", tech, 1.40 if tech == "Solar" else 0.968) / 100
                    insurance_pct = get_param_value(inputs_df, "Insurance(%) of depreciated asset value)", tech, 0.35 if tech == "Solar" else 0.64) / 100
                    depr_rate = get_param_value(inputs_df, "Depreciation rate for the first n1 years (%)", tech, 3.60) / 100
                    depr_cap_pct = get_param_value(inputs_df, "Percentage of capital cost on which depreciation applies (%)", tech, 95 if tech == "Solar" else 85) / 100
                    subsidy = get_param_value(inputs_df, "Capital Subsidy (Per KW)", tech, 0)
                    equity_pct = get_param_value(inputs_df, "Equity (%)", tech, 30) / 100
                    loan_int_pct = get_param_value(inputs_df, "Interest on Loan (%)", tech, 10.55) / 100
                    discount_rate = get_param_value(inputs_df, "Discount Rate (%)", tech, 9.53) / 100
                    wc_interest = get_param_value(inputs_df, "Interest on Working Capital (%)", tech, 11.55) / 100
                    roe_pct = get_param_value(inputs_df, "Return on Equity (%)", tech, 17.60) / 100
                    loan_tenure = get_param_value(inputs_df, "Loan Tenure (years)", tech, 10)
                    moratorium = get_param_value(inputs_df, "Moratorium (years)", tech, 1)
                    onm_growth = get_param_value(inputs_df, "Annual increase in Operation and Maintenance expenses (%)", tech, 5.72) / 100
                    solar_degradation = get_param_value(inputs_df, "Annual Solar Panel Degradation (%)", tech, 2) / 100
                    n1_years = get_param_value(inputs_df, "n1 years", tech, 25)
                    wc_om_months = get_param_value(inputs_df, "Working Capital - O & M (months)", tech, 1)
                    wc_receivables_months = get_param_value(inputs_df, "Working Capital - Receivables (months)", tech, 2)
                    
                    # Calculate capital costs
                    gross_capex = cap_cost * size
                    net_capex = (cap_cost - subsidy) * size
                    equity = net_capex * equity_pct
                    debt = net_capex - equity
                    
                    # Calculate depreciation values
                    dep_first_nyear_gross = gross_capex * depr_cap_pct * depr_rate
                    if n1_years < plant_life:
                        dep_after_n1years_gross = (gross_capex * depr_cap_pct - dep_first_nyear_gross * n1_years) / (plant_life - n1_years)
                    else:
                        dep_after_n1years_gross = 0
                        
                    dep_first_nyear_net = net_capex * depr_cap_pct * depr_rate
                    if n1_years < plant_life:
                        dep_after_n1years_net = (net_capex * depr_cap_pct - dep_first_nyear_net * n1_years) / (plant_life - n1_years)
                    else:
                        dep_after_n1years_net = 0
                    
                    current_asset_value_breakdown = gross_capex
                    
                    # Generate debt schedule for this technology
                    debt_schedule = compute_debt_schedule(net_capex, equity_pct, loan_int_pct, loan_tenure, plant_life, moratorium)
                    
                    for year in range(plant_life):
                        year_num = year + 1
                        
                        if tech == "Solar":
                            annual_degradation_factor = (1 - solar_degradation) ** (year_num - 1)
                        else:
                            annual_degradation_factor = 1
                        
                        yearly_gross_gen = size * cuf * gaf * 8760 * annual_degradation_factor
                        yearly_net_gen = yearly_gross_gen * (1 - auxiliary)
                        
                        # Continue with rest of your existing code...
                        yearly_onm_cost = gross_capex * onm_pct * ((1 + onm_growth) ** year)
                        
                        # Calculate depreciation based on year
                        if year_num <= n1_years:
                            yearly_depreciation_gross = dep_first_nyear_gross
                            yearly_depreciation_net = dep_first_nyear_net
                        else:
                            yearly_depreciation_gross = dep_after_n1years_gross
                            yearly_depreciation_net = dep_after_n1years_net
                        
                        # Calculate insurance on current asset value
                        yearly_insurance_cost = current_asset_value_breakdown * insurance_pct
                        
                        # Update asset value for next year
                        current_asset_value_breakdown = max(0, current_asset_value_breakdown - yearly_depreciation_gross)
                        
                        # Get interest payment from debt schedule
                        yearly_interest_payment = debt_schedule.iloc[year_num - 1]['Interest']
                        
                        wc_om = (yearly_onm_cost / 12) * wc_om_months
                        wc_om_interest = wc_om * wc_interest
                        yearly_roe_cost = equity * roe_pct

                        # Calculate receivables working capital with proper total expenses including ROE and O&M working capital interest
                        if wc_receivables_months > 0:
                            total_expenses_for_receivables = yearly_onm_cost + yearly_insurance_cost + yearly_depreciation_gross + yearly_interest_payment + yearly_roe_cost + wc_om_interest
                            wc_receivables = (total_expenses_for_receivables / 12) * wc_receivables_months
                        else:
                            wc_receivables = 0

                        wc_receivables_interest = wc_receivables * wc_interest
                        yearly_wc_int = wc_om_interest + wc_receivables_interest
                        
                        # Calculate total cost
                        yearly_total_cost = yearly_onm_cost + yearly_insurance_cost + yearly_depreciation_gross + yearly_interest_payment + yearly_wc_int + yearly_roe_cost
                        
                        # Calculate cost per kWh
                        cost_per_kwh = yearly_total_cost / yearly_net_gen if yearly_net_gen > 0 else 0
                        
                        # Calculate discount factor and present values
                        discount_factor = 1 / ((1 + discount_rate) ** (year_num - 1))
                        present_value = cost_per_kwh * discount_factor
                        present_value_cost = yearly_total_cost * discount_factor
                        present_value_gen = yearly_net_gen * discount_factor
                        
                        rows.append({
                            "Technology": tech,
                            "Year": year_num,
                            "Gross generation / kWh input (for Storage)": round(yearly_gross_gen, 2),
                            "Net generation / kWh available (for Storage)": round(yearly_net_gen, 2),
                            "Operation and Maintenance Expenses": round(yearly_onm_cost, 2),
                            "Insurance": round(yearly_insurance_cost, 2),
                            "Depreciation (on gross capital cost)": round(yearly_depreciation_gross, 2),
                            "Depreciation (on net capital cost)": round(yearly_depreciation_net, 2),
                            "Interest on Term Loan": round(yearly_interest_payment, 2),
                            "Interest on Working Capital": round(yearly_wc_int, 2),
                            "Return on Equity": round(yearly_roe_cost, 2),
                            "Total Cost of Generation": round(yearly_total_cost, 2),
                            "Cost Of Generation per kWh": round(cost_per_kwh, 4),
                            "Discount factor": round(discount_factor, 6),
                            "Present value": round(present_value, 6),
                            "Annual Cost (INR)": round(yearly_total_cost, 2),
                            "Discounted Cost (INR)": round(present_value_cost, 2),
                            "Discounted Gen (kWh)": round(present_value_gen, 2)
                        })
                
                df_breakdown = pd.DataFrame(rows)
                st.session_state["lcoe_breakdown"] = df_breakdown
                
                # Save to database (rest of the database code remains the same)
                for _, row in df_breakdown.iterrows():
                    tech = row["Technology"]
                    year_num = int(row["Year"])
                    breakdown_sql = """
                    INSERT INTO besos_lcoe_breakdown
                    (project_id, run_number, technology, year, gross_generation_kwh_input, 
                    net_generation_kwh_available, operation_maintenance_expenses, insurance, 
                    depreciation_gross_capital, depreciation_net_capital, interest_term_loan, 
                    interest_working_capital, return_on_equity, total_cost_generation, 
                    cost_generation_per_kwh, discount_factor, present_value, annual_cost_inr, 
                    discounted_cost_inr, discounted_gen_kwh, calculated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    gross_generation_kwh_input = %s,
                    net_generation_kwh_available = %s,
                    operation_maintenance_expenses = %s,
                    insurance = %s,
                    depreciation_gross_capital = %s,
                    depreciation_net_capital = %s,
                    interest_term_loan = %s,
                    interest_working_capital = %s,
                    return_on_equity = %s,
                    total_cost_generation = %s,
                    cost_generation_per_kwh = %s,
                    discount_factor = %s,
                    present_value = %s,
                    annual_cost_inr = %s,
                    discounted_cost_inr = %s,
                    discounted_gen_kwh = %s,
                    calculated_at = %s
                    """
                    cursor.execute(
                        breakdown_sql,
                        (
                            project_id,
                            run_number,
                            tech,
                            year_num,
                            handle_nan_value(row["Gross generation / kWh input (for Storage)"]),
                            handle_nan_value(row["Net generation / kWh available (for Storage)"]),
                            handle_nan_value(row["Operation and Maintenance Expenses"]),
                            handle_nan_value(row["Insurance"]),
                            handle_nan_value(row["Depreciation (on gross capital cost)"]),
                            handle_nan_value(row["Depreciation (on net capital cost)"]),
                            handle_nan_value(row["Interest on Term Loan"]),
                            handle_nan_value(row["Interest on Working Capital"]),
                            handle_nan_value(row["Return on Equity"]),
                            handle_nan_value(row["Total Cost of Generation"]),
                            handle_nan_value(row["Cost Of Generation per kWh"]),
                            handle_nan_value(row["Discount factor"]),
                            handle_nan_value(row["Present value"]),
                            handle_nan_value(row["Annual Cost (INR)"]),
                            handle_nan_value(row["Discounted Cost (INR)"]),
                            handle_nan_value(row["Discounted Gen (kWh)"]),
                            current_time,
                            # ON DUPLICATE KEY UPDATE values
                            handle_nan_value(row["Gross generation / kWh input (for Storage)"]),
                            handle_nan_value(row["Net generation / kWh available (for Storage)"]),
                            handle_nan_value(row["Operation and Maintenance Expenses"]),
                            handle_nan_value(row["Insurance"]),
                            handle_nan_value(row["Depreciation (on gross capital cost)"]),
                            handle_nan_value(row["Depreciation (on net capital cost)"]),
                            handle_nan_value(row["Interest on Term Loan"]),
                            handle_nan_value(row["Interest on Working Capital"]),
                            handle_nan_value(row["Return on Equity"]),
                            handle_nan_value(row["Total Cost of Generation"]),
                            handle_nan_value(row["Cost Of Generation per kWh"]),
                            handle_nan_value(row["Discount factor"]),
                            handle_nan_value(row["Present value"]),
                            handle_nan_value(row["Annual Cost (INR)"]),
                            handle_nan_value(row["Discounted Cost (INR)"]),
                            handle_nan_value(row["Discounted Gen (kWh)"]),
                            current_time
                        )
                    )
                conn.commit()
                # st.success("LCOE breakdown saved to database")
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error saving LCOE results to database: {str(e)}")
            import traceback
            st.error(traceback.format_exc())

if check_ai_clicked:
    if "lcoe_result" in st.session_state and "inputs_df" in st.session_state:
        with st.spinner("Getting business interpretation from Gemini AI..."):
            # Get LCOE results
            my_lcoe_df = st.session_state["lcoe_result"]
            my_lcoe = {row["Technology"]: row["LCOE (INR/kWh)"] for _, row in my_lcoe_df.iterrows()}
            
            # Get capital metrics
            capital_metrics = st.session_state.get("capital_metrics", {})
            
            # Get project info if available
            project_info = {
                'site_name': st.session_state.get('site_name', 'Not specified'),
                'state': st.session_state.get('state', 'Not specified'), 
                'location': st.session_state.get('location', 'Not specified')
            }
            
            success, ai_response = get_lcoe_interpretation_with_gemini(
                st.session_state["inputs_df"], 
                my_lcoe, 
                capital_metrics, 
                project_info
            )

            if success:
                st.session_state["ai_interpretation_response"] = ai_response
                st.session_state["ai_interpretation_completed"] = True
                st.rerun()
            else:
                st.error(f"AI interpretation failed: {ai_response}")
                st.session_state["ai_interpretation_error"] = ai_response
    else:
        st.warning("Please calculate LCOE first before getting AI interpretation.")

# Show success message if AI validation was just completed
if st.session_state.get("ai_validation_completed", False):
    st.success("AI validation completed successfully! Check the 'AI Validation' tab for detailed results.")
    # Reset the flag
    st.session_state["ai_validation_completed"] = False

st.header("Detailed Analysis")
general_outputs_tab, lcoe_breakdown_tab, financials_tab, ai_validation_tab = st.tabs(["General Outputs", "LCOE Breakdown", "Financial Details", "AI Validation"])

# Replace the existing general_outputs_tab section with this updated code:

with general_outputs_tab:
    st.subheader("General Outputs")
    if "capital_metrics" in st.session_state:
        capital_metrics = st.session_state["capital_metrics"]
        capital_metrics_data = {
            "General Output": [
                "Gross Capital Cost",
                "Net Capital Cost",
                "Equity",
                "Debt",
                "Annual Depreciation for first n1 years (on gross capex)",
                "Annual Depreciation for after n1 years (on gross capex)",
                "Annual Depreciation for first n1 years (on net capex)",
                "Annual Depreciation for after n1 years (on net capex)",
            ],
            "Unit": ["INR", "INR", "INR", "INR", "INR", "INR", "INR", "INR"],
            "Solar Value": [
                capital_metrics["Solar"]["Gross Capital Cost"],
                capital_metrics["Solar"]["Net Capital Cost"],
                capital_metrics["Solar"]["Equity"],
                capital_metrics["Solar"]["Debt"],
                capital_metrics["Solar"]["Annual Depreciation for first n1 years (on gross capex)"],
                capital_metrics["Solar"]["Annual Depreciation for after n1 years (on gross capex)"],
                capital_metrics["Solar"]["Annual Depreciation for first n1 years (on net capex)"],
                capital_metrics["Solar"]["Annual Depreciation for after n1 years (on net capex)"],
            ],
            "Wind Value": [
                capital_metrics["Wind"]["Gross Capital Cost"],
                capital_metrics["Wind"]["Net Capital Cost"],
                capital_metrics["Wind"]["Equity"],
                capital_metrics["Wind"]["Debt"],
                capital_metrics["Wind"]["Annual Depreciation for first n1 years (on gross capex)"],
                capital_metrics["Wind"]["Annual Depreciation for after n1 years (on gross capex)"],
                capital_metrics["Wind"]["Annual Depreciation for first n1 years (on net capex)"],
                capital_metrics["Wind"]["Annual Depreciation for after n1 years (on net capex)"],
            ],
        }        
        capital_df = pd.DataFrame(capital_metrics_data)
        st.dataframe(capital_df, hide_index=True)
    else:
        st.info("General outputs will be available after clicking 'Calculate LCOE' button above.")

with lcoe_breakdown_tab: 
    lcoe_key = f"lcoe_calculated_{project_id}_{run_number}"
    if lcoe_key in st.session_state and st.session_state[lcoe_key] and "lcoe_result" in st.session_state:
        lcoe_df = st.session_state["lcoe_result"]
        solar_lcoe = lcoe_df[lcoe_df["Technology"] == "Solar"]["LCOE (INR/kWh)"].iloc[0] if not lcoe_df[lcoe_df["Technology"] == "Solar"].empty else "Not calculated"
        wind_lcoe = lcoe_df[lcoe_df["Technology"] == "Wind"]["LCOE (INR/kWh)"].iloc[0] if not lcoe_df[lcoe_df["Technology"] == "Wind"].empty else "Not calculated"        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.metric(
                label="Solar LCOE", 
                value=f"{solar_lcoe:.4f} INR/kWh" if isinstance(solar_lcoe, (int, float)) else str(solar_lcoe),
                delta=None
            )
        with col2:
            st.metric(
                label="Wind LCOE", 
                value=f"{wind_lcoe:.4f} INR/kWh" if isinstance(wind_lcoe, (int, float)) else str(wind_lcoe),
                delta=None
            )        
        st.divider()
        
        st.subheader("LCOE Yearly Breakdown")
        if "lcoe_breakdown" in st.session_state:
            df_breakdown = st.session_state["lcoe_breakdown"]
            solar_tab, wind_tab = st.tabs(["Solar", "Wind"])
            with solar_tab:
                if "Technology" in df_breakdown.columns:
                    solar_data = df_breakdown[df_breakdown["Technology"] == "Solar"]
                else:
                    # If Technology column doesn't exist, assume all data is for the selected technology
                    solar_data = df_breakdown.copy()
                st.dataframe(solar_data.drop("Cost Breakdown", axis=1) if "Cost Breakdown" in solar_data.columns else solar_data, hide_index=True)
            with wind_tab:
                if "Technology" in df_breakdown.columns:
                    wind_data = df_breakdown[df_breakdown["Technology"] == "Wind"]
                else:
                    # If Technology column doesn't exist, assume all data is for the selected technology
                    wind_data = df_breakdown.copy()
                st.dataframe(wind_data.drop("Cost Breakdown", axis=1) if "Cost Breakdown" in wind_data.columns else wind_data, hide_index=True)
        else:
            st.info("LCOE breakdown will be available after calculation is complete.")
    else:
        st.info("Please click the 'Calculate LCOE' button above to see the results.")
        st.divider()
        st.subheader("LCOE Yearly Breakdown")

with financials_tab:
    # Extract plant life for both Solar and Wind
    try:
        if 'Parameter' in inputs_df.columns:
            plant_life_row = inputs_df[inputs_df['Parameter'] == "Project Life of Plant (Years)"]
            if not plant_life_row.empty:
                solar_plant_life = int(float(plant_life_row.iloc[0]["Solar"]))
                wind_plant_life = int(float(plant_life_row.iloc[0]["Wind"]))
            else:
                solar_plant_life = 25
                wind_plant_life = 25
        else:
            try:
                solar_plant_life = int(float(inputs_df.loc["Project Life of Plant (Years)", "Solar"]))
                wind_plant_life = int(float(inputs_df.loc["Project Life of Plant (Years)", "Wind"]))
            except:
                try:
                    solar_plant_life = int(float(inputs_df.iloc[3]["Solar"]))
                    wind_plant_life = int(float(inputs_df.iloc[3]["Wind"]))
                except:
                    solar_plant_life = 25
                    wind_plant_life = 25
    except:
        solar_plant_life = 25
        wind_plant_life = 25
    
    project_id = st.session_state.get("current_project_id", "default_project")
    run_number = st.session_state.get("lcoe_run_number", 1)
    solar_fin_tab, wind_fin_tab = st.tabs(["Solar", "Wind"])
    solar_data = {}
    wind_data = {}

    with solar_fin_tab:
        st.header("Solar Financial Analysis")        
        solar_cap_cost = get_param_value(inputs_df, "System Capital Cost (Per KW)", "Solar", 33500)
        solar_size = get_param_value(inputs_df, "Plant Size (KW)", "Solar", 1000)
        solar_subsidy = get_param_value(inputs_df, "Capital Subsidy (Per KW)", "Solar", 0)
        solar_capex = solar_cap_cost * solar_size
        solar_total_subsidy = solar_subsidy * solar_size
        solar_net_capex = solar_capex - solar_total_subsidy
        solar_equity_pct = get_param_value(inputs_df, "Equity (%)", "Solar", 30) / 100
        solar_loan_tenure = int(get_param_value(inputs_df, "Loan Tenure (years)", "Solar", 10))
        solar_interest_rate = get_param_value(inputs_df, "Interest on Loan (%)", "Solar", 10.55) / 100
        solar_o_and_m_pct = get_param_value(inputs_df, "Operation and Maintenance Expenses in year 1 (%)", "Solar", 1.40) / 100
        solar_receivable_months = get_param_value(inputs_df, "Working Capital - Receivables (months)", "Solar", 2)
        solar_wc_interest_rate = get_param_value(inputs_df, "Interest on Working Capital (%)", "Solar", 11.55) / 100
        solar_dep_rate = get_param_value(inputs_df, "Depreciation rate for the first n1 years (%)", "Solar", 3.60) / 100
        st.subheader("Debt")
        solar_moratorium = get_param_value(inputs_df, "Moratorium (years)", "Solar", 1)
        solar_debt_df = compute_debt_schedule(
            solar_net_capex, 
            solar_equity_pct, 
            solar_interest_rate, 
            solar_loan_tenure, 
            solar_plant_life,
            solar_moratorium
        )

        st.dataframe(solar_debt_df, use_container_width=True, hide_index=True)        
        st.subheader("Working Capital")
        solar_om_months = get_param_value(inputs_df, "Working Capital - O & M (months)", "Solar", 1)
        # Calculate solar debt schedule first for proper working capital calculation
        solar_moratorium = get_param_value(inputs_df, "Moratorium (years)", "Solar", 1)
        solar_debt_df = compute_debt_schedule(
            solar_net_capex, 
            solar_equity_pct, 
            solar_interest_rate, 
            solar_loan_tenure, 
            solar_plant_life, 
            solar_moratorium
        )

        # # Calculate solar asset depreciation
        # solar_n1_years = get_param_value(inputs_df, "n1 years", "Solar", 13)
        # solar_asset_df = compute_asset_depreciation(
        #     solar_net_capex, 
        #     solar_dep_rate, 
        #     plant_life, 
        #     solar_n1_years
        # )

        # Calculate working capital with proper parameters for each year
        solar_wc_data = []
        solar_equity = solar_net_capex * solar_equity_pct
        solar_roe = get_param_value(inputs_df, "Return on Equity (%)", "Solar", 16) / 100
        solar_onm_growth = get_param_value(inputs_df, "Annual increase in Operation and Maintenance expenses (%)", "Solar", 5.72) / 100
        solar_insurance_pct = get_param_value(inputs_df, "Insurance(%) of depreciated asset value)", "Solar", 0.35) / 100

        # Get depreciation values from LCOE breakdown
        solar_lcoe_breakdown = st.session_state.get("lcoe_breakdown", pd.DataFrame())
        solar_breakdown_data = solar_lcoe_breakdown[solar_lcoe_breakdown["Technology"] == "Solar"] if not solar_lcoe_breakdown.empty else pd.DataFrame()

        for year in range(1, solar_plant_life + 1):
            # Use values from LCOE breakdown if available, otherwise calculate
            if not solar_breakdown_data.empty and len(solar_breakdown_data) >= year:
                onm_cost = solar_breakdown_data.iloc[year-1]["Operation and Maintenance Expenses"]
                insurance_cost = solar_breakdown_data.iloc[year-1]["Insurance"]
                depreciation_net = solar_breakdown_data.iloc[year-1]["Depreciation (on net capital cost)"]
                interest_payment = solar_breakdown_data.iloc[year-1]["Interest on Term Loan"]
                roe_cost = solar_breakdown_data.iloc[year-1]["Return on Equity"]
            else:
                # Fallback calculations if breakdown data not available
                onm_cost = solar_capex * solar_o_and_m_pct * ((1 + solar_onm_growth) ** (year - 1))
                insurance_cost = solar_capex * solar_insurance_pct
                solar_n1_years = get_param_value(inputs_df, "n1 years", "Solar", 13)
                solar_dep_cap_pct = get_param_value(inputs_df, "Percentage of capital cost on which depreciation applies (%)", "Solar", 95) / 100
                dep_first_nyear_net = solar_net_capex * solar_dep_cap_pct * solar_dep_rate
                if solar_n1_years < solar_plant_life:
                    dep_after_n1years_net = (solar_net_capex * solar_dep_cap_pct - dep_first_nyear_net * solar_n1_years) / (solar_plant_life - solar_n1_years)
                else:
                    dep_after_n1years_net = 0
                depreciation_net = dep_first_nyear_net if year <= solar_n1_years else dep_after_n1years_net
                interest_payment = solar_debt_df.iloc[year-1]['Interest']
                roe_cost = solar_equity * solar_roe
            
            om_wcap = onm_cost / (12 / solar_om_months) if solar_om_months > 0 else 0
            interest_on_om_wcap = om_wcap * solar_wc_interest_rate
            
            if solar_receivable_months > 0:
                # This is the key fix - use the actual values from LCOE breakdown
                total_expenses = onm_cost + insurance_cost + depreciation_net + interest_payment + roe_cost + interest_on_om_wcap
                receivables_wcap = total_expenses / (12 / solar_receivable_months)
            else:
                receivables_wcap = 0
            interest_on_receivables_wcap = receivables_wcap * solar_wc_interest_rate
            total_working_capital = om_wcap + receivables_wcap
            total_interest_on_wc = interest_on_om_wcap + interest_on_receivables_wcap
            
            solar_wc_data.append({
                'Year': year,
                'Operation and Maintenance wcap': round(om_wcap, 2),
                'Interest on working capital - O&M': round(interest_on_om_wcap, 2),
                'Receivables wcap': round(receivables_wcap, 2),
                'Interest on receivables wcap': round(interest_on_receivables_wcap, 2),
                'Total Working Capital': round(total_working_capital, 2),
                'Interest on working capital': round(total_interest_on_wc, 2)
            })

        solar_wc_df = pd.DataFrame(solar_wc_data)
        st.dataframe(solar_wc_df, use_container_width=True, hide_index=True)        
        st.subheader("Asset Value")
        solar_n1_years = get_param_value(inputs_df, "n1 years", "Solar", 13)
        solar_asset_df = compute_asset_depreciation(
            solar_capex,  # Use gross capex instead of net capex
            solar_breakdown_data,  # Pass LCOE breakdown data
            solar_plant_life,
            "Solar"
        )
        st.dataframe(solar_asset_df, use_container_width=True, hide_index=True)
        
        solar_data = {
            'total_capex': solar_capex,
            'subsidy': solar_total_subsidy,
            'net_capex': solar_net_capex,
            'equity_pct': solar_equity_pct * 100,
            'loan_tenure': solar_loan_tenure,
            'interest_rate': solar_interest_rate * 100,
            'debt_df': solar_debt_df,
            'wc_df': solar_wc_df,
            'asset_df': solar_asset_df
        }

    with wind_fin_tab:
        st.header("Wind Financial Analysis")
        
        # Get Wind parameters
        wind_cap_cost = get_param_value(inputs_df, "System Capital Cost (Per KW)", "Wind", 52500)
        wind_size = get_param_value(inputs_df, "Plant Size (KW)", "Wind", 1000)
        wind_subsidy = get_param_value(inputs_df, "Capital Subsidy (Per KW)", "Wind", 0)
        wind_capex = wind_cap_cost * wind_size
        wind_total_subsidy = wind_subsidy * wind_size
        wind_net_capex = wind_capex - wind_total_subsidy
        wind_equity_pct = get_param_value(inputs_df, "Equity (%)", "Wind", 30) / 100
        wind_loan_tenure = int(get_param_value(inputs_df, "Loan Tenure (years)", "Wind", 10))
        wind_interest_rate = get_param_value(inputs_df, "Interest on Loan (%)", "Wind", 10.55) / 100
        wind_moratorium = get_param_value(inputs_df, "Moratorium (years)", "Wind", 1)
        wind_o_and_m_pct = get_param_value(inputs_df, "Operation and Maintenance Expenses in year 1 (%)", "Wind", 0.968) / 100
        wind_receivable_months = get_param_value(inputs_df, "Working Capital - Receivables (months)", "Wind", 2)
        wind_om_months = get_param_value(inputs_df, "Working Capital - O & M (months)", "Wind", 1)
        wind_wc_interest_rate = get_param_value(inputs_df, "Interest on Working Capital (%)", "Wind", 11.55) / 100
        wind_dep_rate = get_param_value(inputs_df, "Depreciation rate for the first n1 years (%)", "Wind", 3.60) / 100
        wind_roe = get_param_value(inputs_df, "Return on Equity (%)", "Wind", 17.60) / 100
        wind_onm_growth = get_param_value(inputs_df, "Annual increase in Operation and Maintenance expenses (%)", "Wind", 5.72) / 100
        wind_insurance_pct = get_param_value(inputs_df, "Insurance(%) of depreciated asset value)", "Wind", 0.64) / 100
        wind_n1_years = get_param_value(inputs_df, "n1 years", "Wind", 25)
        wind_dep_cap_pct = get_param_value(inputs_df, "Percentage of capital cost on which depreciation applies (%)", "Wind", 85) / 100
        
        # Debug information
        st.write(f"Debug - Wind Parameters:")
        st.write(f"Wind Net Capex: {wind_net_capex}")
        st.write(f"Wind Equity %: {wind_equity_pct}")
        st.write(f"Wind Interest Rate: {wind_interest_rate}")
        st.write(f"Wind Loan Tenure: {wind_loan_tenure}")
        st.write(f"Plant Life: {wind_plant_life}")
        st.write(f"Wind Moratorium: {wind_moratorium}")
        
        st.subheader("Debt Schedule")
        # Compute Wind debt schedule
        try:
            wind_debt_df = compute_debt_schedule(
                wind_net_capex, 
                wind_equity_pct, 
                wind_interest_rate, 
                wind_loan_tenure, 
                wind_plant_life,
                wind_moratorium
            )
            st.write(f"Wind Debt DataFrame shape: {wind_debt_df.shape}")
            st.dataframe(wind_debt_df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error computing wind debt schedule: {str(e)}")
            wind_debt_df = pd.DataFrame()  # Create empty DataFrame as fallback
        
        st.subheader("Working Capital")
        wind_wc_data = []
        wind_equity = wind_net_capex * wind_equity_pct

        # Get wind LCOE breakdown data
        wind_lcoe_breakdown = st.session_state.get("lcoe_breakdown", pd.DataFrame())
        wind_breakdown_data = wind_lcoe_breakdown[wind_lcoe_breakdown["Technology"] == "Wind"] if not wind_lcoe_breakdown.empty else pd.DataFrame()
        
        # Calculate depreciation parameters for Wind
        dep_first_nyear_net_wind = wind_net_capex * wind_dep_cap_pct * wind_dep_rate
        if wind_n1_years < wind_plant_life:
            dep_after_n1years_net_wind = (wind_net_capex * wind_dep_cap_pct - dep_first_nyear_net_wind * wind_n1_years) / (wind_plant_life - wind_n1_years)
        else:
            dep_after_n1years_net_wind = 0

        # Calculate working capital for each year
        for year in range(1, wind_plant_life + 1):
            try:
                # Get values from breakdown data if available, otherwise calculate
                if not wind_breakdown_data.empty and len(wind_breakdown_data) >= year:
                    year_row = wind_breakdown_data[wind_breakdown_data['Year'] == year]
                    if not year_row.empty:
                        onm_cost = year_row.iloc[0]["Operation and Maintenance Expenses"]
                        insurance_cost = year_row.iloc[0]["Insurance"]
                        depreciation_net = year_row.iloc[0]["Depreciation (on net capital cost)"]
                        interest_payment = year_row.iloc[0]["Interest on Term Loan"]
                        roe_cost = year_row.iloc[0]["Return on Equity"]
                    else:
                        # Fallback calculation
                        onm_cost = wind_capex * wind_o_and_m_pct * ((1 + wind_onm_growth) ** (year - 1))
                        insurance_cost = wind_capex * wind_insurance_pct
                        depreciation_net = dep_first_nyear_net_wind if year <= wind_n1_years else dep_after_n1years_net_wind
                        interest_payment = wind_debt_df.iloc[year-1]['Interest'] if not wind_debt_df.empty else 0
                        roe_cost = wind_equity * wind_roe
                else:
                    # Calculate from scratch
                    onm_cost = wind_capex * wind_o_and_m_pct * ((1 + wind_onm_growth) ** (year - 1))
                    insurance_cost = wind_capex * wind_insurance_pct
                    depreciation_net = dep_first_nyear_net_wind if year <= wind_n1_years else dep_after_n1years_net_wind
                    interest_payment = wind_debt_df.iloc[year-1]['Interest'] if not wind_debt_df.empty and len(wind_debt_df) >= year else 0
                    roe_cost = wind_equity * wind_roe
                
                # Calculate working capital components
                om_wcap = onm_cost / (12 / wind_om_months) if wind_om_months > 0 else 0
                interest_on_om_wcap = om_wcap * wind_wc_interest_rate
                
                if wind_receivable_months > 0:
                    total_expenses = onm_cost + insurance_cost + depreciation_net + interest_payment + roe_cost + interest_on_om_wcap
                    receivables_wcap = total_expenses / (12 / wind_receivable_months)
                else:
                    receivables_wcap = 0
                    
                interest_on_receivables_wcap = receivables_wcap * wind_wc_interest_rate
                total_working_capital = om_wcap + receivables_wcap
                total_interest_on_wc = interest_on_om_wcap + interest_on_receivables_wcap
                
                wind_wc_data.append({
                    'Year': year,
                    'Operation and Maintenance wcap': round(om_wcap, 2),
                    'Interest on working capital - O&M': round(interest_on_om_wcap, 2),
                    'Receivables wcap': round(receivables_wcap, 2),
                    'Interest on receivables wcap': round(interest_on_receivables_wcap, 2),
                    'Total Working Capital': round(total_working_capital, 2),
                    'Interest on working capital': round(total_interest_on_wc, 2)
                })
                
            except Exception as e:
                st.error(f"Error calculating working capital for year {year}: {str(e)}")
                # Add empty row to maintain structure
                wind_wc_data.append({
                    'Year': year,
                    'Operation and Maintenance wcap': 0,
                    'Interest on working capital - O&M': 0,
                    'Receivables wcap': 0,
                    'Interest on receivables wcap': 0,
                    'Total Working Capital': 0,
                    'Interest on working capital': 0
                })

        wind_wc_df = pd.DataFrame(wind_wc_data)
        st.write(f"Wind Working Capital DataFrame shape: {wind_wc_df.shape}")
        st.dataframe(wind_wc_df, use_container_width=True, hide_index=True)
        
        st.subheader("Asset Value")
        try:
            wind_asset_df = compute_asset_depreciation(
                wind_capex,
                wind_breakdown_data,
                wind_plant_life,
                "Wind"
            )
            st.write(f"Wind Asset DataFrame shape: {wind_asset_df.shape}")
            st.dataframe(wind_asset_df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error computing wind asset depreciation: {str(e)}")
            wind_asset_df = pd.DataFrame()
        
        # Store wind data for potential use elsewhere
        wind_data = {
            'total_capex': wind_capex,
            'subsidy': wind_total_subsidy,
            'net_capex': wind_net_capex,
            'equity_pct': wind_equity_pct * 100,
            'loan_tenure': wind_loan_tenure,
            'interest_rate': wind_interest_rate * 100,
            'debt_df': wind_debt_df,
            'wc_df': wind_wc_df,
            'asset_df': wind_asset_df
        }

    if solar_data and wind_data:
        fin_key = f"fin_data_saved_{project_id}_{run_number}"
        if fin_key not in st.session_state or not st.session_state[fin_key]:
            with st.spinner("Saving financial data to database..."):
                success, message = save_financial_data_to_db(project_id, run_number, solar_data, wind_data)
                if success:
                    st.success("Financial data saved to database successfully")
                    st.session_state[fin_key] = True
                else:
                    st.error(f"Error saving financial data: {message}")
    else:
        st.warning("Complete financial data not available. Cannot save to database.")

with ai_validation_tab:
    st.subheader("AI Business Interpretation")
    
    if check_ai_clicked and "ai_interpretation_response" not in st.session_state:
        st.info("AI interpretation in progress...")
    
    if "ai_interpretation_response" in st.session_state:
        ai_response = st.session_state["ai_interpretation_response"]
        
        # Display current LCOE results for context
        if "lcoe_result" in st.session_state:
            st.subheader("Your LCOE Results")
            col1, col2 = st.columns(2)
            lcoe_df = st.session_state["lcoe_result"]
            
            for _, row in lcoe_df.iterrows():
                if row["Technology"] == "Solar":
                    with col1:
                        st.metric("Solar LCOE", f"{row['LCOE (INR/kWh)']} INR/kWh")
                elif row["Technology"] == "Wind":
                    with col2:
                        st.metric("Wind LCOE", f"{row['LCOE (INR/kWh)']} INR/kWh")
        
        st.divider()
        st.subheader("AI Analysis")
        st.markdown(ai_response)
        
        # Download report
        report_content = f"""# LCOE Business Interpretation Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Project Details
- Project ID: {project_id}
- Run Number: {run_number}

## Calculated LCOE Results
"""
        if "lcoe_result" in st.session_state:
            for _, row in st.session_state["lcoe_result"].iterrows():
                report_content += f"- {row['Technology']}: {row['LCOE (INR/kWh)']} INR/kWh\n"
        
        report_content += f"\n## AI Analysis\n{ai_response}"
        
        st.download_button(
            label="Download Analysis Report",
            data=report_content,
            file_name=f"LCOE_Business_Analysis_{project_id}_{run_number}.txt",
            mime="text/plain"
        )
    else:
        st.info("Click 'Check Results with AI' button to get business interpretation of your LCOE results.")
        st.markdown("""
        **What you'll get:**
        - LCOE competitiveness analysis
        - Technology comparison insights  
        - Key performance drivers
        - Business risk assessment
        - Market viability analysis
        - Strategic recommendations
        """)