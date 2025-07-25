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

# Enhanced CSS styling
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
        .element-container table td,
        .streamlit-expanderContent table th,
        .streamlit-expanderContent table td {
            text-align: center !important;
            vertical-align: middle !important;
            padding: 0.5rem !important;
        }
        
        /* Header specific styling */
        table th,
        .dataframe th,
        div[data-testid="stDataFrame"] th,
        div[data-testid="stDataFrame"] table th,
        .stDataFrame th,
        .stDataFrame table th,
        [data-testid="stDataFrame"] th,
        [data-testid="stDataFrame"] table th,
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
               "July", "August", "September", "October", "November", "December"]
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

def format_value(value, group_type):
    """Format values based on grouping criteria"""
    if pd.isna(value):
        return 0
    return int(value) if group_type == 'sum' else round(float(value), 1)

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
    
    # Department filter
    if filters.get('department') and filters['department'] != "All Departments":
        filtered_df = filtered_df[filtered_df['department'] == filters['department']]
    
    return filtered_df

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
            labels={'value': 'KPI Value', 'attribute 1': 'Primary Attribute', 'attribute 2': 'Secondary Attribute'}
        )
    elif has_attr1:
        chart_df = kpi_df.groupby('attribute 1')['value'].agg(aggfunc).reset_index()
        fig = px.bar(
            chart_df,
            x='attribute 1',
            y='value',
            title=f"{kpi_name} by Primary Attribute",
            labels={'value': 'KPI Value', 'attribute 1': 'Primary Attribute'},
            color='value',
            color_continuous_scale='viridis'
        )
    elif has_attr2:
        chart_df = kpi_df.groupby('attribute 2')['value'].agg(aggfunc).reset_index()
        fig = px.bar(
            chart_df,
            x='attribute 2',
            y='value',
            title=f"{kpi_name} by Secondary Attribute",
            labels={'value': 'KPI Value', 'attribute 2': 'Secondary Attribute'},
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
        fig.update_layout(
            margin=dict(l=0, r=0, t=50, b=0),
            height=400,
            showlegend=True,
            font=dict(size=12)
        )
        
    return fig


@st.cache_resource # Cache the wkhtmltopdf configuration to avoid re-initializing
def get_pdfkit_config():
    """Configures pdfkit to find wkhtmltopdf executable."""
    # IMPORTANT: Adjust this path based on your deployment environment!
    # For Windows local development:
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    
    # For Linux deployments (e.g., Streamlit Cloud, Heroku) after installing wkhtmltopdf via apt or packages.txt
    if os.name == 'posix': # Check if running on Linux/macOS
        path_wkhtmltopdf = '/usr/local/bin/wkhtmltopdf' # Common path after manual install
        # Or often just '/usr/bin/wkhtmltopdf' if installed via apt-get
        # If it's in the system's PATH, you might be able to use an empty string:
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

    # Add summary cards to HTML for PDF
    html_content += get_summary_cards_html_for_pdf(df, filters)


    for dept in sorted(report_df['department'].dropna().unique()):
        html_content += f"""
        <div class="department-section">
            <h2>🏢 {dept} Department</h2>
        </div>
        """
        dept_df = report_df[report_df['department'] == dept]

        for kpi_data in dept_df[['kpi id', 'kpi name', 'grouping criteria']].drop_duplicates().values:
            kpi_id, kpi_name, group_type = kpi_data
            kpi_df = dept_df[dept_df['kpi id'] == kpi_id]

            if group_type == "sum":
                total_value = format_value(kpi_df['value'].sum(), group_type)
            else:
                total_value = format_value(kpi_df['value'].mean(), group_type)

            html_content += f"<h3>📊 {kpi_name} (Total: {total_value})</h3>"

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

    html_content += "</body></html>"
    return html_content

# Main application logic
if uploaded_file:
    try:
        # Load and validate data
        df = pd.read_excel(uploaded_file)
        df = df.replace({np.nan: None})
        
        if not validate_data(df):
            st.stop()
        
        # Clean data
        df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
        df = df.dropna(subset=['kpi id', 'kpi name', 'department'])
        
        st.success(f"✅ Data loaded successfully! Found {len(df)} records with {df['kpi id'].nunique()} unique KPIs.")
        
        # Create tabs
        tabs = st.tabs(["📊 Dashboard", "🔍 KPI Comparison"])
        
        with tabs[0]:
            # Dashboard tab
            st.header("📊 KPI Dashboard")
            
            # Filter controls
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])
            
            with col1:
                report_type = st.selectbox("Report Type", ["Monthly", "Quarter", "Half Annual", "Annual"])
            
            with col2:
                selected_year = st.selectbox("Year", sorted(df['year'].dropna().unique(), reverse=True))
            
            with col5:
                departments = ["All Departments"] + sorted(df['department'].dropna().unique().tolist())
                selected_department = st.selectbox("Department", departments)
            
            # Dynamic filter based on report type
            selected_month = selected_quarter = selected_half = None
            
            if report_type == "Monthly":
                with col3:
                    available_months = sorted(df[df['year'] == selected_year]['month'].dropna().unique(),
                                              key=lambda x: MONTH_ORDER.index(x) if x in MONTH_ORDER else 999)
                    selected_month = st.selectbox("Month", available_months)
            elif report_type == "Quarter":
                with col3:
                    available_quarters = sorted(df[df['year'] == selected_year]['quarter'].dropna().unique())
                    selected_quarter = st.selectbox("Quarter", available_quarters)
            elif report_type == "Half Annual":
                with col3:
                    selected_half = st.selectbox("Half", ["H1", "H2"])
            
            # Create filters dictionary
            filters = {
                'report_type': report_type,
                'year': selected_year,
                'month': selected_month,
                'quarter': selected_quarter,
                'half': selected_half,
                'department': selected_department
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
                        
                        # Display summary cards in Streamlit
                        display_summary_cards_streamlit(df, filters) 
                        
                        # Department overview
                        for dept in sorted(report_df['department'].dropna().unique()):
                            with st.container():
                                st.markdown(f"""
                                    <div class="department-section">
                                        <h3>🏢 {dept} Department</h3>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                dept_df = report_df[report_df['department'] == dept]
                                
                                # Show KPIs for this department
                                for kpi_data in dept_df[['kpi id', 'kpi name', 'grouping criteria']].drop_duplicates().values:
                                    kpi_id, kpi_name, group_type = kpi_data
                                    kpi_df = dept_df[dept_df['kpi id'] == kpi_id]
                                    
                                    # Calculate total for display
                                    if group_type == "sum":
                                        total_value = format_value(kpi_df['value'].sum(), group_type)
                                    else:
                                        total_value = format_value(kpi_df['value'].mean(), group_type)
                                    
                                    with st.expander(f"📊 {kpi_name} (Total: {total_value})", expanded=True):
                                        # Create pivot table
                                        pivot_result = create_pivot_table(kpi_df, report_type, group_type)
                                        
                                        if isinstance(pivot_result, list):
                                            # Two attributes case
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
                                                
                                                st.dataframe(
                                                    pivot,
                                                    use_container_width=True,
                                                    hide_index=True,
                                                    column_config=column_config
                                                )
                                        else:
                                            # Single or no attribute case
                                            column_config = {}
                                            for col in pivot_result.columns:
                                                if col != pivot_result.columns[0]:
                                                    column_config[col] = st.column_config.NumberColumn(
                                                        col, format="%d" if pivot_result[col].dtype == 'int64' else "%.1f"
                                                    )
                                                else:
                                                    column_config[col] = st.column_config.TextColumn(col)
                                            
                                            st.dataframe(
                                                pivot_result,
                                                use_container_width=True,
                                                hide_index=True,
                                                column_config=column_config
                                            )
                                        
                                        # Create chart for Streamlit display
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
            st.info("🚧 KPI comparison tools coming soon!")
            
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.info("Please check your file format and try again.")

else:
    # Show sample data structure only
    st.subheader("📋 Sample Data Structure")
    sample_data = pd.DataFrame({
        'kpi id': ['KPI001', 'KPI001', 'KPI002'],
        'kpi name': ['Patient Satisfaction', 'Patient Satisfaction', 'Average Wait Time'],
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

```
