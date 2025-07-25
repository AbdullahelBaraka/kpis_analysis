import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import io
from xhtml2pdf import pisa
from datetime import datetime

# ---------- KPI Data Loading & Preprocessing ----------
@st.cache_data
def load_data():
    df = pd.read_excel("kpi_data.xlsx")
    return df

def filter_data(df, filters):
    for key, value in filters.items():
        if value and value != "All":
            df = df[df[key] == value]
    return df

# ---------- Chart Generation ----------
def generate_chart(df):
    if df.empty:
        return None
    fig = px.bar(df, x="Department", y="KPI Value", color="KPI Name", barmode="group")
    fig.update_layout(title="KPI Report")
    return fig

# ---------- Chart to Base64 ----------
def plotly_fig_to_base64(fig):
    img_bytes = fig.to_image(format="png", width=900, height=500, engine="kaleido")
    return base64.b64encode(img_bytes).decode("utf-8")

# ---------- HTML to PDF using xhtml2pdf ----------
def convert_html_to_pdf(source_html):
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(source_html), dest=pdf_buffer)
    if pisa_status.err:
        return None
    return pdf_buffer.getvalue()

# ---------- Generate Report HTML ----------
def generate_html_report(df, filters, chart=None):
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial; }}
            h1 {{ text-align: center; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #333; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>KPI Report</h1>
        <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
        <p><strong>Filters Applied:</strong> {', '.join([f'{k}: {v}' for k, v in filters.items() if v])}</p>
    """
    if chart:
        try:
            chart_base64 = plotly_fig_to_base64(chart)
            html += f'<img src="data:image/png;base64,{chart_base64}" style="width:100%; max-height:500px;"/>'
        except Exception as e:
            html += f'<p><i>Chart rendering failed: {str(e)}</i></p>'

    html += "<table><thead><tr>"
    for col in df.columns:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr>" + "".join(f"<td>{val}</td>" for val in row) + "</tr>"
    html += "</tbody></table></body></html>"
    return html

# ---------- Download Button ----------
def download_pdf_button(df, filters):
    chart = generate_chart(df)
    html_str = generate_html_report(df, filters, chart)
    pdf = convert_html_to_pdf(html_str)
    if pdf:
        b64 = base64.b64encode(pdf).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="kpi_report.pdf">📄 Download PDF Report</a>'
        st.markdown(href, unsafe_allow_html=True)
    else:
        st.error("Failed to generate PDF.")

# ---------- Streamlit App ----------
st.set_page_config(page_title="KPI Dashboard", layout="wide")
st.title("📊 KPI Dashboard")

df = load_data()

# Filters
departments = ["All"] + sorted(df["Department"].dropna().unique())
kpis = ["All"] + sorted(df["KPI Name"].dropna().unique())

selected_department = st.sidebar.selectbox("Department", departments)
selected_kpi = st.sidebar.selectbox("KPI Name", kpis)

filters = {
    "Department": None if selected_department == "All" else selected_department,
    "KPI Name": None if selected_kpi == "All" else selected_kpi
}

filtered_df = filter_data(df, filters)

# Chart and Table
chart = generate_chart(filtered_df)
if chart:
    st.plotly_chart(chart, use_container_width=True)

st.dataframe(filtered_df)

# PDF Report
st.subheader("⬇️ Download Report")
download_pdf_button(filtered_df, filters)
