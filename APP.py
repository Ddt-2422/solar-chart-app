import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(
    page_title="Solar Trend Analyzer",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Solar Plant Trend Analyzer")

st.write("Upload Excel file to validate data and generate chart.")


# -----------------------------
# Blank template (for download)
# -----------------------------

def build_template():
    columns = [
        "Date",
        "Time",
        "Active Power(kW)",
        "Reactive Power(kVAr)",
        "PoA(W/m2)"
    ]
    # one example row so the expected format is clear, then blank rows
    rows = [["2026-07-17", "05:00:00", 0, 0, 0]]
    rows += [["", "", "", "", ""] for _ in range(20)]
    template_df = pd.DataFrame(rows, columns=columns)

    buffer = BytesIO()
    template_df.to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer

st.download_button(
    label="⬇️ Download Blank Template (Excel)",
    data=build_template(),
    file_name="solar_data_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)
if uploaded_file is None:
    st.info("📂 Please upload an Excel file to validate data and generate the chart.")
    st.stop()

try:

    # -----------------------------
    # Read Excel (only once)
    # -----------------------------

    df = pd.read_excel(uploaded_file)

    st.success("Excel Uploaded Successfully ✅")

    st.subheader("Data Preview")

    st.dataframe(df)

    # -----------------------------
    # Columns are identified by POSITION, not by name.
    # Column 1 = Date, 2 = Time, 3 = Active Power,
    # 4 = Reactive Power, 5 = PoA. Original names can be anything.
    # -----------------------------

    required_columns = [
        "Date",
        "Time",
        "Active Power(kW)",
        "Reactive Power(kVAr)",
        "PoA(W/m2)"
    ]

    st.subheader("Data Validation")

    if df.shape[1] < len(required_columns):
        st.error(
            f"Need at least {len(required_columns)} columns "
            f"(Date, Time, Active Power, Reactive Power, PoA) by position. "
            f"Found only {df.shape[1]}."
        )
        st.stop()

    # Keep the ORIGINAL column headers (with their units) so we can show
    # exactly what the user typed in the Excel on the chart labels.
    original_names = list(df.columns[:len(required_columns)])
    label_active = original_names[2]
    label_reactive = original_names[3]
    label_poa = original_names[4]

    # Take the first 5 columns by position and give them the standard names
    df = df.iloc[:, :len(required_columns)].copy()
    df.columns = required_columns

    st.success("Columns mapped by position ✅")
    st.caption(
        f"Column 1 → Date, 2 → Time, 3 → {label_active}, "
        f"4 → {label_reactive}, 5 → {label_poa}"
    )

    # -----------------------------
    # Blank Values
    # -----------------------------

    blank = df[required_columns].isnull().sum()
    st.write("Blank Values")
    st.dataframe(blank)

    # -----------------------------
    # Date Time
    # -----------------------------

    df["DateTime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Time"].astype(str),
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
        df[col] = pd.to_numeric(df[col], errors="coerce")

    st.write("Invalid Numeric Values")
    st.dataframe(df[numeric_columns].isnull().sum())

    st.success("Validation Completed")

    # -----------------------------
    # Chart
    # -----------------------------

    st.subheader("Trend Chart")

    # Rows without a valid DateTime cannot be plotted
    plot_df = df.dropna(subset=["DateTime"]).sort_values("DateTime")

    if plot_df.empty:
        st.warning("No valid Date/Time rows available to plot.")
        st.stop()

    # Date-wise filter (works even when one Excel has many dates)
    plot_df["DateOnly"] = plot_df["DateTime"].dt.date
    available_dates = sorted(plot_df["DateOnly"].unique())

    date_options = ["All Dates"] + [d.strftime("%d-%b-%Y") for d in available_dates]
    selected = st.selectbox("Select Date", date_options)

    if selected != "All Dates":
        chosen = pd.to_datetime(selected).date()
        chart_df = plot_df[plot_df["DateOnly"] == chosen]
    else:
        chart_df = plot_df

    # If the visible data spans more than one day, show date + time on the axis
    spans_multiple_days = chart_df["DateOnly"].nunique() > 1
    tick_format = "%d-%b %H:%M" if spans_multiple_days else "%H:%M"
    # Single day -> one tick every hour; multi-day -> let Plotly auto-space
    tick_dtick = None if spans_multiple_days else 3600000

    fig = go.Figure()

    # Active Power (LEFT) — label taken from the Excel header
    fig.add_trace(go.Scatter(
        x=chart_df["DateTime"],
        y=chart_df["Active Power(kW)"],
        mode="lines",
        name=label_active
    ))

    # Reactive Power (LEFT) — label taken from the Excel header
    fig.add_trace(go.Scatter(
        x=chart_df["DateTime"],
        y=chart_df["Reactive Power(kVAr)"],
        mode="lines",
        name=label_reactive
    ))

    # POA (RIGHT) — label taken from the Excel header
    fig.add_trace(go.Scatter(
        x=chart_df["DateTime"],
        y=chart_df["PoA(W/m2)"],
        mode="lines",
        name=label_poa,
        yaxis="y2"
    ))

    fig.update_layout(
        title=f"{label_active}, {label_reactive} & {label_poa}",
        height=500,
        xaxis=dict(
            title="Time",
            tickformat=tick_format,
            dtick=tick_dtick
        ),

        # LEFT AXIS (auto-scales to the data)
        yaxis=dict(
            title=f"{label_active} / {label_reactive}",
            autorange=True,
            rangemode="tozero"
        ),

        # RIGHT AXIS (auto-scales to the data)
        yaxis2=dict(
            title=label_poa,
            overlaying="y",
            side="right",
            autorange=True,
            rangemode="tozero"
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

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(e)
