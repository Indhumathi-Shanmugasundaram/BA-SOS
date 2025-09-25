from pulp import LpProblem, LpVariable, LpMinimize, lpSum
import pandas as pd
import numpy as np

def optimize_generation_capacity(demand_df, solar_cuf, wind_cuf, solar_cost_factor=0.9):
    """
    Solves LP for minimum required solar/wind capacity to meet hourly demand
    with balanced generation and cost optimization

    Parameters:
    - demand_df: DataFrame with 'Hour' and 'Demand' columns
    - solar_cuf, wind_cuf: Capacity Utilization Factor (as decimal, e.g., 0.18)
    - solar_cost_factor: Cost preference factor for solar (default 0.9 makes solar preferred)

    Returns:
    - solar_capacity (MW)
    - wind_capacity (MW)
    - demand_df with estimated generation columns
    """
    avg_demand = demand_df['Demand'].mean()
    demand_threshold_low = avg_demand * 0.6  # 40% below average
    demand_threshold_high = avg_demand * 1.4  # 40% above average
    
    filtered_demand = demand_df[
        (demand_df['Demand'] >= demand_threshold_low) & 
        (demand_df['Demand'] <= demand_threshold_high)
    ].copy()
    
    if len(filtered_demand) == 0:
        filtered_demand = demand_df.copy()
        avg_demand = filtered_demand['Demand'].mean()
    
    total_hours = len(filtered_demand)
    
    prob = LpProblem("Generation_Capacity_Optimization", LpMinimize)
    solar_capacity = LpVariable("Solar_Capacity", lowBound=0)
    wind_capacity = LpVariable("Wind_Capacity", lowBound=0)
    
    prob += solar_capacity+ wind_capacity
    
    for i in filtered_demand.index:
        prob += (solar_capacity * solar_cuf + wind_capacity * wind_cuf >= 
                filtered_demand.loc[i, "Demand"]), f"Demand_Hour_{i}"
    
    if solar_cuf > 0 and wind_cuf > 0:
        if solar_cuf >= wind_cuf: 
            prob += solar_capacity * solar_cuf >= avg_demand * 0.8, "Solar_Min_Contribution"
            prob += wind_capacity * wind_cuf >= avg_demand * 0.2, "Wind_Min_Contribution"
        else:
            prob += wind_capacity * wind_cuf >= avg_demand * 0.8, "Wind_Min_Contribution"
            prob += solar_capacity * solar_cuf >= avg_demand * 0.2, "Solar_Min_Contribution"
    elif solar_cuf > 0 and wind_cuf == 0:
        prob += solar_capacity * solar_cuf >= avg_demand, "Solar_Only_Contribution"
    elif wind_cuf > 0 and solar_cuf == 0:
        prob += wind_capacity * wind_cuf >= avg_demand, "Wind_Only_Contribution"
    
    max_generation_factor = 1.3
    max_allowed_generation = avg_demand * max_generation_factor
    prob += (solar_capacity * solar_cuf + wind_capacity * wind_cuf <= 
            max_allowed_generation), "Max_Generation_Limit"
    
    if solar_cuf > 0 and wind_cuf > 0 and abs(solar_cuf - wind_cuf) < 0.01:
        prob += solar_capacity * solar_cuf >= wind_capacity * wind_cuf, "Solar_Preference"
    
    prob.solve()
    
    solar_val = solar_capacity.varValue if solar_capacity.varValue else 0
    wind_val = wind_capacity.varValue if wind_capacity.varValue else 0
    
    demand_df_result = demand_df.copy()
    demand_df_result["Solar_Generation"] = solar_val * solar_cuf
    demand_df_result["Wind_Generation"] = wind_val * wind_cuf
    demand_df_result["Total_Generation"] = (demand_df_result["Solar_Generation"] + 
                                           demand_df_result["Wind_Generation"])
    return solar_val, wind_val, demand_df_result 