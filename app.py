import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="Amazon Supply Chain Management Dashboard",
    layout="wide"
)

st.title("📦 Amazon Supply Chain Management Dashboard")
st.markdown(
    "Upload the **amazon_supply_chain_data.csv** file to explore key KPIs and visual dashboards."
)

@st.cache_data
def load_data(file):
    # parse_dates ensures date columns are proper datetimes
    df = pd.read_csv(file, parse_dates=["order_date", "ship_date", "delivery_date"])
    return df


def kpi_section(df):
    df = df.copy()
    df["order_value"] = df["units_sold"] * df["unit_price"]
    df["total_cost"] = df["shipping_cost"] + df["fulfillment_cost"]
    df["profit"] = df["order_value"] - df["total_cost"]
    df["delivery_days"] = (df["delivery_date"] - df["ship_date"]).dt.days
    df["is_late"] = df["delivery_status"].eq("Late")

    total_orders = len(df)
    total_revenue = df["order_value"].sum()
    total_profit = df["profit"].sum()
    on_time_rate = 100 * (1 - df["is_late"].mean())
    avg_delivery_days = df["delivery_days"].mean()
    avg_fulfillment_cost = df["fulfillment_cost"].mean()

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Total Orders", f"{total_orders:,}")
    c2.metric("Total Revenue", f"${total_revenue:,.0f}")
    c3.metric("Total Profit", f"${total_profit:,.0f}")
    c4.metric("On-Time Delivery Rate", f"{on_time_rate:.1f}%")
    c5.metric("Avg Delivery Time (days)", f"{avg_delivery_days:.2f}")
    c6.metric("Avg Fulfillment Cost / Order", f"${avg_fulfillment_cost:.2f}")


def charts_section(df):
    df = df.copy()
    df["order_value"] = df["units_sold"] * df["unit_price"]
    df["delivery_days"] = (df["delivery_date"] - df["ship_date"]).dt.days

    st.subheader("📈 Time Series & Performance")

    # Orders & revenue over time
    orders_by_date = (
        df.groupby("order_date")
        .agg(
            orders=("order_id", "count"),
            revenue=("order_value", "sum")
        )
        .reset_index()
    )

    col1, col2 = st.columns(2)

    with col1:
        fig_orders = px.line(
            orders_by_date,
            x="order_date",
            y="orders",
            title="Orders Over Time"
        )
        st.plotly_chart(fig_orders, use_container_width=True)

    with col2:
        fig_revenue = px.line(
            orders_by_date,
            x="order_date",
            y="revenue",
            title="Revenue Over Time"
        )
        st.plotly_chart(fig_revenue, use_container_width=True)

    st.subheader("🏭 Regional & Warehouse Insights")

    col3, col4 = st.columns(2)

    # Revenue by region
    revenue_by_region = (
        df.groupby("region")
        .agg(revenue=("order_value", "sum"))
        .reset_index()
    )
    with col3:
        fig_region = px.bar(
            revenue_by_region,
            x="region",
            y="revenue",
            title="Revenue by Region"
        )
        st.plotly_chart(fig_region, use_container_width=True)

    # On-time delivery by warehouse
    ontime_by_wh = (
        df.assign(is_late=df["delivery_status"].eq("Late"))
        .groupby("warehouse_id")
        .agg(on_time_rate=("is_late", lambda x: 100 * (1 - x.mean())))
        .reset_index()
    )

    with col4:
        fig_wh = px.bar(
            ontime_by_wh,
            x="warehouse_id",
            y="on_time_rate",
            title="On-Time Delivery Rate by Warehouse"
        )
        st.plotly_chart(fig_wh, use_container_width=True)

    st.subheader("📦 Product Category Performance")

    # Profitability by product category
    df["total_cost"] = df["shipping_cost"] + df["fulfillment_cost"]
    df["profit"] = df["order_value"] - df["total_cost"]

    perf_by_cat = (
        df.groupby("product_category")
        .agg(
            revenue=("order_value", "sum"),
            profit=("profit", "sum"),
            avg_delivery_days=("delivery_days", "mean")
        )
        .reset_index()
    )

    fig_cat = px.bar(
        perf_by_cat,
        x="product_category",
        y=["revenue", "profit"],
        barmode="group",
        title="Revenue vs Profit by Product Category"
    )
    st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown("#### Average Delivery Days by Product Category")
    fig_cat_delivery = px.bar(
        perf_by_cat,
        x="product_category",
        y="avg_delivery_days",
        title="Average Delivery Time by Product Category (days)"
    )
    st.plotly_chart(fig_cat_delivery, use_container_width=True)


def sidebar_filters(df):
    st.sidebar.header("🔍 Filters")

    regions = st.sidebar.multiselect(
        "Region",
        options=sorted(df["region"].unique()),
        default=sorted(df["region"].unique())
    )

    warehouses = st.sidebar.multiselect(
        "Warehouse",
        options=sorted(df["warehouse_id"].unique()),
        default=sorted(df["warehouse_id"].unique())
    )

    categories = st.sidebar.multiselect(
        "Product Category",
        options=sorted(df["product_category"].unique()),
        default=sorted(df["product_category"].unique())
    )

    # Ensure min/max as Python date objects for the widget
    min_date = df["order_date"].min().date()
    max_date = df["order_date"].max().date()

    # Streamlit returns a tuple for a range, or a single date if user selects one
    date_range = st.sidebar.date_input(
        "Order Date Range",
        (min_date, max_date)
    )

    # Normalize widget output: support single date or range
    if isinstance(date_range, (list, tuple)):
        if len(date_range) == 2:
            start_date, end_date = date_range
        elif len(date_range) == 1:
            start_date = end_date = date_range[0]
        else:
            start_date, end_date = min_date, max_date
    else:
        # Single date
        start_date = end_date = date_range

    # Convert to Timestamps for comparison with df["order_date"]
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)

    # Build filter mask
    mask = (
        df["region"].isin(regions) &
        df["warehouse_id"].isin(warehouses) &
        df["product_category"].isin(categories) &
        (df["order_date"] >= start_ts) &
        (df["order_date"] <= end_ts)
    )

    return df.loc[mask].copy()


# ---------------- MAIN APP LOGIC ----------------

uploaded_file = st.file_uploader("Upload Supply Chain CSV File", type=["csv"])

if uploaded_file is None:
    st.info(
        "☝️ Please upload the `amazon_supply_chain_data.csv` file "
        "to view KPIs and dashboards."
    )
else:
    df = load_data(uploaded_file)

    st.subheader("Raw Data Preview")
    st.dataframe(df.head())

    filtered_df = sidebar_filters(df)

    st.markdown(f"**Filtered rows:** {len(filtered_df):,}")

    if len(filtered_df) == 0:
        st.warning("No data available for the selected filters.")
    else:
        kpi_section(filtered_df)
        charts_section(filtered_df)
