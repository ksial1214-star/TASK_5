# app.py
import os
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# ---------- Page config ----------
st.set_page_config(
    page_title="Global Superstore BI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Custom CSS for styling ----------
st.markdown("""
    <style>
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(135deg, #1f2937, #4b5563);
            color: white;
        }
        [data-testid="stSidebar"] h1, h2, h3, h4, h5, h6, label {
            color: #f3f4f6 !important;
        }

        /* KPI metric cards */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #2563eb, #3b82f6);
            color: white;
            border-radius: 15px;
            padding: 15px;
            text-align: center;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
        }

        /* Titles */
        h1, h2, h3 {
            color: #1f2937;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Global Superstore — Interactive Dashboard")

# ---------- Settings ----------
DATA_PATH = Path("data/Global_Superstore.csv")
EXPECTED_COLS = [
    "Row ID","Order ID","Order Date","Ship Date","Ship Mode","Customer ID","Customer Name",
    "Segment","Country","City","State","Postal Code","Region","Product ID","Category",
    "Sub-Category","Product Name","Sales","Quantity","Discount","Profit"
]

# ---------- Helpers ----------
@st.cache_data(show_spinner=False)
def load_data(file: Path | None, uploaded_file=None) -> pd.DataFrame:
    if uploaded_file is not None:
        name = uploaded_file.name.lower()
        if name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(uploaded_file, engine="openpyxl")
        else:
            df = pd.read_csv(uploaded_file, encoding="utf-8", errors="replace")
    else:
        if not file.exists():
            raise FileNotFoundError(f"Dataset not found: {file}")
        if str(file).lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(file, engine="openpyxl")
        else:
            df = pd.read_csv(file, encoding="latin-1")


    df.columns = [c.strip() for c in df.columns]
    missing = [c for c in EXPECTED_COLS if c not in df.columns]
    if missing:
        st.warning(f"⚠️ Missing columns: {missing}")
    return df


def smart_parse_datetime(series: pd.Series) -> pd.Series:
    s1 = pd.to_datetime(series, errors="coerce", infer_datetime_format=True, dayfirst=False)
    if s1.isna().mean() > 0.5:
        s1 = pd.to_datetime(series, errors="coerce", infer_datetime_format=True, dayfirst=True)
    return s1


@st.cache_data(show_spinner=False)
def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["Order Date", "Ship Date"]:
        if col in df.columns:
            df[col] = smart_parse_datetime(df[col])
        else:
            st.error(f"❌ Missing column '{col}'")
            st.stop()

    for col in ["Sales", "Profit", "Discount", "Quantity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Order Date", "Sales", "Profit"])
    df["Order Date (Date)"] = df["Order Date"].dt.date
    return df


def apply_filters(df: pd.DataFrame, region_sel, category_sel, subcat_sel) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if region_sel:
        mask &= df["Region"].isin(region_sel)
    if category_sel:
        mask &= df["Category"].isin(category_sel)
    if subcat_sel:
        mask &= df["Sub-Category"].isin(subcat_sel)
    return df[mask]


def kpi_card(label, value, delta=None):
    st.metric(label, value, delta=delta)


# ---------- Data ----------
st.sidebar.header("📁 Data")
uploaded = st.sidebar.file_uploader("Upload CSV/XLSX", type=["csv", "xlsx", "xls"])
try:
    df_raw = load_data(DATA_PATH, uploaded_file=uploaded) if uploaded else load_data(DATA_PATH)
except FileNotFoundError:
    st.info("📂 Upload dataset in the sidebar.")
    st.stop()

df = preprocess(df_raw)

# ---------- Sidebar filters ----------
st.sidebar.header("🔎 Filters")
regions = sorted(df["Region"].dropna().unique()) if "Region" in df.columns else []
cats    = sorted(df["Category"].dropna().unique()) if "Category" in df.columns else []
subcats = sorted(df["Sub-Category"].dropna().unique()) if "Sub-Category" in df.columns else []

region_sel = st.sidebar.multiselect("🌍 Region", regions, default=regions)
cat_sel    = st.sidebar.multiselect("📦 Category", cats, default=cats)
subcat_sel = st.sidebar.multiselect("🛒 Sub-Category", subcats, default=subcats)

df_f = apply_filters(df, region_sel, cat_sel, subcat_sel)

# ---------- KPIs ----------
total_sales  = float(df_f["Sales"].sum()) if "Sales" in df_f.columns else 0.0
total_profit = float(df_f["Profit"].sum()) if "Profit" in df_f.columns else 0.0
margin = (total_profit / total_sales * 100) if total_sales != 0 else 0.0

col1, col2, col3 = st.columns(3)
with col1:
    kpi_card("💰 Total Sales", f"${total_sales:,.2f}")
with col2:
    kpi_card("📈 Total Profit", f"${total_profit:,.2f}")
with col3:
    kpi_card("📊 Profit Margin", f"{margin:.2f}%")

st.divider()

# ---------- Charts ----------
c1, c2 = st.columns(2)
with c1:
    st.subheader("🌍 Sales by Region")
    if "Region" in df_f.columns:
        g = df_f.groupby("Region", as_index=False)["Sales"].sum().sort_values("Sales", ascending=False)
        fig = px.bar(g, x="Region", y="Sales", text_auto=".2s", color="Sales", color_continuous_scale="Blues")
        fig.update_layout(yaxis_title=None, xaxis_title=None, plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("📦 Profit by Category")
    if "Category" in df_f.columns:
        g = df_f.groupby("Category", as_index=False)["Profit"].sum().sort_values("Profit", ascending=False)
        fig = px.bar(g, x="Category", y="Profit", text_auto=".2s", color="Profit", color_continuous_scale="Viridis")
        fig.update_layout(yaxis_title=None, xaxis_title=None, plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    st.subheader("📅 Sales Over Time")
    ts = df_f.groupby("Order Date (Date)", as_index=False)["Sales"].sum().rename(columns={"Order Date (Date)": "Date"})
    if not ts.empty:
        fig = px.area(ts, x="Date", y="Sales", color_discrete_sequence=["#3b82f6"])
        fig.update_layout(yaxis_title=None, xaxis_title=None, plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

with c4:
    st.subheader("🏆 Top 5 Customers")
    if "Customer Name" in df_f.columns:
        top5 = df_f.groupby("Customer Name", as_index=False)["Sales"].sum().nlargest(5, "Sales")
        fig = px.bar(top5, x="Customer Name", y="Sales", text_auto=".2s", color="Sales", color_continuous_scale="Plasma")
        fig.update_layout(yaxis_title=None, xaxis_title=None, plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("🔍 See table"):
            st.dataframe(top5, use_container_width=True)

st.subheader("🛒 Sub-Category Performance")
if "Sub-Category" in df_f.columns:
    subperf = df_f.groupby("Sub-Category", as_index=False).agg(Sales=("Sales","sum"), Profit=("Profit","sum"))
    subperf = subperf.sort_values("Sales", ascending=False)
    fig = px.bar(subperf, x="Sub-Category", y="Sales", color="Profit", text_auto=".2s", color_continuous_scale="RdYlGn")
    fig.update_layout(yaxis_title=None, xaxis_title=None, plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("⬇ Download Data"):
        csv = df_f.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "filtered_data.csv", "text/csv")

with st.expander("📄 Raw Data Preview"):
    st.dataframe(df_f.head(50), use_container_width=True)
