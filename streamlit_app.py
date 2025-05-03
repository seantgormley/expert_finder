"""
streamlit_app.py
Streamlit UI for the Expert Finder application.
"""

import streamlit as st
import pandas as pd
from expert_finder import find_and_rank

st.set_page_config(
    page_title="Expert Finder",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Expert Finder")
st.markdown("""
This application helps you find industry experts based on company searches. 
Enter a query like "I'm trying to get smart on [company name]" and the app will produce:
- A table of former executives at the company ranked by tenure
- Former executives who work at competitors
""")

with st.form("search_form"):
    query = st.text_input(
        "Enter your query:",
        placeholder="I'm trying to get smart on [company name]",
        help="Example: 'I'm trying to get smart on Aquasana'"
    )
    
    top_n = st.slider(
        "Number of results to show:",
        min_value=5,
        max_value=50,
        value=25,
        step=5
    )
    
    submitted = st.form_submit_button("Find Experts")

if submitted and query:
    with st.spinner("Searching for experts..."):
        try:
            results_df = find_and_rank(query, top_n=top_n)
            
            if not results_df.empty:
                st.subheader("Top Experts")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.dataframe(
                        results_df.drop(columns=["score"]),
                        use_container_width=True,
                        hide_index=True
                    )
                
                with col2:
                    company_name = query.split()[-1]
                    
                    company_counts = results_df["company"].value_counts()
                    
                    st.subheader("Companies Represented")
                    st.bar_chart(company_counts)
                
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="Download results as CSV",
                    data=csv,
                    file_name=f"{company_name}_experts.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No experts found. Try a different company name.")
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.info("Make sure your API keys are set correctly in the .env file or as environment variables.")

with st.sidebar:
    st.subheader("About")
    st.markdown("""
    This application uses:
    - **Crunchbase API**: For company information and competitor searches
    - **People Data Labs API**: For people information and work history
    
    The experts are ranked based on:
    - Title importance (CEO, Founder > VP > Director > Manager)
    - Years of experience
    - Whether they worked at the target company
    - Mentions of the target company in their job summary
    """)
    
    st.subheader("API Keys")
    st.markdown("""
    To use this application, you need to set up API keys for:
    1. Crunchbase
    2. People Data Labs
    
    Create a `.env` file with:
    ```
    CB_KEY=your_crunchbase_api_key
    PDL_KEY=your_people_data_labs_api_key
    ```
    """)
