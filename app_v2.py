import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

# PDF export dependencies
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# Page config
st.set_page_config(page_title="Horus Hospital KPIs", layout="wide", initial_sidebar_state="expanded")

# Enhanced CSS styling
st.markdown(""" ... CSS STYLES HERE (truncated to save space) ... """, unsafe_allow_html=True)

# Main header
st.markdown("""
    <div class="main-header">
        <h1>🏥 Horus Hospital KPI Dashboard</h1>
        <p>Comprehensive Healthcare Performance Analytics</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("### 📁 Upload KPI Data")
uploaded_file = st.sidebar.file_uploader("Upload your Excel file (.xlsx)", type=["xlsx"])
with st.sidebar.expander("📋 Required Excel Format", expanded=False):
    st.markdown(""" ... (columns explanation) ... """)

# Constants
MONTH_ORDER = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]
QUARTER_MONTHS = {
    'Q1': ['January', 'February', 'March'],
    'Q2': ['April', 'May', 'June'],
    'Q3': ['July', 'August', 'September'],
    'Q4': ['October', 'November', 'December']
}

# Utility Functions
def validate_data(df):
    required_columns = ['kpi id', 'kpi name', 'attribute 1', 'attribute 2', 
                        'grouping criteria', 'value', 'month', 'quarter', 'year', 'department']
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return False
    if not pd.api.types.is_numeric_dtype(df['value']):
        st.error("'value' column must be numeric")
        return False
    return True

def format_value(value, group_type):
    return int(value) if group_type == 'sum' else round(float(value), 1)

def apply_filters(df, filters):
    df_filtered = df.copy()
    if filters['year']:
        df_filtered = df_filtered[df_filtered['year'] == filters['year']]
    if filters['report_type'] == "Monthly" and filters['month']:
        df_filtered = df_filtered[df_filtered['month'] == filters['month']]
    elif filters['report_type'] == "Quarter" and filters['quarter']:
        df_filtered = df_filtered[df_filtered['month'].isin(QUARTER_MONTHS.get(filters['quarter'], []))]
    elif filters['report_type'] == "Half Annual" and filters['half']:
        if filters['half'] == "H1":
            df_filtered = df_filtered[df_filtered['month'].isin(MONTH_ORDER[:6])]
        else:
            df_filtered = df_filtered[df_filtered['month'].isin(MONTH_ORDER[6:])]
    if filters.get('department') and filters['department'] != "All Departments":
        df_filtered = df_filtered[df_filtered['department'] == filters['department']]
    return df_filtered

def convert_df_to_excel(df, sheet_name="Report"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()

def generate_pdf_report(df, title="Horus KPI Report"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 12))
    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.black),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(table)
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# Main app logic
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df = df.replace({np.nan: None})
        if not validate_data(df):
            st.stop()
        df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
        df = df.dropna(subset=['kpi id', 'kpi name', 'department'])
        st.success(f"✅ Data loaded successfully! Found {len(df)} records with {df['kpi id'].nunique()} unique KPIs.")

        tabs = st.tabs(["📊 Dashboard", "🔍 KPI Comparison"])

        with tabs[0]:
            st.header("📊 KPI Dashboard")
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])
            with col1:
                report_type = st.selectbox("Report Type", ["Monthly", "Quarter", "Half Annual", "Annual"])
            with col2:
                selected_year = st.selectbox("Year", sorted(df['year'].dropna().unique(), reverse=True))
            with col5:
                departments = ["All Departments"] + sorted(df['department'].dropna().unique().tolist())
                selected_department = st.selectbox("Department", departments)

            selected_month = selected_quarter = selected_half = None
            if report_type == "Monthly":
                with col3:
                    months = sorted(df[df['year'] == selected_year]['month'].dropna().unique(),
                                    key=lambda x: MONTH_ORDER.index(x) if x in MONTH_ORDER else 999)
                    selected_month = st.selectbox("Month", months)
            elif report_type == "Quarter":
                with col3:
                    quarters = sorted(df[df['year'] == selected_year]['quarter'].dropna().unique())
                    selected_quarter = st.selectbox("Quarter", quarters)
            elif report_type == "Half Annual":
                with col3:
                    selected_half = st.selectbox("Half", ["H1", "H2"])

            filters = {
                'report_type': report_type,
                'year': selected_year,
                'month': selected_month,
                'quarter': selected_quarter,
                'half': selected_half,
                'department': selected_department
            }

            if st.button("🔄 Generate Dashboard", type="primary"):
                with st.spinner("Generating dashboard..."):
                    report_df = apply_filters(df, filters)
                    if report_df.empty:
                        st.warning("⚠️ No data available for selected filters.")
                    else:
                        st.success(f"📈 Dashboard generated with {len(report_df)} records")

                        # PDF download
                        pdf_data = generate_pdf_report(report_df)
                        st.download_button(
                            label="📄 Download KPI Report as PDF",
                            data=pdf_data,
                            file_name=f"horus_kpi_report_{filters['year']}_{filters.get('month') or filters.get('quarter') or filters.get('half') or 'All'}.pdf",
                            mime="application/pdf"
                        )

                        # Render your KPI sections here
                        # (KPI cards, departments, charts, tables, etc. — unchanged from your code)

        with tabs[1]:
            st.header("🔍 KPI Comparison")
            st.info("🚧 KPI comparison tools coming soon!")

    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
else:
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
