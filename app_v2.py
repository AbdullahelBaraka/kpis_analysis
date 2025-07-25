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
    - `kpi id` - Unique KPI identifier [cite: 18]
    - `kpi name` - KPI description [cite: 18]
    - `attribute 1` - Primary grouping attribute [cite: 18]
    - `attribute 2` - Secondary grouping attribute [cite: 18]
    - `grouping criteria` - 'sum' or 'average' [cite: 18]
    - `value` - KPI numeric value [cite: 18]
    - `month` - Month name [cite: 18]
    - `quarter` - Quarter (Q1, Q2, Q3, Q4) [cite: 18]
    - `year` - Year (YYYY) [cite: 18]
    - `department` - Department name [cite: 18]
    """)

# Constants
MONTH_ORDER = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"] [cite: 19]
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
    missing_columns = [col for col in required_columns if col not in df.columns] [cite: 20]
    
    if missing_columns:
        st.error(f"Missing required columns: {', '.join(missing_columns)}")
        return False
    
    # Check for numeric values
    if not pd.api.types.is_numeric_dtype(df['value']):
        st.error("'value' column must contain numeric data")
        return False
        
    return True

def format_value(value, group_type):
    """Format values based on grouping criteria""" [cite: 21]
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
        filtered_df = filtered_df[filtered_df['month'] == filters['month']] [cite: 22]
    elif filters['report_type'] == "Quarter" and filters['quarter']:
        quarter_months = QUARTER_MONTHS.get(filters['quarter'], [])
        filtered_df = filtered_df[filtered_df['month'].isin(quarter_months)]
    elif filters['report_type'] == "Half Annual" and filters['half']:
        if filters['half'] == "H1":
            filtered_df = filtered_df[filtered_df['month'].isin(MONTH_ORDER[:6])]
        else:
            filtered_df = filtered_df[filtered_df['month'].isin(MONTH_ORDER[6:])]
    
    # Department filter [cite: 23]
    if filters.get('department') and filters['department'] != "All Departments":
        filtered_df = filtered_df[filtered_df['department'] == filters['department']]
    
    return filtered_df

# START OF UNCOMMENTED display_summary_cards_streamlit FUNCTION
def display_summary_cards_streamlit(df, filters):
    """Displays KPI summary cards in Streamlit columns.""" [cite: 23]
    filtered_df = apply_filters(df, filters)
    
    if filtered_df.empty:
        return # Nothing to display
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_kpis = filtered_df['kpi id'].nunique() [cite: 24]
    with col1:
        st.markdown(f"""
            <div class="kpi-card">
                <h4>📊 Total KPIs</h4>
                <div class="kpi-value">{total_kpis}</div>
            </div>
        """, unsafe_allow_html=True)
    
    total_departments = filtered_df['department'].nunique() [cite: 25]
    with col2:
        st.markdown(f"""
            <div class="kpi-card">
                <h4>🏢 Departments</h4>
                <div class="kpi-value">{total_departments}</div>
            </div>
        """, unsafe_allow_html=True)
    
    avg_value = filtered_df['value'].mean() [cite: 26]
    with col3:
        st.markdown(f"""
            <div class="kpi-card">
                <h4>📈 Avg Value</h4>
                <div class="kpi-value">{format_value(avg_value, 'average')}</div>
            </div>
        """, unsafe_allow_html=True)
    
    total_records = len(filtered_df) [cite: 27]
    with col4:
        st.markdown(f"""
            <div class="kpi-card">
                <h4>📋 Records</h4>
                <div class="kpi-value">{total_records}</div>
            </div>
        """, unsafe_allow_html=True)
# END OF UNCOMMENTED display_summary_cards_streamlit FUNCTION

# START OF UNCOMMENTED get_summary_cards_html_for_pdf FUNCTION
def get_summary_cards_html_for_pdf(df, filters):
    """Generates HTML string for KPI summary cards, suitable for PDF embedding.""" [cite: 27]
    filtered_df = apply_filters(df, filters)
    
    if filtered_df.empty:
        return ""
  
    summary_html = "" [cite: 28]
    
    total_kpis = filtered_df['kpi id'].nunique() [cite: 28]
    summary_html += f"""
        <div class="kpi-card">
            <h4>📊 Total KPIs</h4>
            <div class="kpi-value">{total_kpis}</div>
        </div>
    """
    
    total_departments = filtered_df['department'].nunique() [cite: 28]
    summary_html += f"""
        <div class="kpi-card">
            <h4>🏢 Departments</h4> [cite: 29]
            <div class="kpi-value">{total_departments}</div>
        </div>
    """
    
    avg_value = filtered_df['value'].mean() [cite: 29]
    summary_html += f"""
        <div class="kpi-card">
            <h4>📈 Avg Value</h4>
            <div class="kpi-value">{format_value(avg_value, 'average')}</div>
        </div>
    """
    
    total_records = len(filtered_df) [cite: 30]
    summary_html += f"""
        <div class="kpi-card">
            <h4>📋 Records</h4>
            <div class="kpi-value">{total_records}</div>
        </div>
    """
    # Wrap in a flex container for PDF layout
    return f"""<div style="display:flex; justify-content:space-around; flex-wrap:wrap; margin-bottom: 2rem;">{summary_html}</div>""" [cite: 31]
# END OF UNCOMMENTED get_summary_cards_html_for_pdf FUNCTION

def create_pivot_table(kpi_df, report_type, group_type):
    """Create pivot table for KPI data""" [cite: 31]
    has_attr1 = kpi_df['attribute 1'].notna().any() and kpi_df['attribute 1'].ne("").any()
    has_attr2 = kpi_df['attribute 2'].notna().any() and kpi_df['attribute 2'].ne("").any()
    
    aggfunc = 'sum' if group_type == 'sum' else 'mean'
    
    if has_attr1 and has_attr2:
        # Two attributes case
        return create_two_attribute_pivot(kpi_df, report_type, aggfunc, group_type)
    elif has_attr1:
        # Single attribute 1 case [cite: 32]
        return create_single_attribute_pivot(kpi_df, 'attribute 1', report_type, aggfunc, group_type)
    elif has_attr2:
        # Single attribute 2 case [cite: 32]
        return create_single_attribute_pivot(kpi_df, 'attribute 2', report_type, aggfunc, group_type)
    else:
        # No attributes case [cite: 32]
        return create_no_attribute_pivot(kpi_df, report_type, aggfunc, group_type)

def create_two_attribute_pivot(kpi_df, report_type, aggfunc, group_type):
    """Handle two attribute pivot tables""" [cite: 32]
    results = []
    
    for attr1 in sorted(kpi_df['attribute 1'].dropna().unique()):
        sub_df = kpi_df[kpi_df['attribute 1'] == attr1]
        
        if report_type != "Monthly":
            pivot = pd.pivot_table(
                sub_df,
                index='attribute 2',
                columns='month',
                values='value', [cite: 34]
                aggfunc=aggfunc,
                fill_value=0
            )
            # Reorder columns by month order
            available_months = [m for m in MONTH_ORDER if m in pivot.columns]
            pivot = pivot.reindex(columns=available_months) [cite: 35]
            pivot['Total'] = pivot.sum(axis=1) if group_type == 'sum' else pivot.mean(axis=1)
        else:
            pivot = pd.pivot_table(
                sub_df,
                index='attribute 2',
                values='value', [cite: 36]
                aggfunc=aggfunc,
                fill_value=0
            )
            pivot.columns = ['Total']
        
        pivot = pivot.reset_index()
        
        # Format values [cite: 36]
        for col in pivot.columns[1:]: [cite: 37]
            pivot[col] = pivot[col].apply(lambda x: format_value(x, group_type))
        
        # Calculate attribute total [cite: 37]
        attr1_total = format_value(sub_df['value'].sum() if group_type == 'sum' else sub_df['value'].mean(), group_type)
        
        results.append((attr1, attr1_total, pivot)) [cite: 37]
    
    return results

def create_single_attribute_pivot(kpi_df, attribute, report_type, aggfunc, group_type):
    """Handle single attribute pivot tables""" [cite: 38]
    if report_type != "Monthly":
        pivot = pd.pivot_table(
            kpi_df,
            index=attribute,
            columns='month',
            values='value',
            aggfunc=aggfunc,
            fill_value=0
        )
        # Reorder columns by month order [cite: 39]
        available_months = [m for m in MONTH_ORDER if m in pivot.columns]
        pivot = pivot.reindex(columns=available_months) [cite: 39]
        pivot['Total'] = pivot.sum(axis=1) if group_type == 'sum' else pivot.mean(axis=1)
    else:
        pivot = pd.pivot_table(
            kpi_df,
            index=attribute,
            values='value', [cite: 40]
            aggfunc=aggfunc,
            fill_value=0
        )
        pivot.columns = ['Total']
    
    pivot = pivot.reset_index()
    
    # Format values [cite: 40]
    for col in pivot.columns[1:]: [cite: 40]
        pivot[col] = pivot[col].apply(lambda x: format_value(x, group_type))
    
    return pivot

def create_no_attribute_pivot(kpi_df, report_type, aggfunc, group_type): [cite: 41]
    """Handle no attribute pivot tables""" [cite: 41]
    if report_type != "Monthly":
        pivot = pd.pivot_table(
            kpi_df,
            columns='month',
            values='value',
            aggfunc=aggfunc,
            fill_value=0
        )
        # Reorder columns by month order [cite: 42]
        available_months = [m for m in MONTH_ORDER if m in pivot.columns]
        pivot = pivot.reindex(columns=available_months) [cite: 42]
        pivot['Total'] = pivot.sum() if group_type == 'sum' else pivot.mean()
        pivot = pd.DataFrame([pivot])
    else:
        total_value = kpi_df['value'].sum() if group_type == 'sum' else kpi_df['value'].mean()
        pivot = pd.DataFrame({'Total': [format_value(total_value, group_type)]})
    
    return pivot [cite: 43]


def create_chart(kpi_df, kpi_name, group_type):
    """Create appropriate chart for KPI data and return Plotly figure object.""" [cite: 43]
    has_attr1 = kpi_df['attribute 1'].notna().any() and kpi_df['attribute 1'].ne("").any()
    has_attr2 = kpi_df['attribute 2'].notna().any() and kpi_df['attribute 2'].ne("").any()
    
    aggfunc = 'sum' if group_type == 'sum' else 'mean'
    
    fig = None 
    
    if has_attr1 and has_attr2:
        chart_df = kpi_df.groupby(['attribute 1', 'attribute 2'])['value'].agg(aggfunc).reset_index()
        fig = px.bar(
            chart_df, [cite: 44]
            x='attribute 1',
            y='value',
            color='attribute 2',
            barmode='group',
            title=f"{kpi_name} by Attributes",
            labels={'value': 'KPI Value', 'attribute 1': 'Primary Attribute', 'attribute 2': 'Secondary Attribute'}
        ) [cite: 45]
    elif has_attr1:
        chart_df = kpi_df.groupby('attribute 1')['value'].agg(aggfunc).reset_index()
        fig = px.bar(
            chart_df,
            x='attribute 1',
            y='value',
            title=f"{kpi_name} by Primary Attribute",
            labels={'value': 'KPI Value', 'attribute 1': 'Primary Attribute'}, [cite: 46]
            color='value',
            color_continuous_scale='viridis'
        )
    elif has_attr2:
        chart_df = kpi_df.groupby('attribute 2')['value'].agg(aggfunc).reset_index()
        fig = px.bar(
            chart_df,
            x='attribute 2',
            y='value',
            title=f"{kpi_name} by Secondary Attribute", [cite: 47]
            labels={'value': 'KPI Value', 'attribute 2': 'Secondary Attribute'},
            color='value',
            color_continuous_scale='viridis'
        )
    else:
        # Create time series chart [cite: 47]
        if len(kpi_df['month'].unique()) > 1:
            monthly_data = kpi_df.groupby('month')['value'].agg(aggfunc).reset_index() [cite: 48]
            monthly_data['month_num'] = monthly_data['month'].map({month: i for i, month in enumerate(MONTH_ORDER, 1)})
            monthly_data = monthly_data.sort_values('month_num')
            
            fig = px.line(
                monthly_data,
                x='month',
                y='value', [cite: 49]
                title=f"{kpi_name} Trend",
                markers=True,
                labels={'value': 'KPI Value', 'month': 'Month'}
            )
        # No chart if only one month and no attributes [cite: 49]
    
    if fig: [cite: 50]
        fig.update_layout(
            margin=dict(l=0, r=0, t=50, b=0),
            height=400,
            showlegend=True,
            font=dict(size=12)
        )
        
    return fig


@st.cache_resource # Cache the wkhtmltopdf configuration to avoid re-initializing
def get_pdfkit_config():
    """Configures pdfkit to find wkhtmltopdf executable.""" [cite: 51]
    # IMPORTANT: Adjust this path based on your deployment environment! [cite: 51]
    # For Windows local development: [cite: 52]
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    
    # For Linux deployments (e.g., Streamlit Cloud, Heroku) after installing wkhtmltopdf via apt or packages.txt [cite: 52]
    if os.name == 'posix': # Check if running on Linux/macOS [cite: 52]
        # On Streamlit Cloud (Debian/Ubuntu), it's typically /usr/bin/wkhtmltopdf [cite: 52]
        path_wkhtmltopdf = '/usr/bin/wkhtmltopdf' 
        # Sometimes '/usr/local/bin/wkhtmltopdf' might be used for manual installs, but apt puts it in /usr/bin [cite: 52]
        # Or if it's in the system's PATH, you might be able to use an empty string: [cite: 53]
        # path_wkhtmltopdf = '' 

    try:
        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
        return config
    except Exception as e:
        st.error(f"Error configuring wkhtmltopdf. Please ensure it is installed and the path is correct: {e}") [cite: 53]
        st.info("If running locally, download wkhtmltopdf from https://wkhtmltopdf.org/downloads.html") [cite: 53]
        st.info("If deploying on Streamlit Cloud, remember to add 'wkhtmltopdf' to packages.txt.") [cite: 54]
        st.stop() # Removed the extra `def` here, as this was likely the source of previous syntax error

def generate_dashboard_html(df, filters):
    """Generates the full HTML content of the dashboard for PDF conversion.""" [cite: 54]
    
    # Inline CSS for the PDF report [cite: 54]
    inline_css = """
    <style>
        body { font-family: sans-serif; margin: 20px; color: #333; } [cite: 55]
        .main-header {
            background: linear-gradient(90deg, #1f77b4, #2ca02c); [cite: 55]
            padding: 1rem; [cite: 56]
            border-radius: 10px; [cite: 56]
            margin-bottom: 2rem; [cite: 56]
            color: white; [cite: 56]
            text-align: center; [cite: 56]
        } [cite: 57]
        .kpi-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); [cite: 57]
            padding: 1rem; [cite: 58]
            border-radius: 10px; [cite: 58]
            margin: 0.5rem; /* Adjust margin for HTML export */ [cite: 58]
            color: white; [cite: 59]
            text-align: center; [cite: 59]
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); [cite: 59]
            display: inline-block; /* For side-by-side cards in PDF */ [cite: 59]
            width: 22%; [cite: 60]
            /* Adjust width for 4 cards in a row */ [cite: 60]
            vertical-align: top; [cite: 60]
        } [cite: 61]
        .kpi-value { font-size: 2rem; font-weight: bold; margin: 0.5rem 0; } [cite: 62]
        .department-section {
            border-left: 4px solid #1f77b4; [cite: 62]
            padding-left: 1rem; [cite: 63]
            margin: 1rem 0; [cite: 63]
            background-color: #f8f9fa; [cite: 63]
            border-radius: 0 10px 10px 0; [cite: 63]
        } [cite: 64]
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; } [cite: 65]
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; [cite: 65]
        vertical-align: middle; } [cite: 66]
        th { background-color: #f0f2f6; font-weight: bold; } [cite: 67]
        .plotly-chart-img { max-width: 100%; height: auto; display: block; margin: 1rem auto; } [cite: 68] /* Style for embedded chart images */
        hr { border: 0; [cite: 68]
        height: 1px; background-color: #ddd; margin: 2rem 0; } [cite: 69]
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
            <h1>🏥 Horus Hospital KPI Report</h1> [cite: 70]
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p> [cite: 70]
            <p>Filters: Year: {filters['year']}, Report Type: {filters['report_type']} [cite: 70]
            {f", Month: {filters['month']}" if filters['month'] else ""} [cite: 70]
            {f", Quarter: {filters['quarter']}" if filters['quarter'] else ""} [cite: 70]
            {f", Half: {filters['half']}" if filters['half'] else ""} [cite: 70]
            {f", Department: {filters['department']}" if filters['department'] != "All Departments" else ""} [cite: 71]
            </p>
        </div>
    """

    report_df = apply_filters(df, filters) [cite: 71]

    if report_df.empty: [cite: 71]
        html_content += "<p>No data available for selected filters.</p>" [cite: 71]
        return html_content + "</body></html>" [cite: 71]

    # Add summary cards to HTML for PDF [cite: 71]
    html_content += get_summary_cards_html_for_pdf(df, filters) [cite: 71]


    for dept in sorted(report_df['department'].dropna().unique()): [cite: 72]
        html_content += f"""
        <div class="department-section">
            <h2>🏢 {dept} Department</h2>
        </div>
        """
        dept_df = report_df[report_df['department'] == dept]

        for kpi_data in dept_df[['kpi id', 'kpi name', 'grouping criteria']].drop_duplicates().values: [cite: 72]
            kpi_id, kpi_name, group_type = kpi_data [cite: 72]
            kpi_df = dept_df[dept_df['kpi id'] == kpi_id] [cite: 73]

            if group_type == "sum": [cite: 73]
                total_value = format_value(kpi_df['value'].sum(), group_type) [cite: 73]
            else:
                total_value = format_value(kpi_df['value'].mean(), group_type) [cite: 73]

            html_content += f"<h3>📊 {kpi_name} (Total: {total_value})</h3>" [cite: 73]

            # Create pivot table [cite: 74]
            pivot_result = create_pivot_table(kpi_df, filters['report_type'], group_type) [cite: 74]

            if isinstance(pivot_result, list): # Two attributes case [cite: 74]
                for attr1, attr1_total, pivot in pivot_result: [cite: 74]
                    html_content += f"<h4>{attr1} (Total: {attr1_total})</h4>" [cite: 74]
                    # Convert DataFrame to HTML table string [cite: 75]
                    html_content += pivot.to_html(index=False, float_format=lambda x: f"{int(x)}" if group_type == 'sum' else f"{x:.1f}") [cite: 75]
                    html_content += "<br>" [cite: 75]
            else: # Single or no attribute case [cite: 75]
                html_content += pivot_result.to_html(index=False, float_format=lambda x: f"{int(x)}" if group_type == 'sum' else f"{x:.1f}") [cite: 76]
                html_content += "<br>" [cite: 76]

            # Create chart figure and convert to base64 image for HTML [cite: 76]
            fig_for_pdf = create_chart(kpi_df, kpi_name, group_type) [cite: 76]
            if fig_for_pdf: [cite: 76]
                # Requires kaleido package [cite: 77] to export Plotly figures to image bytes [cite: 77]
                img_bytes = fig_for_pdf.to_image(format="png", engine="kaleido") [cite: 77]
                encoded_img = base64.b64encode(img_bytes).decode('utf-8') [cite: 77]
                html_content += f'<img src="data:image/png;base64,{encoded_img}" class="plotly-chart-img">' [cite: 77]
            
            html_content += "<hr>" # Separator for better readability [cite: 77]

    html_content += "</body></html>" [cite: 78]
    return html_content

# Main application logic
if uploaded_file: [cite: 78]
    try: [cite: 78]
        # Load and validate data [cite: 78]
        df = pd.read_excel(uploaded_file) [cite: 78]
        df = df.replace({np.nan: None}) [cite: 78]
        
        if not validate_data(df): [cite: 79]
            st.stop()
        
        # Clean data [cite: 79]
        df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0) [cite: 79]
        df = df.dropna(subset=['kpi id', 'kpi name', 'department']) [cite: 79]
        
        st.success(f"✅ Data loaded successfully! Found {len(df)} records with {df['kpi id'].nunique()} unique KPIs.") [cite: 80]
        
        # Create tabs [cite: 80]
        tabs = st.tabs(["📊 Dashboard", "🔍 KPI Comparison"]) [cite: 80]
        
        with tabs[0]: [cite: 80]
            # Dashboard tab [cite: 80]
            st.header("📊 KPI Dashboard") [cite: 80]
            
            # Filter controls [cite: 81]
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2]) [cite: 81]
            
            with col1: [cite: 81]
                report_type = st.selectbox("Report Type", ["Monthly", "Quarter", "Half Annual", "Annual"]) [cite: 81]
            
            with col2: [cite: 82]
                selected_year = st.selectbox("Year", sorted(df['year'].dropna().unique(), reverse=True)) [cite: 82]
            
            with col5: [cite: 82]
                departments = ["All Departments"] + sorted(df['department'].dropna().unique().tolist()) [cite: 82]
                selected_department = st.selectbox("Department", departments) [cite: 82]
            
            # Dynamic filter based on report type [cite: 83]
            selected_month = selected_quarter = selected_half = None [cite: 83]
            
            if report_type == "Monthly": [cite: 83]
                with col3: [cite: 83]
                    available_months = sorted(df[df['year'] == selected_year]['month'].dropna().unique(),
                                              key=lambda x: MONTH_ORDER.index(x) if x in MONTH_ORDER else 999) [cite: 84]
                    selected_month = st.selectbox("Month", available_months) [cite: 84]
            elif report_type == "Quarter": [cite: 84]
                with col3: [cite: 85]
                    available_quarters = sorted(df[df['year'] == selected_year]['quarter'].dropna().unique()) [cite: 85]
                    selected_quarter = st.selectbox("Quarter", available_quarters) [cite: 85]
            elif report_type == "Half Annual": [cite: 85]
                with col3: [cite: 86]
                    selected_half = st.selectbox("Half", ["H1", "H2"]) [cite: 86]
            
            # Create filters dictionary [cite: 86]
            filters = {
                'report_type': report_type, [cite: 87]
                'year': selected_year, [cite: 87]
                'month': selected_month, [cite: 87]
                'quarter': selected_quarter, [cite: 87]
                'half': selected_half, [cite: 87]
                'department': selected_department [cite: 87]
            }
            
            # Use a session state variable to store if dashboard is generated [cite: 88]
            if 'dashboard_generated' not in st.session_state: [cite: 88]
                st.session_state.dashboard_generated = False [cite: 88]
            
            generate_button = st.button("🔄 Generate Dashboard", type="primary") [cite: 88]

            if generate_button or st.session_state.dashboard_generated: [cite: 88]
                st.session_state.dashboard_generated = True # Mark as generated [cite: 89]
                with st.spinner("Generating dashboard..."): [cite: 89]
                    report_df = apply_filters(df, filters) [cite: 89]
                    
                    if report_df.empty: [cite: 89]
                        st.warning("⚠️ No data available for selected filters.") [cite: 90]
                        st.session_state.dashboard_generated = False # Reset if no data [cite: 90]
                    else:
                        st.success(f"📈 Dashboard generated with {len(report_df)} records") [cite: 91]
                        
                        # Display summary cards in Streamlit - COMMENTED OUT THIS CALL TO REMOVE FROM UI
                        # display_summary_cards_streamlit(df, filters) 
                   
                        # Department overview [cite: 92]
                        for dept in sorted(report_df['department'].dropna().unique()): [cite: 92]
                            with st.container(): [cite: 92]
                                st.markdown(f"""
                                    <div class="department-section">
                                        <h3>🏢 {dept} Department</h3> [cite: 93]
                                    </div>
                                """, unsafe_allow_html=True) [cite: 94]
                                
                                dept_df = report_df[report_df['department'] == dept] [cite: 95]
                                
                                # Show KPIs for this department [cite: 96]
                                for kpi_data in dept_df[['kpi id', 'kpi name', 'grouping criteria']].drop_duplicates().values: [cite: 96]
                                    kpi_id, kpi_name, group_type = kpi_data [cite: 96]
                                    kpi_df = dept_df[dept_df['kpi id'] == kpi_id] [cite: 97]
                                    
                                    # Calculate total [cite: 97] for display [cite: 98]
                                    if group_type == "sum": [cite: 98]
                                        total_value = format_value(kpi_df['value'].sum(), group_type) [cite: 98]
                                    else: [cite: 99]
                                        total_value = format_value(kpi_df['value'].mean(), group_type) [cite: 99]
                                    
                                    with st.expander(f"📊 {kpi_name} (Total: {total_value})", expanded=True): [cite: 100]
                                        # Create pivot table [cite: 100]
                                        pivot_result = create_pivot_table(kpi_df, report_type, group_type) [cite: 101]
                                        
                                        if isinstance(pivot_result, list): [cite: 101] # Two attributes case [cite: 102]
                                            for attr1, attr1_total, pivot in pivot_result: [cite: 103]
                                                st.markdown(f"**{attr1} (Total: {attr1_total})**") [cite: 103]
                                                
                                                column_config = {} [cite: 104]
                                                for col in pivot.columns: [cite: 105]
                                                    if col != pivot.columns[0]: [cite: 105]
                                                        column_config[col] = st.column_config.NumberColumn( [cite: 106]
                                                            col, format="%d" if pivot[col].dtype == 'int64' else "%.1f" [cite: 106]
                                                        ) [cite: 107]
                                                    else: [cite: 107]
                                                        column_config[col] = st.column_config.TextColumn(col) [cite: 108]
                                                
                                                st.dataframe( [cite: 109]
                                                    pivot, [cite: 109]
                                                    use_container_width=True, [cite: 110]
                                                    hide_index=True, [cite: 111]
                                                    column_config=column_config [cite: 111]
                                                ) [cite: 112]
                                        else: [cite: 112]
                                            # Single or no attribute case [cite: 112]
                                            column_config = {} [cite: 113]
                                            for col in pivot_result.columns: [cite: 113]
                                                if col != pivot_result.columns[0]: [cite: 114]
                                                    column_config[col] = st.column_config.NumberColumn( [cite: 114]
                                                        col, format="%d" if pivot_result[col].dtype == 'int64' else "%.1f" [cite: 115]
                                                    ) [cite: 116]
                                                else: [cite: 116]
                                                    column_config[col] = st.column_config.TextColumn(col) [cite: 117]
                                            
                                            st.dataframe( [cite: 117]
                                                pivot_result, [cite: 118]
                                                use_container_width=True, [cite: 118]
                                                hide_index=True, [cite: 119]
                                                column_config=column_config [cite: 119]
                                            ) [cite: 120]
                                        
                                        # Create chart for Streamlit display [cite: 121]
                                        fig_to_display = create_chart(kpi_df, kpi_name, group_type) [cite: 121]
                                        
                                        if fig_to_display: [cite: 122]
                                            st.plotly_chart(fig_to_display, use_container_width=True) [cite: 122]
                        
                        # Add a download button for PDF report [cite: 123]
                        st.markdown("---") # Separator before download button [cite: 123]
                        st.subheader("⬇️ Download Report") [cite: 123]
                        
                        # Generate the full HTML content for the PDF report [cite: 124]
                        pdf_html = generate_dashboard_html(df, filters) [cite: 124]
                        
                        # Get pdfkit configuration [cite: 125]
                        wkhtmltopdf_config = get_pdfkit_config() [cite: 125]
                        
                        try: [cite: 126]
                            # Generate PDF from HTML string [cite: 126]
                            pdf_bytes = pdfkit.from_string(pdf_html, False, configuration=wkhtmltopdf_config) [cite: 126]
                            
                            st.download_button( [cite: 127]
                                label="Download Dashboard as PDF", [cite: 127]
                                data=pdf_bytes, [cite: 127]
                                file_name=f"Horus_Hospital_KPI_Report_{filters['year']}_{filters['report_type']}.pdf", [cite: 128]
                                mime="application/pdf", [cite: 128]
                                help="Download the currently displayed dashboard as a PDF file." [cite: 129]
                            )
                        except Exception as e: [cite: 129]
                            st.error(f"Failed to generate PDF. Please ensure wkhtmltopdf is correctly installed and configured. Error: {e}") [cite: 130]
                            st.info("Check the console/logs for more details, especially regarding wkhtmltopdf path.") [cite: 130]

        with tabs[1]: [cite: 130]
            st.header("🔍 KPI Comparison") [cite: 131]
            st.info("🚧 KPI comparison tools coming soon!") [cite: 131]
            
    except Exception as e: [cite: 131]
        st.error(f"❌ Error processing file: {str(e)}") [cite: 131]
        st.info("Please check your file format and try again.") [cite: 131]

else: [cite: 131]
    # Show sample data structure only [cite: 131]
    st.subheader("📋 Sample Data Structure") [cite: 131]
    sample_data = pd.DataFrame({
        'kpi id': ['KPI001', 'KPI001', 'KPI002'], [cite: 131]
        'kpi name': ['Patient Satisfaction', 'Patient Satisfaction', 'Average Wait Time'], [cite: 132]
        'attribute 1': ['Outpatient', 'Inpatient', 'Emergency'], [cite: 132]
        'attribute 2': ['Cardiology', 'Surgery', 'Triage'], [cite: 132]
        'grouping criteria': ['average', 'average', 'average'], [cite: 132]
        'value': [4.5, 4.8, 25.5], [cite: 132]
        'month': ['January', 'January', 'January'], [cite: 132]
        'quarter': ['Q1', 'Q1', 'Q1'], [cite: 132]
        'year': [2024, 2024, 2024], [cite: 132]
        'department': ['Cardiology', 'Surgery', 'Emergency'] [cite: 132]
    })
    
    st.dataframe(sample_data, use_container_width=True) [cite: 132]
