import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pdfkit
import base64
import io
import os # To check OS for wkhtmltopdf path

# Page config
st.set_page_config(page_title="Horus Hospital KPIs", layout="wide", initial_sidebar_state="expanded")

# Enhanced CSS styling for Streamlit display
st.markdown("""
    <style>
        /* Main container styling */
        .main > div {
            padding-top: 2rem;
        }
        
        /* Header styling */
        .main-header {
            background: linear-gradient(90deg, #1f77b4, #2ca02c);
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            color: white;
            text-align: center;
        }
        
        /* KPI cards styling */
        .kpi-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            color: white;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .kpi-value {
            font-size: 2rem;
            font-weight: bold;
            margin: 0.5rem 0;
        }
        
        /* Table styling - More aggressive overrides */
        .dataframe {
            width: 100%;
            border-collapse: collapse;
        }
        
        /* Universal table alignment - targeting all possible Streamlit table elements */
        table th,
        table td,
        .dataframe th,
        .dataframe td,
        div[data-testid="stDataFrame"] th,
        div[data-testid="stDataFrame"] td,
        div[data-testid="stDataFrame"] table th,
        div[data-testid="stDataFrame"] table td,
        .stDataFrame th,
        .stDataFrame td,
        .stDataFrame table th,
        .stDataFrame table td,
        [data-testid="stDataFrame"] th,
        [data-testid="stDataFrame"] td,
        [data-testid="stDataFrame"] table th,
        [data-testid="stDataFrame"] table td,
        .element-container table th,
        .streamlit-expanderContent table th {
            background-color: #f0f2f6 !important;
            font-weight: bold !important;
            text-align: center !important;
        }
        
        /* Force center alignment on all table content */
        * table * {
            text-align: center !important;
        }
        
        /* Department section styling */
        .department-section {
            border-left: 4px solid #1f77b4;
            padding-left: 1rem;
            margin: 1rem 0;
            background-color: #f8f9fa;
            border-radius: 0 10px 10px 0;
        }
        
        /* Alert styling */
        .alert-info {
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            background-color: #f0f2f6;
        }
    </style>
""", unsafe_allow_html=True)

