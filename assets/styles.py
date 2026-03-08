"""
Custom CSS styles for the Streamlit application.
"""

MAIN_CSS = """
<style>
/* Main container styling */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* Header styling */
.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
}

/* Metric containers */
.metric-container {
    background-color: #f8f9fa;
    padding: 1.5rem;
    border-radius: 0.75rem;
    border-left: 4px solid #1f77b4;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
}

/* P&L styling */
.positive {
    color: #28a745;
    font-weight: bold;
}

.negative {
    color: #dc3545;
    font-weight: bold;
}

/* Mode indicators */
.test-mode {
    background: linear-gradient(90deg, #fff3cd, #ffeaa7);
    border: 1px solid #ffeaa7;
    border-radius: 0.75rem;
    padding: 1rem;
    margin: 1rem 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.live-mode {
    background: linear-gradient(90deg, #d1ecf1, #bee5eb);
    border: 1px solid #bee5eb;
    border-radius: 0.75rem;
    padding: 1rem;
    margin: 1rem 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Trade action styling */
.trade-action-buy {
    background-color: #d4edda;
    padding: 0.4rem 0.8rem;
    border-radius: 0.5rem;
    color: #155724;
    font-weight: bold;
    display: inline-block;
    border: 1px solid #c3e6cb;
}

.trade-action-sell {
    background-color: #f8d7da;
    padding: 0.4rem 0.8rem;
    border-radius: 0.5rem;
    color: #721c24;
    font-weight: bold;
    display: inline-block;
    border: 1px solid #f5c6cb;
}

/* Button styling */
.stButton > button {
    border-radius: 0.5rem;
    border: none;
    padding: 0.75rem 1.5rem;
    font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

/* Table styling */
.dataframe {
    border-radius: 0.5rem;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Sidebar styling */
.css-1d391kg {
    background-color: #f8f9fa;
}

/* Chart container */
.plotly-container {
    border-radius: 0.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    overflow: hidden;
}

/* Success/Error message styling */
.stSuccess {
    border-radius: 0.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stError {
    border-radius: 0.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stWarning {
    border-radius: 0.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stInfo {
    border-radius: 0.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Progress bar styling */
.stProgress > div > div > div {
    background-color: #1f77b4;
}

/* Input field styling */
.stTextInput > div > div > input {
    border-radius: 0.5rem;
    border: 2px solid #e0e0e0;
    transition: border-color 0.3s ease;
}

.stTextInput > div > div > input:focus {
    border-color: #1f77b4;
    box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2);
}

/* Number input styling */
.stNumberInput > div > div > input {
    border-radius: 0.5rem;
    border: 2px solid #e0e0e0;
    transition: border-color 0.3s ease;
}

.stNumberInput > div > div > input:focus {
    border-color: #1f77b4;
    box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2);
}

/* Checkbox styling */
.stCheckbox > label {
    font-weight: 500;
}

/* Custom divider */
.custom-divider {
    border: none;
    height: 2px;
    background: linear-gradient(90deg, transparent, #1f77b4, transparent);
    margin: 2rem 0;
}

/* Responsive design */
@media (max-width: 768px) {
    .main-header {
        font-size: 2rem;
    }
    
    .metric-container {
        padding: 1rem;
    }
    
    .stButton > button {
        width: 100%;
        margin-bottom: 0.5rem;
    }
}

/* Loading spinner customization */
.stSpinner {
    color: #1f77b4;
}

/* Tooltip styling */
.tooltip {
    background-color: #333;
    color: white;
    padding: 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.875rem;
}
</style>
"""

DARK_MODE_CSS = """
<style>
/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
    .metric-container {
        background-color: #2d3748;
        color: #e2e8f0;
    }
    
    .test-mode {
        background: linear-gradient(90deg, #744210, #975a16);
        color: #fef5e7;
    }
    
    .live-mode {
        background: linear-gradient(90deg, #2c5aa0, #2b6cb0);
        color: #ebf8ff;
    }
}
</style>
"""
