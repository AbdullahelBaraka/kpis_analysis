# --- Horus Hospital KPI Dashboard with PDF Export ---

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import base64
import io
from xhtml2pdf import pisa
from datetime import datetime

# Page Config
st.set_page_config(page_title="Horus Hospital KPIs", layout="wide")

# --- Styling ---
st.markdown("""
    <style>
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
            margin: 0.5rem 0;
            color: white;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .kpi-value {
            font-size: 2rem;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("""
    <div class="main-header">
        <h1>🏥 Horus Hospital KPI Dashboard</h1>
        <p>Comprehensive Healthcare Performance Analytics</p>
    </div>
""", unsafe_allow_html=True)

# --- File Upload ---
st.sidebar.header("📁 Upload KPI Data")
uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])

# --- Load Data ---
@st.cache_data

def load_data(file):
    if file:
        df = pd.read_excel(file)
        df.columns = [c.strip().lower() for c in df.columns]
        return df.replace({np.nan: None})
    return pd.DataFrame()

# --- Validate Data ---
def validate_data(df):
    required = ['kpi id', 'kpi name', 'attribute 1', 'attribute 2', 'grouping criteria',
                'value', 'month', 'quarter', 'year', 'department']
    missing = [col for col in required if col not in df.columns]
    if missing:
        st.error(f"Missing columns: {', '.join(missing)}")
        return False
    return pd.api.types.is_numeric_dtype(df['value'])

# --- Utility Functions ---
MONTH_ORDER = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]

def apply_filters(df, year, month, quarter, half, report_type, dept):
    df = df[df['year'] == year]
    if report_type == "Monthly" and month:
        df = df[df['month'] == month]
    elif report_type == "Quarter" and quarter:
        quarters = {
            'Q1': ['January', 'February', 'March'],
            'Q2': ['April', 'May', 'June'],
            'Q3': ['July', 'August', 'September'],
            'Q4': ['October', 'November', 'December']
        }
        df = df[df['month'].isin(quarters.get(quarter, []))]
    elif report_type == "Half Annual" and half:
        df = df[df['month'].isin(MONTH_ORDER[:6] if half == 'H1' else MONTH_ORDER[6:])]
    if dept and dept != "All":
        df = df[df['department'] == dept]
    return df

def format_value(val, group):
    return int(val) if group == 'sum' else round(float(val), 1)

def generate_chart(df):
    if df.empty:
        return None
    chart_df = df.groupby(['department', 'kpi name'])['value'].sum().reset_index()
    fig = px.bar(chart_df, x='department', y='value', color='kpi name', barmode='group')
    fig.update_layout(title="KPI Summary by Department")
    return fig

# --- PDF Generation ---
def plotly_fig_to_base64(fig):
    try:
        img_bytes = fig.to_image(format="png", engine="kaleido")
        return base64.b64encode(img_bytes).decode("utf-8")
    except:
        return ""

def convert_html_to_pdf(source_html):
    pdf_buffer = io.BytesIO()
    pisa.CreatePDF(io.StringIO(source_html), dest=pdf_buffer)
    return pdf_buffer.getvalue()

def generate_html_report(df, chart):
    html = f"""
    <html><body><h1>Horus KPI Report - {datetime.now().strftime('%Y-%m-%d')}</h1>
    """
    if chart:
        img = plotly_fig_to_base64(chart)
        html += f'<img src="data:image/png;base64,{img}" width="800"/>'

    html += "<table border='1' cellspacing='0' cellpadding='5'>"
    html += "<tr>" + "".join(f"<th>{col}</th>" for col in df.columns) + "</tr>"
    for _, row in df.iterrows():
        html += "<tr>" + "".join(f"<td>{val}</td>" for val in row) + "</tr>"
    html += "</table></body></html>"
    return html

def download_pdf_button(df):
    chart = generate_chart(df)
    html = generate_html_report(df, chart)
    pdf = convert_html_to_pdf(html)
    b64 = base64.b64encode(pdf).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="kpi_report.pdf">📄 Download PDF</a>'
    st.markdown(href, unsafe_allow_html=True)

# --- Main App ---
df = load_data(uploaded_file)

if not df.empty and validate_data(df):
    st.success("✅ Data validated successfully")

    st.sidebar.header("🔎 Filters")
    report_type = st.sidebar.selectbox("Report Type", ["Monthly", "Quarter", "Half Annual", "Annual"])
    year = st.sidebar.selectbox("Year", sorted(df['year'].dropna().unique(), reverse=True))
    department = st.sidebar.selectbox("Department", ["All"] + sorted(df['department'].dropna().unique()))

    month = quarter = half = None
    if report_type == "Monthly":
        month = st.sidebar.selectbox("Month", MONTH_ORDER)
    elif report_type == "Quarter":
        quarter = st.sidebar.selectbox("Quarter", ["Q1", "Q2", "Q3", "Q4"])
    elif report_type == "Half Annual":
        half = st.sidebar.selectbox("Half", ["H1", "H2"])

    filtered_df = apply_filters(df, year, month, quarter, half, report_type, department)

    # KPI Cards
    if not filtered_df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""<div class='kpi-card'><h4>Total KPIs</h4><div class='kpi-value'>{filtered_df['kpi id'].nunique()}</div></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class='kpi-card'><h4>Departments</h4><div class='kpi-value'>{filtered_df['department'].nunique()}</div></div>""", unsafe_allow_html=True)
        with col3:
            avg_val = filtered_df['value'].mean()
            st.markdown(f"""<div class='kpi-card'><h4>Average Value</h4><div class='kpi-value'>{format_value(avg_val, 'average')}</div></div>""", unsafe_allow_html=True)

        st.divider()
        st.subheader("📊 KPI Chart")
        fig = generate_chart(filtered_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 KPI Data")
        st.dataframe(filtered_df, use_container_width=True)

        st.subheader("⬇️ Export Report")
        download_pdf_button(filtered_df)

    else:
        st.warning("No data found for selected filters.")

elif uploaded_file:
    st.error("Failed to validate uploaded file. Check required columns and data types.")
else:
    st.info("Please upload an Excel file to begin.")
