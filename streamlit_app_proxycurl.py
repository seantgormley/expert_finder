"""
streamlit_app_proxycurl.py
Streamlit UI for the Expert Finder application using Proxycurl API.
"""

import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from expert_finder_proxycurl import find_and_rank, extract_company_name, check_api_keys

load_dotenv()

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
    company_name = extract_company_name(query)
    
    with st.spinner(f"Searching for experts related to {company_name}..."):
        try:
            check_api_keys()
            
            results_df = find_and_rank(query, top_n=top_n)
            
            if not results_df.empty:
                st.subheader(f"Top Experts for {company_name}")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.dataframe(
                        results_df.drop(columns=["score"]),
                        use_container_width=True,
                        hide_index=True
                    )
                
                with col2:
                    company_counts = results_df["company"].value_counts()
                    
                    st.subheader("Companies Represented")
                    st.bar_chart(company_counts)
                    
                    st.subheader("Title Distribution")
                    title_counts = results_df["title"].apply(
                        lambda x: x.split()[0].lower() if x and " " in x else "other"
                    ).value_counts().head(5)
                    st.bar_chart(title_counts)
                
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="Download results as CSV",
                    data=csv,
                    file_name=f"{company_name.replace(' ', '_')}_experts.csv",
                    mime="text/csv"
                )
            else:
                st.warning(f"No experts found for {company_name}. Try a different company name.")
        
        except ValueError as e:
            st.error(f"API Key Error: {str(e)}")
            st.info("Please set up your Proxycurl API key in the .env file or as environment variable.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.info("If this error persists, please check your API key and internet connection.")

with st.sidebar:
    st.subheader("About")
    st.markdown("""
    This application uses:
    - **Proxycurl API**: For LinkedIn data including company information, 
      competitor searches, and people profiles
    
    The experts are ranked based on:
    - Title importance (CEO, Founder > VP > Director > Manager)
    - Years of experience
    - Whether they worked at the target company
    - Mentions of the target company in their profile
    """)
    
    st.subheader("API Key")
    st.markdown("""
    To use this application, you need to set up an API key for:
    - Proxycurl
    
    Create a `.env` file with:
    ```
    PROXYCURL_API_KEY=your_proxycurl_api_key
    ```
    """)
    
    st.subheader("API Key Status")
    
    proxycurl_key = os.getenv("PROXYCURL_API_KEY")
    
    if proxycurl_key and proxycurl_key != "your_proxycurl_api_key":
        st.success("✅ Proxycurl API Key: Set")
    else:
        st.error("❌ Proxycurl API Key: Not set")
