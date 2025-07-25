import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from weasyprint import HTML
import base64
from io import BytesIO
import plotly.io as pio

# Page config
st.set_page_config(page_title="Horus Hospital KPIs", layout="wide", initial_sidebar_state="expanded")

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
    required_columns = ['kpi id', 'kpi name', 'attribute 1', 'attribute 2', 
                        'grouping criteria', 'value', 'month', 'quarter', 'year', 'department']
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.error(f"Missing columns: {', '.join(missing)}")
        return False
    return True

def format_value(value, group_type):
    return int(value) if group_type == 'sum' else round(float(value), 1)

def apply_filters(df, filters):
    df = df[df['year'] == filters['year']]
    if filters['report_type'] == "Monthly" and filters['month']:
        df = df[df['month'] == filters['month']]
    elif filters['report_type'] == "Quarter" and filters['quarter']:
        df = df[df['month'].isin(QUARTER_MONTHS[filters['quarter']])]
    elif filters['report_type'] == "Half Annual" and filters['half']:
        df = df[df['month'].isin(MONTH_ORDER[:6] if filters['half'] == 'H1' else MONTH_ORDER[6:])]
    if filters['department'] != "All Departments":
        df = df[df['department'] == filters['department']]
    return df

def create_pivot_table(kpi_df, report_type, group_type):
    aggfunc = 'sum' if group_type == 'sum' else 'mean'
    attr1, attr2 = kpi_df['attribute 1'], kpi_df['attribute 2']

    if attr1.notna().any() and attr1.ne("").any() and attr2.notna().any() and attr2.ne("").any():
        results = []
        for a1 in sorted(attr1.dropna().unique()):
            sub_df = kpi_df[attr1 == a1]
            pivot = pd.pivot_table(sub_df, index='attribute 2', columns='month', values='value',
                                   aggfunc=aggfunc, fill_value=0)
            available = [m for m in MONTH_ORDER if m in pivot.columns]
            pivot = pivot.reindex(columns=available)
            pivot['Total'] = pivot.sum(axis=1) if group_type == 'sum' else pivot.mean(axis=1)
            pivot = pivot.reset_index()
            for col in pivot.columns[1:]:
                pivot[col] = pivot[col].apply(lambda x: format_value(x, group_type))
            total = format_value(sub_df['value'].sum() if group_type == 'sum' else sub_df['value'].mean(), group_type)
            results.append((a1, total, pivot))
        return results
    else:
        index_attr = 'attribute 1' if attr1.notna().any() and attr1.ne("").any() else 'attribute 2'
        if index_attr not in kpi_df.columns:
            pivot = pd.DataFrame({'Total': [format_value(kpi_df['value'].sum() if group_type == 'sum' else kpi_df['value'].mean(), group_type)]})
        else:
            pivot = pd.pivot_table(kpi_df, index=index_attr, columns='month', values='value',
                                   aggfunc=aggfunc, fill_value=0)
            available = [m for m in MONTH_ORDER if m in pivot.columns]
            pivot = pivot.reindex(columns=available)
            pivot['Total'] = pivot.sum(axis=1) if group_type == 'sum' else pivot.mean(axis=1)
            pivot = pivot.reset_index()
            for col in pivot.columns[1:]:
                pivot[col] = pivot[col].apply(lambda x: format_value(x, group_type))
        return pivot

def create_chart(kpi_df, kpi_name, group_type):
    aggfunc = 'sum' if group_type == 'sum' else 'mean'
    attr1, attr2 = kpi_df['attribute 1'], kpi_df['attribute 2']

    if attr1.notna().any() and attr2.notna().any():
        df = kpi_df.groupby(['attribute 1', 'attribute 2'])['value'].agg(aggfunc).reset_index()
        fig = px.bar(df, x='attribute 1', y='value', color='attribute 2', barmode='group')
    elif attr1.notna().any():
        df = kpi_df.groupby('attribute 1')['value'].agg(aggfunc).reset_index()
        fig = px.bar(df, x='attribute 1', y='value', color='value', color_continuous_scale='viridis')
    elif attr2.notna().any():
        df = kpi_df.groupby('attribute 2')['value'].agg(aggfunc).reset_index()
        fig = px.bar(df, x='attribute 2', y='value', color='value', color_continuous_scale='viridis')
    else:
        if len(kpi_df['month'].unique()) > 1:
            df = kpi_df.groupby('month')['value'].agg(aggfunc).reset_index()
            df['month_num'] = df['month'].map({m: i for i, m in enumerate(MONTH_ORDER)})
            df = df.sort_values('month_num')
            fig = px.line(df, x='month', y='value', markers=True)
        else:
            return None
    fig.update_layout(height=400, margin=dict(t=40, b=40))
    return fig

