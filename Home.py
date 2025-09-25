import streamlit as st
st.set_page_config(
    page_title="Capacity Planning for Renewable Energy",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Add Full Width Image at the top ---
st.image("images/banner3.jpg", use_container_width=True)

st.title("Capacity Planning for Renewable Energy")

st.markdown("""
Welcome! Please use the sidebar to navigate through pages.

This tool helps energy planners assess, configure, and optimize hybrid renewable energy projects through detailed capacity planning and financial evaluation.
""")

st.subheader("Instructions:")
st.markdown("""
1. Navigate to **Project Summary** to review existing projects or create new ones.

2. To configure a new project, go to **Project Configuration**. Note that only projects that are confirmed will appear on subsequent pages to perform other operations.

3. Go to **Site Load** to upload wind, solar, battery, and demand profiles.

4. Go to **Configure Optimize** to set up, calculate CUF and Optimized Plant Size values and run technical and financial analyses.

5. View the LCOE and financial details on the **LCOE Outputs** page.

6. Go to **LCOS** to enter inputs and view LCOS details.
""")