# Main title with enhanced styling
st.markdown("""
    <div class="main-header">
        <h1>🏥 Horus Hospital KPI Dashboard</h1>
        <p>Comprehensive Healthcare Performance Analytics</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar configuration
st.sidebar.markdown("### 📁 Upload KPI Data")
uploaded_file = st.sidebar.file_uploader(
    "Upload your Excel file (.xlsx)",
    type=["xlsx"],
    help="Upload an Excel file containing your KPI data"
)

# Enhanced sidebar instructions
with st.sidebar.expander("📋 Required Excel Format", expanded=False):
    st.markdown("""
    **Required Columns:**
    - `kpi id` - Unique KPI identifier
    - `kpi name` - KPI description
    - `attribute 1` - Primary grouping attribute
    - `attribute 2` - Secondary grouping attribute
    - `grouping criteria` - 'sum' or 'average'
    - `value` - KPI numeric value
    - `month` - Month name
    - `quarter` - Quarter (Q1, Q2, Q3, Q4)
    - `year` - Year (YYYY)
    - `department` - Department name
    """)

# Constants
MONTH_ORDER = ["January", "February", "March", "April", "May", "June",
               'July', 'August', 'September', 'October', 'November', 'December']
QUARTER_MONTHS = {
    'Q1': ['January', 'February', 'March'],
    'Q2': ['April', 'May', 'June'],
    'Q3': ['July', 'August', 'September'],
    'Q4': ['October', 'November', 'December']
}

def validate_data(df):
    """Validate uploaded data structure"""
    required_columns = ['kpi id', 'kpi name', 'attribute 1', 'attribute 2',
                        'grouping criteria', 'value', 'month', 'quarter', 'year', 'department']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"Missing required columns: {', '.join(missing_columns)}")
        return False
    
    # Check for numeric values
    if not pd.api.types.is_numeric_dtype(df['value']):
        st.error("'value' column must contain numeric data")
        return False
        
    return True

def apply_filters(df, filters):
    """Apply selected filters to dataframe"""
    filtered_df = df.copy()
    
    # Year filter
    if filters['year']:
        filtered_df = filtered_df[filtered_df['year'] == filters['year']]
    
    # Report type specific filters
    if filters['report_type'] == "Monthly" and filters['month']:
        filtered_df = filtered_df[filtered_df['month'] == filters['month']]
    elif filters['report_type'] == "Quarter" and filters['quarter']:
        quarter_months = QUARTER_MONTHS.get(filters['quarter'], [])
        filtered_df = filtered_df[filtered_df['month'].isin(quarter_months)]
    elif filters['report_type'] == "Half Annual" and filters['half']:
        if filters['half'] == "H1":
            filtered_df = filtered_df[filtered_df['month'].isin(MONTH_ORDER[:6])]
        else:
            filtered_df = filtered_df[filtered_df['month'].isin(MONTH_ORDER[6:])]
    
    # Department filter (only applied if 'department' key is present in filters and not "All Departments")
    if filters.get('department') and filters['department'] != "All Departments":
        filtered_df = filtered_df[filtered_df['department'] == filters['department']]

    # KPI Name filter
    # Corrected logic: If "All KPIs" is selected, don't filter by kpi_name at all
    # Otherwise, filter by the selected KPI names
    if filters.get('kpi_name') and "All KPIs" not in filters['kpi_name']:
        if isinstance(filters['kpi_name'], list) and filters['kpi_name']:
            filtered_df = filtered_df[filtered_df['kpi name'].isin(filters['kpi_name'])]
        elif not isinstance(filters['kpi_name'], list) and filters['kpi_name'] is not None:
            filtered_df = filtered_df[filtered_df['kpi name'] == filters['kpi_name']]
    # If "All KPIs" is in filters['kpi_name'], no filtering by kpi_name is done, which is the desired behavior for "All KPIs"

    return filtered_df

def format_value(value, group_type):
    """Format values based on grouping criteria"""
    if pd.isna(value):
        return 0
    # Use 'mean' instead of 'average' here for consistent logic with aggregation functions
    return int(value) if group_type == 'sum' else round(float(value), 1) 

def display_summary_cards_streamlit(df, filters):
    """Displays KPI summary cards in Streamlit columns."""
    filtered_df = apply_filters(df, filters) 
    
    if filtered_df.empty:
        return # Nothing to display
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_kpis = filtered_df['kpi id'].nunique()
    with col1:
        st.markdown(f"""
            <div class="kpi-card">
                <h4>📊 Total KPIs</h4>
                <div class="kpi-value">{total_kpis}</div>
            </div>
        """, unsafe_allow_html=True)
    
    total_departments = filtered_df['department'].nunique()
    with col2:
        st.markdown(f"""
            <div class="kpi-card">
                <h4>🏢 Departments</h4>
                <div class="kpi-value">{total_departments}</div>
            </div>
        """, unsafe_allow_html=True)
    
    avg_value = filtered_df['value'].mean()
    with col3:
        st.markdown(f"""
            <div class="kpi-card">
                <h4>📈 Avg Value</h4>
                <div class="kpi-value">{format_value(avg_value, 'average')}</div>
            </div>
        """, unsafe_allow_html=True)
    
    total_records = len(filtered_df)
    with col4:
        st.markdown(f"""
            <div class="kpi-card">
                <h4>📋 Records</h4>
                <div class="kpi-value">{total_records}</div>
            </div>
        """, unsafe_allow_html=True)

def get_summary_cards_html_for_pdf(df, filters):
    """Generates HTML string for KPI summary cards, suitable for PDF embedding."""
    filtered_df = apply_filters(df, filters)
    
    if filtered_df.empty:
        return ""
    
    summary_html = ""
    
    total_kpis = filtered_df['kpi id'].nunique()
    summary_html += f"""
        <div class="kpi-card">
            <h4>📊 Total KPIs</h4>
            <div class="kpi-value">{total_kpis}</div>
        </div>
    """
    
    total_departments = filtered_df['department'].nunique()
    summary_html += f"""
        <div class="kpi-card">
            <h4>🏢 Departments</h4>
            <div class="kpi-value">{total_departments}</div>
        </div>
    """
    
    avg_value = filtered_df['value'].mean()
    summary_html += f"""
        <div class="kpi-card">
            <h4>📈 Avg Value</h4>
            <div class="kpi-value">{format_value(avg_value, 'average')}</div>
        </div>
    """
    
    total_records = len(filtered_df)
    summary_html += f"""
        <div class="kpi-card">
            <h4>📋 Records</h4>
            <div class="kpi-value">{total_records}</div>
        </div>
    """
    # Wrap in a flex container for PDF layout
    return f"""<div style="display:flex; justify-content:space-around; flex-wrap:wrap; margin-bottom: 2rem;">{summary_html}</div>"""


def create_pivot_table(kpi_df, report_type, group_type):
    """Create pivot table for KPI data"""
    has_attr1 = kpi_df['attribute 1'].notna().any() and kpi_df['attribute 1'].ne("").any()
    has_attr2 = kpi_df['attribute 2'].notna().any() and kpi_df['attribute 2'].ne("").any()
    
    # Use 'mean' for aggregation if group_type is 'average' or 'mean'
    aggfunc = 'sum' if group_type == 'sum' else 'mean' 
    
    if has_attr1 and has_attr2:
        # Two attributes case
        return create_two_attribute_pivot(kpi_df, report_type, aggfunc, group_type)
    elif has_attr1:
        # Single attribute 1 case
        return create_single_attribute_pivot(kpi_df, 'attribute 1', report_type, aggfunc, group_type)
    elif has_attr2:
        # Single attribute 2 case
        return create_single_attribute_pivot(kpi_df, 'attribute 2', report_type, aggfunc, group_type)
    else:
        # No attributes case
        return create_no_attribute_pivot(kpi_df, report_type, aggfunc, group_type)

def create_two_attribute_pivot(kpi_df, report_type, aggfunc, group_type):
    """Handle two attribute pivot tables"""
    results = []
    
    for attr1 in sorted(kpi_df['attribute 1'].dropna().unique()):
        sub_df = kpi_df[kpi_df['attribute 1'] == attr1]
        
        if report_type != "Monthly":
            pivot = pd.pivot_table(
                sub_df,
                index='attribute 2',
                columns='month',
                values='value',
                aggfunc=aggfunc,
                fill_value=0
            )
            # Reorder columns by month order
            available_months = [m for m in MONTH_ORDER if m in pivot.columns]
            pivot = pivot.reindex(columns=available_months)
            pivot['Total'] = pivot.sum(axis=1) if group_type == 'sum' else pivot.mean(axis=1)
        else:
            pivot = pd.pivot_table(
                sub_df,
                index='attribute 2',
                values='value',
                aggfunc=aggfunc,
                fill_value=0
            )
            pivot.columns = ['Total']
        
        pivot = pivot.reset_index()
        
        # Format values
        for col in pivot.columns[1:]:
            pivot[col] = pivot[col].apply(lambda x: format_value(x, group_type))
        
        # Calculate attribute total
        attr1_total = format_value(sub_df['value'].sum() if group_type == 'sum' else sub_df['value'].mean(), group_type)
        
        results.append((attr1, attr1_total, pivot))
    
    return results

def create_single_attribute_pivot(kpi_df, attribute, report_type, aggfunc, group_type):
    """Handle single attribute pivot tables"""
    if report_type != "Monthly":
        pivot = pd.pivot_table(
            kpi_df,
            index=attribute,
            columns='month',
            values='value',
            aggfunc=aggfunc,
            fill_value=0
        )
        # Reorder columns by month order
        available_months = [m for m in MONTH_ORDER if m in pivot.columns]
        pivot = pivot.reindex(columns=available_months)
        pivot['Total'] = pivot.sum(axis=1) if group_type == 'sum' else pivot.mean(axis=1)
    else:
        pivot = pd.pivot_table(
            kpi_df,
            index=attribute,
            values='value',
            aggfunc=aggfunc,
            fill_value=0
        )
        pivot.columns = ['Total']
    
    pivot = pivot.reset_index()
    
    # Format values
    for col in pivot.columns[1:]:
        pivot[col] = pivot[col].apply(lambda x: format_value(x, group_type))
    
    return pivot

def create_no_attribute_pivot(kpi_df, report_type, aggfunc, group_type):
    """Handle no attribute pivot tables"""
    if report_type != "Monthly":
        pivot = pd.pivot_table(
            kpi_df,
            columns='month',
            values='value',
            aggfunc=aggfunc,
            fill_value=0
        )
        # Reorder columns by month order
        available_months = [m for m in MONTH_ORDER if m in pivot.columns]
        pivot = pivot.reindex(columns=available_months)
        pivot['Total'] = pivot.sum() if group_type == 'sum' else pivot.mean()
        pivot = pd.DataFrame([pivot])
    else:
        total_value = kpi_df['value'].sum() if group_type == 'sum' else kpi_df['value'].mean()
        pivot = pd.DataFrame({'Total': [format_value(total_value, group_type)]})
    
    return pivot


def create_chart(kpi_df, kpi_name, group_type):
    """Create appropriate chart for KPI data and return Plotly figure object."""
    has_attr1 = kpi_df['attribute 1'].notna().any() and kpi_df['attribute 1'].ne("").any()
    has_attr2 = kpi_df['attribute 2'].notna().any() and kpi_df['attribute 2'].ne("").any()
    
    # Use 'mean' for aggregation if group_type is 'average' or 'mean'
    aggfunc = 'sum' if group_type == 'sum' else 'mean' 
    
    fig = None 
    
    if has_attr1 and has_attr2:
        chart_df = kpi_df.groupby(['attribute 1', 'attribute 2'])['value'].agg(aggfunc).reset_index()
        fig = px.bar(
            chart_df,
            x='attribute 1',
            y='value',
            color='attribute 2',
            barmode='group',
            title=f"{kpi_name} by Attributes",
            labels={'value': 'KPI Value', 'attribute 1': chart_df.columns[0], 'attribute 2': chart_df.columns[1]}, # Modified label to just column name
            color_discrete_sequence=px.colors.qualitative.D3 # Use a distinct qualitative color scale
        )
    elif has_attr1:
        chart_df = kpi_df.groupby('attribute 1')['value'].agg(aggfunc).reset_index()
        fig = px.bar(
            chart_df,
            x='attribute 1',
            y='value',
            title=f"{kpi_name} by {chart_df.columns[0]}", # Modified title
            labels={'value': 'KPI Value', 'attribute 1': chart_df.columns[0]}, # Modified label to just column name
            color='value',
            color_continuous_scale='viridis'
        )
    elif has_attr2:
        chart_df = kpi_df.groupby('attribute 2')['value'].agg(aggfunc).reset_index()
        fig = px.bar(
            chart_df,
            x='attribute 2',
            y='value',
            title=f"{kpi_name} by {chart_df.columns[0]}", # Modified title
            labels={'value': 'KPI Value', 'attribute 2': chart_df.columns[0]}, # Modified label to just column name
            color='value',
            color_continuous_scale='viridis'
        )
    else:
        # Create time series chart
        if len(kpi_df['month'].unique()) > 1:
            monthly_data = kpi_df.groupby('month')['value'].agg(aggfunc).reset_index()
            monthly_data['month_num'] = monthly_data['month'].map({month: i for i, month in enumerate(MONTH_ORDER, 1)})
            monthly_data = monthly_data.sort_values('month_num')
            
            fig = px.line(
                monthly_data,
                x='month',
                y='value',
                title=f"{kpi_name} Trend",
                markers=True,
                labels={'value': 'KPI Value', 'month': 'Month'}
            )
        # No chart if only one month and no attributes
    
    if fig:
        # Add a white background to the figure to ensure visibility when exported
        fig.update_layout(
            template='plotly_white', # Set template to plotly_white for clean backgrounds
            margin=dict(l=0, r=0, t=50, b=0),
            height=400,
            showlegend=True,
            font=dict(size=12, color="black") # Ensure text is black
        )
        
        # For line charts, explicitly set a common line color for visibility
        if not (has_attr1 or has_attr2) and len(kpi_df['month'].unique()) > 1:
            fig.update_traces(line_color='blue') # Set line color explicitly for single line charts
        
    return fig


@st.cache_resource # Cache the wkhtmltopdf configuration to avoid re-initializing
def get_pdfkit_config():
    """Configures pdfkit to find wkhtmltopdf executable."""
    # IMPORTANT: Adjust this path based on your deployment environment!
    # For Windows local development:
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    
    # For Linux deployments (e.g., Streamlit Cloud, Heroku) after installing wkhtmltopdf via apt or packages.txt
    if os.name == 'posix': # Check if running on Linux/macOS
        # On Streamlit Cloud (Debian/Ubuntu), it's typically /usr/bin/wkhtmltopdf
        path_wkhtmltopdf = '/usr/bin/wkhtmltopdf' 
        # Sometimes '/usr/local/bin/wkhtmltopdf' might be used for manual installs, but apt puts it in /usr/bin
        # Or if it's in the system's PATH, you might be able to use an empty string:
        # path_wkhtmltopdf = '' 

    try:
        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
        return config
    except Exception as e:
        st.error(f"Error configuring wkhtmltopdf. Please ensure it is installed and the path is correct: {e}")
        st.info("If running locally, download wkhtmltopdf from https://wkhtmltopdf.org/downloads.html")
        st.info("If deploying on Streamlit Cloud, remember to add 'wkhtmltopdf' to packages.txt.")
        st.stop() 

def generate_dashboard_html(df, filters):
    """Generates the full HTML content of the dashboard for PDF conversion."""
    
    # Inline CSS for the PDF report
    inline_css = """
    <style>
        body { font-family: sans-serif; margin: 20px; color: #333; }
        .main-header {
            background: linear-gradient(90deg, #1f77b4, #2ca02c);
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            color: white;
            text-align: center;
        }
        .kpi-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem; /* Adjust margin for HTML export */
            color: white;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: inline-block; /* For side-by-side cards in PDF */
            width: 22%; /* Adjust width for 4 cards in a row */
            vertical-align: top;
        }
        .kpi-value { font-size: 2rem; font-weight: bold; margin: 0.5rem 0; }
        .department-section {
            border-left: 4px solid #1f77b4;
            padding-left: 1rem;
            margin: 1rem 0;
            background-color: #f8f9fa;
            border-radius: 0 10px 10px 0;
        }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; vertical-align: middle; }
        th { background-color: #f0f2f6; font-weight: bold; }
        .plotly-chart-img { max-width: 100%; height: auto; display: block; margin: 1rem auto; } /* Style for embedded chart images */
        hr { border: 0; height: 1px; background-color: #ddd; margin: 2rem 0; }

        /* Custom styling for KPI Name (h3) */
        h3 {
            font-size: 1.3em; /* Adjusted to be between h2 and h4 */
            font-weight: bold;
            color: #333; /* Inherit or specify a color */
        }
        /* New CSS to keep KPI sections together on a single page in PDF */
        .kpi-section-for-pdf {
            page-break-inside: avoid;
            margin-bottom: 2rem; /* Add some space between KPI sections */
        }
    </style>
    """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Horus Hospital KPI Report</title>
        {inline_css}
    </head>
    <body>
        <div class="main-header">
            <h1>🏥 Horus Hospital KPI Report</h1>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Filters: Year: {filters['year']}, Report Type: {filters['report_type']}
            {f", Month: {filters['month']}" if filters['month'] else ""}
            {f", Quarter: {filters['quarter']}" if filters['quarter'] else ""}
            {f", Half: {filters['half']}" if filters['half'] else ""}
            {f", Department: {filters['department']}" if filters['department'] != "All Departments" else ""}
            </p>
        </div>
    """

    report_df = apply_filters(df, filters)

    if report_df.empty:
        html_content += "<p>No data available for selected filters.</p>"
        return html_content + "</body></html>"

    # Removed the call to add summary cards to HTML for PDF
    # html_content += get_summary_cards_html_for_pdf(df, filters)


    for dept in sorted(report_df['department'].dropna().unique()):
        html_content += f"""
        <div class="department-section">
            <h2>🏢 {dept} Department</h2>
        </div>
        """
        # Corrected line: filter report_df instead of dept_df
        dept_df = report_df[report_df['department'] == dept]

        for kpi_data in dept_df[['kpi id', 'kpi name', 'grouping criteria']].drop_duplicates().values:
            kpi_id, kpi_name, group_type = kpi_data
            kpi_df = dept_df[dept_df['kpi id'] == kpi_id] 

            if group_type == "sum":
                total_value = format_value(kpi_df['value'].sum(), group_type)
            else:
                total_value = format_value(kpi_df['value'].mean(), group_type)

            # Wrap each KPI section (heading, table, chart) in a div with page-break-inside: avoid
            html_content += f"""
            <div class="kpi-section-for-pdf">
                <h3>📊 {kpi_name} (Total: {total_value})</h3>
            """

            # Create pivot table
            pivot_result = create_pivot_table(kpi_df, filters['report_type'], group_type)

            if isinstance(pivot_result, list): # Two attributes case
                for attr1, attr1_total, pivot in pivot_result:
                    html_content += f"<h4>{attr1} (Total: {attr1_total})</h4>"
                    # Convert DataFrame to HTML table string
                    html_content += pivot.to_html(index=False, float_format=lambda x: f"{int(x)}" if group_type == 'sum' else f"{x:.1f}")
                    html_content += "<br>"
            else: # Single or no attribute case
                html_content += pivot_result.to_html(index=False, float_format=lambda x: f"{int(x)}" if group_type == 'sum' else f"{x:.1f}")
                html_content += "<br>"

            # Create chart figure and convert to base64 image for HTML
            fig_for_pdf = create_chart(kpi_df, kpi_name, group_type)
            if fig_for_pdf:
                # Requires kaleido package to export Plotly figures to image bytes
                img_bytes = fig_for_pdf.to_image(format="png", engine="kaleido")
                encoded_img = base64.b64encode(img_bytes).decode('utf-8')
                html_content += f'<img src="data:image/png;base64,{encoded_img}" class="plotly-chart-img">'
            
            html_content += "<hr>" # Separator for better readability
            html_content += "</div>" # Close kpi-section-for-pdf div

    html_content += "</body></html>"
    return html_content

# Main application logic
if uploaded_file:
    try:
        # Load and validate data
        df = pd.read_excel(uploaded_file)
        
        if not validate_data(df):
            st.stop()
        
        # Standardize 'grouping criteria' column immediately after loading
        # Replace 'average' with 'mean' for consistent aggregation function names
        df['grouping criteria'] = df['grouping criteria'].astype(str).str.lower().replace('average', 'mean')
        
        df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
        df = df.dropna(subset=['kpi id', 'kpi name', 'department'])
        
        st.success(f"✅ Data loaded successfully! Found {len(df)} records with {df['kpi id'].nunique()} unique KPIs.")
        
        # Create tabs
        tabs = st.tabs(["📊 Dashboard", "🔍 KPI Comparison"])
        
        with tabs[0]:
            # Dashboard tab
            st.header("📊 KPI Dashboard")
            
            # Filter controls - Adjusted column widths for new filter arrangement
            # [Report Type, Year, Dynamic Period (Month/Quarter/Half), KPI Name, Department]
            col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1.5, 2.5, 1.5]) 
            
            with col1:
                report_type = st.selectbox("Report Type", ["Monthly", "Quarter", "Half Annual", "Annual"])
            
            with col2:
                selected_year = st.selectbox("Year", sorted(df['year'].dropna().unique(), reverse=True))
            
            # Dynamic filter based on report type (moved to col3)
            selected_month = selected_quarter = selected_half = None
            
            if report_type == "Monthly":
                with col3: # Moved to col3
                    available_months = sorted(df[df['year'] == selected_year]['month'].dropna().unique(),
                                              key=lambda x: MONTH_ORDER.index(x) if x in MONTH_ORDER else 999)
                    selected_month = st.selectbox("Month", available_months)
            elif report_type == "Quarter":
                with col3: # Moved to col3
                    available_quarters = sorted(df[df['year'] == selected_year]['quarter'].dropna().unique())
                    selected_quarter = st.selectbox("Quarter", available_quarters)
            elif report_type == "Half Annual":
                with col3: # Moved to col3
                    selected_half = st.selectbox("Half", ["H1", "H2"])

            # KPI Name filter - NEW (moved to col4)
            with col4: # Moved to col4
                all_kpi_names_dashboard = ["All KPIs"] + sorted(df['kpi name'].dropna().unique().tolist())
                selected_kpi_names = st.multiselect("KPI Name", all_kpi_names_dashboard, default="All KPIs")
            
            with col5:
                departments = ["All Departments"] + sorted(df['department'].dropna().unique().tolist())
                selected_department = st.selectbox("Department", departments)
            
            # Create filters dictionary
            filters = {
                'report_type': report_type,
                'year': selected_year,
                'month': selected_month,
                'quarter': selected_quarter,
                'half': selected_half,
                'department': selected_department,
                'kpi_name': selected_kpi_names # Add new KPI name filter
            }
            
            # Use a session state variable to store if dashboard is generated
            if 'dashboard_generated' not in st.session_state:
                st.session_state.dashboard_generated = False
            
            generate_button = st.button("🔄 Generate Dashboard", type="primary")

            if generate_button or st.session_state.dashboard_generated:
                st.session_state.dashboard_generated = True # Mark as generated
                with st.spinner("Generating dashboard..."):
                    report_df = apply_filters(df, filters)
                    
                    if report_df.empty:
                        st.warning("⚠️ No data available for selected filters.")
                        st.session_state.dashboard_generated = False # Reset if no data
                    else:
                        st.success(f"📈 Dashboard generated with {len(report_df)} records")
                        
                        # Display summary cards in Streamlit - THIS CALL IS REMOVED
                        # display_summary_cards_streamlit(df, filters) 
                        
                        # Department overview
                        # If a specific KPI is selected, only show that KPI, not department overview
                        # If "All KPIs" or multiple KPIs are selected, proceed with department overview
                        
                        # Determine which KPIs to iterate over for display
                        # Adjust this to use selected_kpi_names from filters directly for consistency
                        
                        # Get KPI names to display from the filters (considering "All KPIs")
                        actual_kpi_names_to_display = []
                        if "All KPIs" in filters['kpi_name']:
                            actual_kpi_names_to_display = sorted(report_df['kpi name'].dropna().unique().tolist())
                        else:
                            actual_kpi_names_to_display = filters['kpi_name']
                        
                        # Filter report_df further based on actual_kpi_names_to_display
                        if actual_kpi_names_to_display:
                            report_df = report_df[report_df['kpi name'].isin(actual_kpi_names_to_display)]

                        displayed_departments = sorted(report_df['department'].dropna().unique())
                        
                        # Consolidated display logic for Dashboard tab
                        if actual_kpi_names_to_display and len(actual_kpi_names_to_display) == 1 and len(displayed_departments) == 1:
                            # Scenario: Single KPI, single department selected (or resulting from filters)
                            kpi_name_selected_single = actual_kpi_names_to_display[0]
                            # MODIFIED: Replaced "Department" with the KPI name in the heading
                            st.markdown(f"## {kpi_name_selected_single} for {displayed_departments[0]}")
                            st.markdown(f"### Selected KPI: {kpi_name_selected_single}") # This line is now redundant/can be removed if desired
                            
                            kpi_df_single = report_df[report_df['kpi name'] == kpi_name_selected_single]
                            group_type_single = kpi_df_single['grouping criteria'].iloc[0]

                            if group_type_single == "sum":
                                total_value = format_value(kpi_df_single['value'].sum(), group_type_single)
                            else:
                                total_value = format_value(kpi_df_single['value'].mean(), group_type_single)
                            
                            with st.expander(f"📊 {kpi_name_selected_single} (Total: {total_value})", expanded=True):
                                pivot_result = create_pivot_table(kpi_df_single, report_type, group_type_single)
                                if isinstance(pivot_result, list):
                                    for attr1, attr1_total, pivot in pivot_result:
                                        st.markdown(f"**{attr1} (Total: {attr1_total})**")
                                        column_config = {}
                                        for col in pivot.columns:
                                            if col != pivot.columns[0]:
                                                column_config[col] = st.column_config.NumberColumn(
                                                    col, format="%d" if pivot[col].dtype == 'int64' else "%.1f"
                                                )
                                            else:
                                                column_config[col] = st.column_config.TextColumn(col)
                                        st.dataframe(pivot, use_container_width=True, hide_index=True, column_config=column_config)
                                else:
                                    column_config = {}
                                    for col in pivot_result.columns:
                                        if col != pivot_result.columns[0]:
                                            column_config[col] = st.column_config.NumberColumn(
                                                col, format="%d" if pivot_result[col].dtype == 'int64' else "%.1f"
                                            )
                                        else:
                                            column_config[col] = st.column_config.TextColumn(col)
                                    st.dataframe(pivot_result, use_container_width=True, hide_index=True, column_config=column_config)
                                
                                fig_to_display = create_chart(kpi_df_single, kpi_name_selected_single, group_type_single)
                                if fig_to_display:
                                    st.plotly_chart(fig_to_display, use_container_width=True)

                        else: # Iterate through departments and then KPIs within them
                            for dept in displayed_departments:
                                with st.container():
                                    st.markdown(f"""
                                        <div class="department-section">
                                            <h3>🏢 {dept} Department</h3>
                                        </div>
                                    """, unsafe_allow_html=True)
                                    
                                    dept_df = report_df[report_df['department'] == dept]
                                    
                                    # Filter KPIs for display within this department, based on selected_kpi_names
                                    kpis_in_dept = dept_df[['kpi id', 'kpi name', 'grouping criteria']].drop_duplicates()
                                    if actual_kpi_names_to_display and "All KPIs" not in selected_kpi_names: # Redundant check, but safe
                                        kpis_in_dept = kpis_in_dept[kpis_in_dept['kpi name'].isin(actual_kpi_names_to_display)]


                                    for kpi_data in kpis_in_dept.values:
                                        kpi_id, kpi_name, group_type = kpi_data
                                        kpi_df = dept_df[dept_df['kpi id'] == kpi_id] 
                                        
                                        if group_type == "sum":
                                            total_value = format_value(kpi_df['value'].sum(), group_type)
                                        else:
                                            total_value = format_value(kpi_df['value'].mean(), group_type)
                                        
                                        with st.expander(f"📊 {kpi_name} (Total: {total_value})", expanded=True):
                                            pivot_result = create_pivot_table(kpi_df, report_type, group_type)
                                            if isinstance(pivot_result, list):
                                                for attr1, attr1_total, pivot in pivot_result:
                                                    st.markdown(f"**{attr1} (Total: {attr1_total})**")
                                                    column_config = {}
                                                    for col in pivot.columns:
                                                        if col != pivot.columns[0]:
                                                            column_config[col] = st.column_config.NumberColumn(
                                                                col, format="%d" if pivot[col].dtype == 'int64' else "%.1f"
                                                            )
                                                        else:
                                                            column_config[col] = st.column_config.TextColumn(col)
                                                    st.dataframe(pivot, use_container_width=True, hide_index=True, column_config=column_config)
                                            else:
                                                column_config = {}
                                                for col in pivot_result.columns:
                                                    if col != pivot_result.columns[0]:
                                                        column_config[col] = st.column_config.NumberColumn(
                                                            col, format="%d" if pivot_result[col].dtype == 'int64' else "%.1f"
                                                        )
                                                    else:
                                                        column_config[col] = st.column_config.TextColumn(col)
                                                st.dataframe(pivot_result, use_container_width=True, hide_index=True, column_config=column_config)
                                            
                                            fig_to_display = create_chart(kpi_df, kpi_name, group_type)
                                            if fig_to_display:
                                                st.plotly_chart(fig_to_display, use_container_width=True)
                        
                        # Add a download button for PDF report
                        st.markdown("---") # Separator before download button
                        st.subheader("⬇️ Download Report")
                        
                        # Generate the full HTML content for the PDF report
                        pdf_html = generate_dashboard_html(df, filters)
                        
                        # Get pdfkit configuration
                        wkhtmltopdf_config = get_pdfkit_config()
                        
                        try:
                            # Generate PDF from HTML string
                            pdf_bytes = pdfkit.from_string(pdf_html, False, configuration=wkhtmltopdf_config)
                            
                            st.download_button(
                                label="Download Dashboard as PDF",
                                data=pdf_bytes,
                                file_name=f"Horus_Hospital_KPI_Report_{filters['year']}_{filters['report_type']}.pdf",
                                mime="application/pdf",
                                help="Download the currently displayed dashboard as a PDF file."
                            )
                        except Exception as e:
                            st.error(f"Failed to generate PDF. Please ensure wkhtmltopdf is correctly installed and configured. Error: {e}")
                            st.info("Check the console/logs for more details, especially regarding wkhtmltopdf path.")

        with tabs[1]:
            st.header("🔍 KPI Comparison")
            # All available KPI names for comparison
            all_kpi_names_comparison = sorted(df['kpi name'].dropna().unique().tolist())

            # Single KPI Name filter for both reports - Now includes "All KPIs" and sets it as default
            selected_kpi_names_comparison_global = st.multiselect(
                "Select KPIs for Comparison", 
                ["All KPIs"] + all_kpi_names_comparison, # Added "All KPIs"
                default=["All KPIs"], # Set "All KPIs" as default
                key="kpi_name_comparison_global"
            )

            # Columns for comparison filters
            # Adjusted column widths to better accommodate period selectors and labels
            comp_col1, comp_col2 = st.columns([1, 1]) 

            # --- Report 1 Filters (Left Side) ---
            with comp_col1:
                st.subheader("Report 1 Filters")
                report_type_1 = st.selectbox("Report Type 1", ["Monthly", "Quarter", "Half Annual", "Annual"], key="report_type_1")
                selected_year_1 = st.selectbox("Year 1", sorted(df['year'].dropna().unique(), reverse=True), key="year_1")
                
                selected_month_1 = None
                selected_quarter_1 = None
                selected_half_1 = None

                if report_type_1 == "Monthly":
                    available_months_1 = sorted(df[df['year'] == selected_year_1]['month'].dropna().unique(), key=lambda x: MONTH_ORDER.index(x) if x in MONTH_ORDER else 999)
                    selected_month_1 = st.selectbox("Month 1", available_months_1, key="month_1")
                elif report_type_1 == "Quarter":
                    available_quarters_1 = sorted(df[df['year'] == selected_year_1]['quarter'].dropna().unique())
                    selected_quarter_1 = st.selectbox("Quarter 1", available_quarters_1, key="quarter_1")
                elif report_type_1 == "Half Annual":
                    selected_half_1 = st.selectbox("Half 1", ["H1", "H2"], key="half_1")
                
                # Dynamic Period Label for Report 1
                period_label_1 = ""
                if report_type_1 == "Monthly" and selected_month_1:
                    period_label_1 = f"{selected_month_1} {selected_year_1}"
                elif report_type_1 == "Quarter" and selected_quarter_1:
                    period_label_1 = f"{selected_quarter_1} {selected_year_1}"
                elif report_type_1 == "Half Annual" and selected_half_1:
                    period_label_1 = f"{selected_half_1} {selected_year_1}"
                elif report_type_1 == "Annual":
                    period_label_1 = str(selected_year_1)

                filters_1 = {
                    'report_type': report_type_1,
                    'year': selected_year_1,
                    'month': selected_month_1,
                    'quarter': selected_quarter_1,
                    'half': selected_half_1,
                    'department': "All Departments", # No department filter as per instruction
                    'kpi_name': selected_kpi_names_comparison_global, # Use global filter
                    'period_label': period_label_1 # Add period label for dynamic column naming
                }

            # --- Report 2 Filters (Right Side) ---
            with comp_col2:
                st.subheader("Report 2 Filters")
                report_type_2 = st.selectbox("Report Type 2", ["Monthly", "Quarter", "Half Annual", "Annual"], key="report_type_2")
                selected_year_2 = st.selectbox("Year 2", sorted(df['year'].dropna().unique(), reverse=True), key="year_2")
                
                selected_month_2 = None
                selected_quarter_2 = None
                selected_half_2 = None

                if report_type_2 == "Monthly":
                    available_months_2 = sorted(df[df['year'] == selected_year_2]['month'].dropna().unique(), key=lambda x: MONTH_ORDER.index(x) if x in MONTH_ORDER else 999)
                    selected_month_2 = st.selectbox("Month 2", available_months_2, key="month_2")
                elif report_type_2 == "Quarter":
                    available_quarters_2 = sorted(df[df['year'] == selected_year_2]['quarter'].dropna().unique())
                    selected_quarter_2 = st.selectbox("Quarter 2", available_quarters_2, key="quarter_2")
                elif report_type_2 == "Half Annual":
                    selected_half_2 = st.selectbox("Half 2", ["H1", "H2"], key="half_2")
                
                # Dynamic Period Label for Report 2
                period_label_2 = ""
                if report_type_2 == "Monthly" and selected_month_2:
                    period_label_2 = f"{selected_month_2} {selected_year_2}"
                elif report_type_2 == "Quarter" and selected_quarter_2:
                    period_label_2 = f"{selected_quarter_2} {selected_year_2}"
                elif report_type_2 == "Half Annual" and selected_half_2:
                    period_label_2 = f"{selected_half_2} {selected_year_2}"
                elif report_type_2 == "Annual":
                    period_label_2 = str(selected_year_2)

                filters_2 = {
                    'report_type': report_type_2, 
                    'year': selected_year_2,
                    'month': selected_month_2,
                    'quarter': selected_quarter_2,
                    'half': selected_half_2,
                    'department': "All Departments", # No department filter as per instruction
                    'kpi_name': selected_kpi_names_comparison_global, # Use global filter
                    'period_label': period_label_2 # Add period label for dynamic column naming
                }

            st.markdown("---") # Separator between filters and comparison results
            compare_button = st.button("Compare KPIs", type="primary", key="compare_button")

            if compare_button:
                st.subheader("Comparison Results")
                
                if not selected_kpi_names_comparison_global:
                    st.warning("Please select at least one KPI to compare.")
                else:
                    kpis_to_compare = selected_kpi_names_comparison_global
                    if "All KPIs" in selected_kpi_names_comparison_global:
                        kpis_to_compare = all_kpi_names_comparison # Use all actual KPI names

                    # Get unique departments from the overall filtered data relevant to selected KPIs
                    # This is important to ensure we only show departments that have data for the selected KPIs
                    all_departments_with_kpi_data = df[df['kpi name'].isin(kpis_to_compare)]['department'].dropna().unique().tolist()
                    
                    if not all_departments_with_kpi_data:
                        st.info("No departments found with data for the selected KPIs in the provided dataset.")
                        st.markdown("---")
                        
                    # Group by department first
                    for dept_comp in sorted(all_departments_with_kpi_data):
                        st.markdown(f"## 🏢 Department: {dept_comp}")

                        # Filter data specific to this department for comparison
                        dept_df_comp = df[df['department'] == dept_comp].copy()

                        # Filter KPIs relevant to this department and selected KPIs for comparison
                        kpis_in_this_dept = dept_df_comp[dept_df_comp['kpi name'].isin(kpis_to_compare)][['kpi id', 'kpi name', 'grouping criteria']].drop_duplicates().values
                        
                        if not kpis_in_this_dept.tolist(): # Check if there are any KPIs to display in this department
                            st.info(f"No KPI data found for selected KPIs in {dept_comp} Department within the chosen comparison periods.")
                            st.markdown("---")
                            continue

                        # Add a flag to track if any KPI data was displayed for this department to avoid generic "No data" message
                        dept_has_displayed_data = False 

                        for kpi_data_comp in kpis_in_this_dept:
                            kpi_id_selected = kpi_data_comp[0]
                            kpi_name_selected = kpi_data_comp[1]
                            group_type = kpi_data_comp[2]

                            # Start with the full dataframe for the specific KPI and department
                            kpi_df_specific_dept = dept_df_comp[dept_df_comp['kpi id'] == kpi_id_selected].copy() 

                            # Apply filters for report 1 and report 2 to these KPI-specific dataframes
                            kpi_df_1_filtered = apply_filters(kpi_df_specific_dept, filters_1)
                            kpi_df_2_filtered = apply_filters(kpi_df_specific_dept, filters_2)


                            if kpi_df_1_filtered.empty and kpi_df_2_filtered.empty:
                                # Only show this message if there's truly no data for this KPI at all in both periods
                                st.info(f"No data for '{kpi_name_selected}' in either selected period for {dept_comp} Department.")
                                continue # Skip to next KPI if no data

                            # Define period names for chart labels and table columns
                            report1_col_name = filters_1['period_label']
                            report2_col_name = filters_2['period_label']
                            
                            # --- Build Comparison Table Data ---
                            
                            has_attr1 = kpi_df_specific_dept['attribute 1'].notna().any() and kpi_df_specific_dept['attribute 1'].ne("").any()
                            has_attr2 = kpi_df_specific_dept['attribute 2'].notna().any() and kpi_df_specific_dept['attribute 2'].ne("").any()

                            # Flag to check if any data was displayed for this specific KPI (or its sub-attributes)
                            local_kpi_data_displayed_in_section = False

                            if has_attr1 and has_attr2:
                                # Iterate through unique values of attribute 1
                                unique_attr1_values = kpi_df_specific_dept['attribute 1'].dropna().unique()

                                for attr1_val in sorted(unique_attr1_values):
                                    # Filter for the current attribute 1 value for both reports
                                    sub_kpi_df_1_filtered = kpi_df_1_filtered[kpi_df_1_filtered['attribute 1'] == attr1_val]
                                    sub_kpi_df_2_filtered = kpi_df_2_filtered[kpi_df_2_filtered['attribute 1'] == attr1_val]

                                    # Group by attribute 2 for this attribute 1 value
                                    agg_df1 = sub_kpi_df_1_filtered.groupby('attribute 2')['value'].agg(group_type).reset_index().rename(columns={'value': report1_col_name})
                                    agg_df2 = sub_kpi_df_2_filtered.groupby('attribute 2')['value'].agg(group_type).reset_index().rename(columns={'value': report2_col_name})
                                    
                                    # Check if both aggregated dataframes are empty for this attribute 1 value
                                    if agg_df1.empty and agg_df2.empty:
                                        continue # Skip to the next primary attribute value

                                    sub_comparison_table_df = pd.merge(agg_df1, agg_df2, on='attribute 2', how='outer').fillna(0)
                                    sub_comparison_table_df['Change'] = sub_comparison_table_df[report2_col_name] - sub_comparison_table_df[report1_col_name]
                                    sub_comparison_table_df['% Change'] = (sub_comparison_table_df['Change'] / sub_comparison_table_df[report1_col_name] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                                    
                                    # Format numerical columns
                                    for col in [report1_col_name, report2_col_name, 'Change']:
                                        if col in sub_comparison_table_df.columns:
                                            sub_comparison_table_df[col] = sub_comparison_table_df[col].apply(lambda x: format_value(x, group_type))

                                    # Add Total Row
                                    sub_total_row_data = {}
                                    sub_total_row_data[sub_comparison_table_df.columns[0]] = "Total" # First column is attr2
                                    sub_total_row_data[report1_col_name] = sub_comparison_table_df[report1_col_name].agg(group_type)
                                    sub_total_row_data[report2_col_name] = sub_comparison_table_df[report2_col_name].agg(group_type)
                                    sub_total_row_data['Change'] = sub_total_row_data[report2_col_name] - sub_total_row_data[report1_col_name]
                                    sub_total_row_data['% Change'] = (sub_total_row_data['Change'] / sub_total_row_data[report1_col_name] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                                    
                                    sub_total_row = pd.DataFrame([sub_total_row_data])
                                    sub_comparison_table_df = pd.concat([sub_comparison_table_df, sub_total_row], ignore_index=True)


                                    # Get the actual attribute 2 column name to use in the title/labels
                                    attr2_col_name = kpi_df_specific_dept.columns[3].replace('attribute ', '') 
                                    sub_comparison_table_df.rename(columns={'attribute 2': attr2_col_name}, inplace=True)


                                    if not sub_comparison_table_df.empty:
                                        local_kpi_data_displayed_in_section = True 
                                        st.markdown(f"#### {kpi_name_selected} ({attr1_val})") # Use KPI name and attr1 value
                                        st.dataframe(sub_comparison_table_df, use_container_width=True, hide_index=True)

                                        # Create chart for this sub-comparison
                                        melted_sub_df = sub_comparison_table_df.iloc[:-1].melt(id_vars=[sub_comparison_table_df.columns[0]], # Exclude 'Total' row
                                                                                value_vars=[report1_col_name, report2_col_name],
                                                                                var_name='Period', value_name='Value')
                                        
                                        fig_sub_comp = px.bar(
                                            melted_sub_df, 
                                            x=melted_sub_df.columns[0], 
                                            y='Value', 
                                            color='Period', 
                                            barmode='group',
                                            title=f"Comparison for {kpi_name_selected} ({attr1_val})", # Modified title
                                            labels={'Value': 'KPI Value', melted_sub_df.columns[0]: attr2_col_name}, 
                                            color_discrete_map={report1_col_name: 'blue', report2_col_name: 'red'},
                                            template='plotly_white'
                                        )
                                        fig_sub_comp.update_layout(
                                            margin=dict(l=0, r=0, t=50, b=0),
                                            height=400,
                                            showlegend=True,
                                            font=dict(size=12, color="black"),
                                            xaxis_title="" # Hide x-axis title
                                        )
                                        st.plotly_chart(fig_sub_comp, use_container_width=True)
                                    
                                    st.markdown("-----") # Sub-separator for clarity
                                
                                if not local_kpi_data_displayed_in_section: 
                                    st.info(f"No detailed attribute data found for '{kpi_name_selected}' (grouped by {kpi_df_specific_dept.columns[2].replace('attribute ', '')} and {kpi_df_specific_dept.columns[3].replace('attribute ', '')}) in either selected period for {dept_comp} Department.")


                            elif has_attr1:
                                # Group by attribute 1
                                agg_df1 = kpi_df_1_filtered.groupby('attribute 1')['value'].agg(group_type).reset_index().rename(columns={'value': report1_col_name})
                                agg_df2 = kpi_df_2_filtered.groupby('attribute 1')['value'].agg(group_type).reset_index().rename(columns={'value': report2_col_name})
                                
                                # Check if both aggregated dataframes are empty
                                if agg_df1.empty and agg_df2.empty:
                                    st.info(f"No attribute data ({kpi_df_specific_dept.columns[2].replace('attribute ', '')}) found for '{kpi_name_selected}' in either selected period for {dept_comp} Department.")
                                    st.markdown("---")
                                    continue # Skip to next KPI

                                comparison_table_df = pd.merge(agg_df1, agg_df2, on='attribute 1', how='outer').fillna(0)
                                comparison_table_df['Change'] = comparison_table_df[report2_col_name] - comparison_table_df[report1_col_name]
                                comparison_table_df['% Change'] = (comparison_table_df['Change'] / comparison_table_df[report1_col_name] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                                
                                attr1_col_name = kpi_df_specific_dept.columns[2].replace('attribute ', '')
                                comparison_table_df.rename(columns={'attribute 1': attr1_col_name}, inplace=True) # Removed "Attribute " prefix

                                # Add Total Row
                                total_row_data = {}
                                total_row_data[comparison_table_df.columns[0]] = "Total" # First column is attr1
                                total_row_data[report1_col_name] = comparison_table_df[report1_col_name].agg(group_type)
                                total_row_data[report2_col_name] = comparison_table_df[report2_col_name].agg(group_type)
                                total_row_data['Change'] = total_row_data[report2_col_name] - total_row_data[report1_col_name]
                                total_row_data['% Change'] = (total_row_data['Change'] / total_row_data[report1_col_name] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                                
                                total_row = pd.DataFrame([total_row_data])
                                comparison_table_df = pd.concat([comparison_table_df, total_row], ignore_index=True)


                                if not comparison_table_df.empty:
                                    local_kpi_data_displayed_in_section = True
                                    st.dataframe(comparison_table_df, use_container_width=True, hide_index=True)

                                    # --- Create Comparison Chart for has_attr1 ---
                                    melted_df = comparison_table_df.iloc[:-1].melt(id_vars=[comparison_table_df.columns[0]], # Exclude 'Total' row
                                                                        value_vars=[report1_col_name, report2_col_name],
                                                                        var_name='Period', value_name='Value')
                                    fig_comp = px.bar(
                                        melted_df, 
                                        x=melted_df.columns[0], # Use the renamed attribute column as x-axis
                                        y='Value', 
                                        color='Period', 
                                        barmode='group',
                                        title=f"Comparison for {kpi_name_selected} ({attr1_col_name})", # Modified title, removed "by X"
                                        labels={'Value': 'KPI Value', melted_df.columns[0]: attr1_col_name}, # Modified label
                                        color_discrete_map={report1_col_name: 'blue', report2_col_name: 'red'},
                                        template='plotly_white'
                                    )
                                    fig_comp.update_layout(
                                        margin=dict(l=0, r=0, t=50, b=0),
                                        height=400,
                                        showlegend=True,
                                        font=dict(size=12, color="black"),
                                        xaxis_title="" # Hide x-axis title
                                    )
                                    st.plotly_chart(fig_comp, use_container_width=True)


                            elif has_attr2:
                                # Group by attribute 2
                                agg_df1 = kpi_df_1_filtered.groupby('attribute 2')['value'].agg(group_type).reset_index().rename(columns={'value': report1_col_name})
                                agg_df2 = kpi_df_2_filtered.groupby('attribute 2')['value'].agg(group_type).reset_index().rename(columns={'value': report2_col_name})

                                # Check if both aggregated dataframes are empty
                                if agg_df1.empty and agg_df2.empty:
                                    st.info(f"No attribute data ({kpi_df_specific_dept.columns[3].replace('attribute ', '')}) found for '{kpi_name_selected}' in either selected period for {dept_comp} Department.")
                                    st.markdown("---")
                                    continue # Skip to next KPI

                                comparison_table_df = pd.merge(agg_df1, agg_df2, on='attribute 2', how='outer').fillna(0)
                                comparison_table_df['Change'] = comparison_table_df[report2_col_name] - comparison_table_df[report1_col_name]
                                comparison_table_df['% Change'] = (comparison_table_df['Change'] / comparison_table_df[report1_col_name] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                                
                                attr2_col_name = kpi_df_specific_dept.columns[3].replace('attribute ', '')
                                comparison_table_df.rename(columns={'attribute 2': attr2_col_name}, inplace=True) # Removed "Attribute " prefix

                                # Add Total Row
                                total_row_data = {}
                                total_row_data[comparison_table_df.columns[0]] = "Total" # First column is attr2
                                total_row_data[report1_col_name] = comparison_table_df[report1_col_name].agg(group_type)
                                total_row_data[report2_col_name] = comparison_table_df[report2_col_name].agg(group_type)
                                total_row_data['Change'] = total_row_data[report2_col_name] - total_row_data[report1_col_name]
                                total_row_data['% Change'] = (total_row_data['Change'] / total_row_data[report1_col_name] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                                
                                total_row = pd.DataFrame([total_row_data])
                                comparison_table_df = pd.concat([comparison_table_df, total_row], ignore_index=True)


                                if not comparison_table_df.empty:
                                    local_kpi_data_displayed_in_section = True
                                    st.dataframe(comparison_table_df, use_container_width=True, hide_index=True)

                                    # --- Create Comparison Chart for has_attr2 ---
                                    melted_df = comparison_table_df.iloc[:-1].melt(id_vars=[comparison_table_df.columns[0]], # Exclude 'Total' row
                                                                        value_vars=[report1_col_name, report2_col_name],
                                                                        var_name='Period', value_name='Value')
                                    fig_comp = px.bar(
                                        melted_df, 
                                        x=melted_df.columns[0], # Use the renamed attribute column as x-axis
                                        y='Value', 
                                        color='Period', 
                                        barmode='group',
                                        title=f"Comparison for {kpi_name_selected} ({attr2_col_name})", # Modified title
                                        labels={'Value': 'KPI Value', melted_df.columns[0]: attr2_col_name}, # Modified label
                                        color_discrete_map={report1_col_name: 'blue', report2_col_name: 'red'},
                                        template='plotly_white'
                                    )
                                    fig_comp.update_layout(
                                        margin=dict(l=0, r=0, t=50, b=0),
                                        height=400,
                                        showlegend=True,
                                        font=dict(size=12, color="black"),
                                        xaxis_title="" # Hide x-axis title
                                    )
                                    st.plotly_chart(fig_comp, use_container_width=True)


                            else: # No attributes
                                # No attributes, just aggregate the total KPI value for each period
                                total_val_1 = kpi_df_1_filtered['value'].agg(group_type) if not kpi_df_1_filtered.empty else 0
                                total_val_2 = kpi_df_2_filtered['value'].agg(group_type) if not kpi_df_2_filtered.empty else 0
                                
                                change = total_val_2 - total_val_1
                                pct_change = (change / total_val_1 * 100) if total_val_1 != 0 else (0 if change == 0 else np.nan)
                                pct_change_str = f"{pct_change:.1f}%" if pd.notna(pct_change) else "N/A"

                                comparison_table_df = pd.DataFrame({
                                    'KPI': [kpi_name_selected],
                                    report1_col_name: [format_value(total_val_1, group_type)],
                                    report2_col_name: [format_value(total_val_2, group_type)],
                                    'Change': [format_value(change, group_type)],
                                    '% Change': [pct_change_str]
                                })
                                
                                # Add Total Row (for no attribute case, it's just the one row)
                                # No need to aggregate, as it's already a single row summarizing the KPI
                                total_val_1_fmt = format_value(total_val_1, group_type)
                                total_val_2_fmt = format_value(total_val_2, group_type)
                                change_fmt = format_value(change, group_type)

                                total_row_data = {
                                    'KPI': "Total",
                                    report1_col_name: total_val_1_fmt,
                                    report2_col_name: total_val_2_fmt,
                                    'Change': change_fmt,
                                    '% Change': pct_change_str
                                }
                                comparison_table_df = pd.concat([comparison_table_df, pd.DataFrame([total_row_data])], ignore_index=True)

                                if not comparison_table_df.empty:
                                    local_kpi_data_displayed_in_section = True
                                    st.dataframe(comparison_table_df, use_container_width=True, hide_index=True)

                                    # --- Create Comparison Chart for no attributes ---
                                    melted_df = comparison_table_df.iloc[:-1].melt(id_vars=['KPI'], # Exclude 'Total' row
                                                                        value_vars=[report1_col_name, report2_col_name],
                                                                        var_name='Period', value_name='Value')
                                    fig_comp = px.bar(
                                        melted_df, 
                                        x='Period', 
                                        y='Value', 
                                        color='Period',
                                        title=f"Overall Comparison for {kpi_name_selected}",
                                        labels={'Value': 'KPI Value'},
                                        color_discrete_map={report1_col_name: 'blue', report2_col_name: 'red'},
                                        template='plotly_white'
                                    )
                                    fig_comp.update_layout(
                                        margin=dict(l=0, r=0, t=50, b=0),
                                        height=400,
                                        showlegend=True,
                                        font=dict(size=12, color="black")
                                    )
                                    st.plotly_chart(fig_comp, use_container_width=True)
                            
                            if not local_kpi_data_displayed_in_section: # If no data was displayed for this specific KPI
                                st.info(f"No comparison data could be generated for '{kpi_name_selected}' in {dept_comp} Department given the chosen periods. Please check your filters and data.")
                        
                        st.markdown("---") # Separator between KPI comparisons
                    
                    # Final check for the overall comparison section if anything was displayed
                    # This global kpi_data_displayed logic needs to be managed carefully
                    # as it's set True within nested loops.
                    # A more robust check might be to track if `any_kpi_data_was_displayed_overall`
                    # outside the department loop.
                    
                    # For simplicity, if the initial all_departments_with_kpi_data is empty,
                    # we already show a message. If it's not empty, but all nested loops
                    # resulted in 'continue' or no data, the individual st.info will cover it.

    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.info("Please check your file format and try again.")

else:
    # Show sample data structure only
    st.subheader("📋 Sample Data Structure")
    sample_data = pd.DataFrame({
        'kpi id': ['KPI001', 'KPI001', 'KPI002'],
        'kpi name': ['Patient Satisfaction', 'Patient Satisfaction', 'Average Wait-Time'],
        'attribute 1': ['Outpatient', 'Inpatient', 'Emergency'],
        'attribute 2': ['Cardiology', 'Surgery', 'Triage'],
        'grouping criteria': ['average', 'average', 'average'],
        'value': [4.5, 4.8, 25.5],
        'month': ['January', 'January', 'January'],
        'quarter': ['Q1', 'Q1', 'Q1'],
        'year': [2024, 2024, 2024],
        'department': ['Cardiology', 'Surgery', 'Emergency']
    })
    
    st.dataframe(sample_data, use_container_width=True)