def plotly_fig_to_base64(fig):
    img_bytes = fig.to_image(format="png", width=900, height=500, engine="kaleido")
    return base64.b64encode(img_bytes).decode()

def generate_html_report(report_df, filters):
    html = f"""
    <html><head><meta charset='utf-8'><style>
    body {{ font-family: Arial; margin: 20px; }}
    h1, h2, h3 {{ color: #1f77b4; }}
    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
    th, td {{ border: 1px solid #ccc; padding: 6px; text-align: center; }}
    </style></head><body>
    <h1>🏥 Horus Hospital KPI Report</h1>
    <p><b>Report Type:</b> {filters['report_type']} | <b>Year:</b> {filters['year']} | <b>Department:</b> {filters['department']}</p><hr>
    """
    for dept in sorted(report_df['department'].dropna().unique()):
        dept_df = report_df[report_df['department'] == dept]
        html += f"<h2>🏢 {dept} Department</h2>"
        for kpi_id, kpi_name, group_type in dept_df[['kpi id', 'kpi name', 'grouping criteria']].drop_duplicates().values:
            kpi_df = dept_df[dept_df['kpi id'] == kpi_id]
            pivot_result = create_pivot_table(kpi_df, filters['report_type'], group_type)
            chart = create_chart(kpi_df, kpi_name, group_type)
            html += f"<h3>📊 {kpi_name}</h3>"
            if isinstance(pivot_result, list):
                for attr1, attr1_total, pivot in pivot_result:
                    html += f"<h4>{attr1} (Total: {attr1_total})</h4>"
                    html += pivot.to_html(index=False, border=1)
            else:
                html += pivot_result.to_html(index=False, border=1)
            if chart:
                chart_base64 = plotly_fig_to_base64(chart)
                html += f'<img src="data:image/png;base64,{chart_base64}" style="width:100%;max-width:900px;margin:20px 0;">'
    html += "</body></html>"
    return html

def download_pdf_button(report_df, filters):
    html_str = generate_html_report(report_df, filters)
    try:
        pdf_bytes = HTML(string=html_str).write_pdf()
        st.download_button("📥 Download KPI Report as PDF", data=pdf_bytes, file_name="kpi_report.pdf", mime="application/pdf")
    except Exception as e:
        st.error("❌ Error generating PDF.")
        st.exception(e)

# --- Streamlit App ---
st.sidebar.header("📁 Upload KPI Data")
uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
    df = df.dropna(subset=['kpi id', 'kpi name', 'department'])
    if not validate_data(df):
        st.stop()

    st.success(f"✅ Loaded {len(df)} records | {df['kpi id'].nunique()} unique KPIs")
    report_type = st.selectbox("Report Type", ["Monthly", "Quarter", "Half Annual", "Annual"])
    year = st.selectbox("Year", sorted(df['year'].dropna().unique(), reverse=True))
    department = st.selectbox("Department", ["All Departments"] + sorted(df['department'].dropna().unique()))
    month = quarter = half = None
    if report_type == "Monthly":
        month = st.selectbox("Month", sorted(df[df['year'] == year]['month'].dropna().unique(), key=lambda x: MONTH_ORDER.index(x)))
    elif report_type == "Quarter":
        quarter = st.selectbox("Quarter", sorted(df[df['year'] == year]['quarter'].dropna().unique()))
    elif report_type == "Half Annual":
        half = st.selectbox("Half", ["H1", "H2"])

    filters = {
        'report_type': report_type,
        'year': year,
        'month': month,
        'quarter': quarter,
        'half': half,
        'department': department
    }

    if st.button("🔄 Generate Dashboard"):
        report_df = apply_filters(df, filters)
        if report_df.empty:
            st.warning("⚠️ No data for selected filters.")
        else:
            st.success(f"📈 Showing {len(report_df)} filtered records")
            download_pdf_button(report_df, filters)
else:
    st.info("📄 Upload a KPI Excel file to begin.")

