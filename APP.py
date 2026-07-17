import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Solar Trend Analyzer",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Solar Plant Trend Analyzer")

st.write("Upload Excel file to validate data and generate chart.")

uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)
if uploaded_file is None:
    st.info("📂 Please upload an Excel file to validate data and generate the chart.")
    st.stop()

if uploaded_file is not None:

    try:

        df = pd.read_excel(uploaded_file)

        st.success("Excel Uploaded Successfully ✅")

        st.subheader("Data Preview")

        st.dataframe(df)

        # -----------------------------
        # Required Columns
        # -----------------------------

        required_columns = [

            "Date",
            "Time",
            "Active Power(kW)",
            "Reactive Power(kVAr)",
            "PoA(W/m2)"

        ]

        st.subheader("Data Validation")

        missing_columns = []

        for col in required_columns:

            if col not in df.columns:

                missing_columns.append(col)

        if len(missing_columns) > 0:

            st.error("Missing Columns")

            st.write(missing_columns)

            st.stop()

        else:

            st.success("All Required Columns Found")

        # -----------------------------
        # Blank Values
        # -----------------------------

        blank = df[required_columns].isnull().sum()

        st.write("Blank Values")

        st.dataframe(blank)

        # -----------------------------
        # Date Time
        # -----------------------------



        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%m-%d-%Y")
        df["DateTime"] = pd.to_datetime(

            df["Date"].astype(str)

            + " "

            + df["Time"].astype(str),

            errors="coerce"

        )

        invalid_datetime = df["DateTime"].isna().sum()

        if invalid_datetime == 0:

            st.success("No Invalid Date/Time")

        else:

            st.error(f"{invalid_datetime} Invalid Date/Time Found")

        # -----------------------------
        # Duplicate
        # -----------------------------

        duplicate = df["DateTime"].duplicated().sum()

        if duplicate == 0:

            st.success("No Duplicate Timestamp")

        else:

            st.error(f"{duplicate} Duplicate Timestamp Found")

        # -----------------------------
        # Numeric Validation
        # -----------------------------

        numeric_columns = [

            "Active Power(kW)",

            "Reactive Power(kVAr)",

            "PoA(W/m2)"

        ]

        for col in numeric_columns:

            df[col] = pd.to_numeric(

                df[col],

                errors="coerce"

            )

        st.write("Invalid Numeric Values")

        st.dataframe(

            df[numeric_columns].isnull().sum()

        )

        st.success("Validation Completed")

    except Exception as e:

        st.error(e)


import pandas as pd
import plotly.graph_objects as go

# Read Excel
df = pd.read_excel(uploaded_file)

# Combine Date + Time
df["DateTime"] = pd.to_datetime(
    df["Date"].astype(str) + " " + df["Time"].astype(str),
    errors="coerce"
)

fig = go.Figure()

# Active Power (LEFT)
fig.add_trace(go.Scatter(
    x=df["DateTime"],
    y=df["Active Power(kW)"],
    mode="lines",
    name="Active Power"
))

# Reactive Power (LEFT)
fig.add_trace(go.Scatter(
    x=df["DateTime"],
    y=df["Reactive Power(kVAr)"],
    mode="lines",
    name="Reactive Power"
))

# POA (RIGHT)
fig.add_trace(go.Scatter(
    x=df["DateTime"],
    y=df["PoA(W/m2)"],
    mode="lines",
    name="POA",
    yaxis="y2"
))

fig.update_layout(

    title="Active Power, Reactive Power & POA",
width=1000,
    height=500,
    xaxis=dict(
        title="Time",
        dtick=3600000,
        tickformat="%H:%M"
    ),

    # LEFT AXIS
    yaxis=dict(
        title="Power (MW / MVAr)",
        range=[-50000,250000]
    ),

    # RIGHT AXIS
    yaxis2=dict(
        title="POA (W/m²)",
        overlaying="y",
        side="right",
        range=[0,1200]
    ),
legend=dict(
    orientation="h",
    y=1.12,
    x=0.5,
    xanchor="center"
),
    hovermode="x unified",

    template="plotly_dark"
)

st.plotly_chart(fig,use_container_width=True)