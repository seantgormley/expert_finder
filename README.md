# Expert Finder

A Streamlit application that helps users find industry experts based on company searches. The application allows users to ask questions like "I'm trying to get smart on [company name]" and produces a table of former executives at the company ranked by tenure, as well as former executives who work at competitors.

## Features

- Search for experts by company name
- View ranked list of former executives based on tenure and relevance
- Discover experts from competitor companies
- Export results to CSV
- Intelligent company name extraction from queries
- Robust error handling for API calls

## API Integrations

This application integrates with:
- **Proxycurl API**: For LinkedIn data including company information, competitor searches, and people profiles

## Requirements

- Python 3.8+
- Streamlit
- Pandas
- Requests
- Python-dotenv (for environment variable management)
- urllib3 (for retry functionality)

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up your API key:
   - Create a `.env` file in the root directory
   - Add your API key:
     ```
     PROXYCURL_API_KEY=your_proxycurl_api_key
     ```
   - Alternatively, you can set this as an environment variable

## Usage

### Proxycurl Version (Recommended)
Run the Proxycurl-integrated Streamlit application:
```
streamlit run streamlit_app_proxycurl.py
```

### Legacy Versions
The original versions using Crunchbase and People Data Labs APIs are still available:
```
streamlit run streamlit_app.py
streamlit run streamlit_app_improved.py
```

Then open your browser and navigate to the URL shown in the terminal (typically http://localhost:8501).

## Project Structure

- `expert_finder.py`: Original core functionality using Crunchbase and People Data Labs APIs
- `expert_finder_improved.py`: Improved version with better error handling using original APIs
- `expert_finder_proxycurl.py`: New implementation using Proxycurl API for LinkedIn data
- `streamlit_app.py`: Basic Streamlit UI for the application
- `streamlit_app_improved.py`: Improved Streamlit UI with better error handling
- `streamlit_app_proxycurl.py`: Streamlit UI for the Proxycurl API integration
- `test_proxycurl.py`: Test script for the Proxycurl API integration
- `requirements.txt`: Python dependencies
- `.env`: API keys (not tracked in git)
- `.env.example`: Example environment file with placeholder API keys

## Improvements in the Proxycurl Version

The Proxycurl version includes:
1. **LinkedIn Data Integration**: Uses Proxycurl API to access LinkedIn data for companies and people
2. **Robust Error Handling**: Comprehensive error handling for API calls with proper exception handling
3. **Intelligent Company Name Extraction**: Smarter extraction of company names from user queries
4. **Fallback Mechanisms**: Generates sample data when API calls fail or limits are reached
5. **Retry Mechanism**: Automatic retries for failed API calls with exponential backoff
6. **Comprehensive Logging**: Detailed logging for better debugging and monitoring
7. **Enhanced UI**: Improved visualizations and API key status indicators
8. **Test Mode**: Special test mode for reliable testing without making actual API calls
