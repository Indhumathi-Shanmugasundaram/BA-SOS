import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.gemini_config import get_gemini_response, configure_gemini
import pandas as pd
import json
import time

def create_lcoe_interpretation_prompt(inputs_df, lcoe_results, capital_metrics, project_info=None):
    """Create prompt for LCOE business interpretation"""
    
    # Extract key parameters for context
    solar_params = {}
    wind_params = {}
    
    key_params = [
        "Plant Size (KW)",
        "Project Life of Plant (Years)", 
        "Capacity Utilization Factor (%)",
        "System Capital Cost (Per KW)",
        "Operation and Maintenance Expenses in year 1 (%)",
        "Discount Rate (%)",
        "Equity (%)",
        "Return on Equity (%)"
    ]
    
    for param in key_params:
        try:
            solar_row = inputs_df[inputs_df['Parameter'] == param]
            if not solar_row.empty:
                solar_params[param] = solar_row.iloc[0]['Solar']
                wind_params[param] = solar_row.iloc[0]['Wind']
        except:
            continue
    
    # Get project context if available
    site_info = ""
    if project_info:
        site_info = f"""
    **PROJECT CONTEXT:**
    - Site Name: {project_info.get('site_name', 'Not specified')}
    - State: {project_info.get('state', 'Not specified')}
    - Location: {project_info.get('location', 'Not specified')}
        """
    
    prompt = f"""
    You are a renewable energy business analyst. Analyze the following LCOE results and provide business insights.

    {site_info}

    **CALCULATED LCOE RESULTS:**
    - Solar LCOE: {lcoe_results.get('Solar', 'N/A')} INR/kWh
    - Wind LCOE: {lcoe_results.get('Wind', 'N/A')} INR/kWh

    **KEY PROJECT PARAMETERS:**
    
    **Solar Project:**
    {json.dumps(solar_params, indent=2)}
    
    **Wind Project:**
    {json.dumps(wind_params, indent=2)}

    **CAPITAL COST BREAKDOWN:**
    Solar:
    - Gross Capital Cost: {capital_metrics.get('Solar', {}).get('Gross Capital Cost', 'N/A')} INR
    - Net Capital Cost: {capital_metrics.get('Solar', {}).get('Net Capital Cost', 'N/A')} INR
    - Equity: {capital_metrics.get('Solar', {}).get('Equity', 'N/A')} INR
    - Debt: {capital_metrics.get('Solar', {}).get('Debt', 'N/A')} INR

    Wind:
    - Gross Capital Cost: {capital_metrics.get('Wind', {}).get('Gross Capital Cost', 'N/A')} INR
    - Net Capital Cost: {capital_metrics.get('Wind', {}).get('Net Capital Cost', 'N/A')} INR
    - Equity: {capital_metrics.get('Wind', {}).get('Equity', 'N/A')} INR
    - Debt: {capital_metrics.get('Wind', {}).get('Debt', 'N/A')} INR

    Please provide a comprehensive business analysis covering:

    1. **LCOE Competitiveness**: How do these LCOE values compare to market rates in India? Are they competitive?

    2. **Technology Comparison**: Which technology offers better economics for this project and why?

    3. **Key Performance Drivers**: What are the main factors driving the LCOE for each technology?

    4. **Risk Assessment**: What business and financial risks should be considered?

    5. **Market Viability**: Are these projects commercially viable at current power purchase agreement (PPA) rates?

    6. **Recommendations**: What business recommendations would you provide to optimize the project economics?

    Format your response clearly with headings and provide practical, actionable insights.
    """
    
    return prompt

def get_lcoe_interpretation_with_gemini(inputs_df, lcoe_results, capital_metrics, project_info=None, max_retries=2):
    """Get business interpretation of LCOE results from Gemini"""
    
    quota_file = os.path.join(os.path.dirname(__file__), '.quota_check')
    if os.path.exists(quota_file):
        with open(quota_file, 'r') as f:
            last_check = float(f.read().strip())
            if time.time() - last_check < 3600:
                return False, "Skipping Gemini interpretation - quota check active"
    
    try:
        model = configure_gemini()
        prompt = create_lcoe_interpretation_prompt(inputs_df, lcoe_results, capital_metrics, project_info)
        
        print("Getting LCOE business interpretation from Gemini...")
        response = get_gemini_response(prompt, model, max_retries=max_retries)
        
        if os.path.exists(quota_file):
            os.remove(quota_file)
        
        return True, response
        
    except Exception as e:
        error_str = str(e)
        print(f"Gemini interpretation error: {error_str}")
        
        if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
            with open(quota_file, 'w') as f:
                f.write(str(time.time()))
            return False, "API quota exceeded - please try again later"
        
        elif "404" in error_str or "not found" in error_str:
            return False, "Gemini model not available"
        
        elif "permission" in error_str.lower() or "forbidden" in error_str.lower():
            return False, "Please verify your API key and permissions"
        
        else:
            return False, f"Interpretation failed: {error_str}"

def validate_and_compare_lcoe(inputs_df, my_calculated_lcoe, gemini_lcoe, gemini_response):
    """Compare your LCOE with AI's calculated LCOE"""
    
    comparison_text = f"""
Your Calculations:
- Solar LCOE: {my_calculated_lcoe.get('Solar', 'N/A')} INR/kWh
- Wind LCOE: {my_calculated_lcoe.get('Wind', 'N/A')} INR/kWh

AI Calculations:
- Solar LCOE: {gemini_lcoe.get('Solar', 'N/A')} INR/kWh
- Wind LCOE: {gemini_lcoe.get('Wind', 'N/A')} INR/kWh

Differences:"""
    
    if 'Solar' in my_calculated_lcoe and 'Solar' in gemini_lcoe:
        diff_solar = abs(my_calculated_lcoe['Solar'] - gemini_lcoe['Solar'])
        diff_pct_solar = (diff_solar / gemini_lcoe['Solar']) * 100
        comparison_text += f"\n- Solar: {diff_solar:.2f} INR/kWh ({diff_pct_solar:.1f}% difference)"
    if 'Wind' in my_calculated_lcoe and 'Wind' in gemini_lcoe:
        diff_wind = abs(my_calculated_lcoe['Wind'] - gemini_lcoe['Wind'])
        diff_pct_wind = (diff_wind / gemini_lcoe['Wind']) * 100
        comparison_text += f"\n- Wind: {diff_wind:.2f} INR/kWh ({diff_pct_wind:.1f}% difference)"
    
    comparison_text += f"\n\n**AI'S DETAILED ANALYSIS:**\n{gemini_response}"
    
    return comparison_text

def parse_gemini_lcoe_response(response_text):
    """Parse Gemini response to extract key insights"""
    sections = {
        "validation": "",
        "gemini_calculation": "",
        "comparison": "",
        "analysis": "",
        "recommendations": ""
    }
    
    try:
        # Simple parsing based on headers
        current_section = None
        lines = response_text.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            if 'validation' in line_lower or 'reasonable' in line_lower:
                current_section = "validation"
            elif 'calculation' in line_lower and ('**' in line or '#' in line):
                current_section = "gemini_calculation"
            elif 'comparison' in line_lower or 'cost-effective' in line_lower:
                current_section = "comparison"
            elif 'analysis' in line_lower and ('**' in line or '#' in line):
                current_section = "analysis"
            elif 'recommendation' in line_lower:
                current_section = "recommendations"
            elif current_section and line.strip():
                sections[current_section] += line + "\n"
    
    except Exception as e:
        # If parsing fails, return the full response
        sections["validation"] = response_text
    
    return sections