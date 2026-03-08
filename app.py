"""
Portfolio Rebalancing Tool

A professional Streamlit application for portfolio rebalancing using the Public.com API.
"""

import sys
import os

# Ensure the project root is on sys.path so absolute imports inside src/ work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from src.ui.main_app import StreamlitUI
from src.utils.logger import setup_logger

# Configure page
st.set_page_config(
    page_title="Portfolio Rebalancing Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application entry point."""
    # Set up logging
    logger = setup_logger()
    
    try:
        # Initialize and run the Streamlit UI
        app = StreamlitUI()
        app.run()
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"An error occurred: {e}")
        st.error("Please check your API key and try again.")

if __name__ == "__main__":
    main()
