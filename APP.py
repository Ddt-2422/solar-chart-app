"""
☀️  Solar Power Plant — Advanced Trend Analyzer
------------------------------------------------
Ek advanced Streamlit tool. Excel/CSV data upload karo aur:
  • Date / range / time-window filter
  • Kitne bhi parameters, har ek ko Primary ya Secondary axis pe
  • Live KPI cards (min / max / avg / last)
  • Resampling & smoothing (high-frequency / ms data ke liye)
  • Statistics, Correlation heatmap aur data-quality report
  • CSV / Excel export

Run:
    pip install -r requirements.txt
    streamlit run solar_trend_analyzer.py
"""

import io
import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ---------------------------------------------------------------
# Page config + design system
# ---------------------------------------------------------------
st.set_page_config(
    page_title="Solar Plant · Trend Analyzer",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Validated dark categorical palette (dataviz skill — fixed order, never cycled)
SERIES_COLORS = [
    "#3987e5",  # blue
    "#d95926",  # orange
    "#199e70",  # aqua
    "#c98500",  # yellow
    "#d55181",  # magenta
    "#008300",  # green
    "#9085e9",  # violet
    "#e66767",  # red
]
SURFACE = "#141922"
INK = "#E8EAED"
MUTED = "#8b93a1"
GRID = "#252b36"

# Diverging blue↔red for correlation (gray midpoint)
DIVERGING = [
    [0.0, "#184f95"], [0.25, "#6da7ec"], [0.5, "#383835"],
    [0.75, "#e08a8a"], [1.0, "#b83232"],
]

CUSTOM_CSS = """
<style>
/* ---- App background & typography ---- */
.stApp {
    background:
        radial-gradient(1200px 600px at 15% -10%, rgba(57,135,229,0.10), transparent 60%),
        radial-gradient(1000px 500px at 100% 0%, rgba(201,133,0,0.08), transparent 55%),
        #0b0e14;
}
html, body, [class*="css"] { font-family: "Segoe UI", system-ui, -apple-system, sans-serif; }

/* ---- Hero header ---- */
.hero {
    padding: 26px 30px;
    border-radius: 18px;
    background: linear-gradient(120deg, rgba(57,135,229,0.16), rgba(201,133,0,0.12));
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 8px;
}
.hero h1 { margin: 0; font-size: 30px; font-weight: 700; letter-spacing:-0.5px; color:#fff; }
.hero p  { margin: 6px 0 0; color: #aab2c0; font-size: 15px; }

/* ---- KPI cards ---- */
.kpi-grid { display:flex; gap:14px; flex-wrap:wrap; margin: 6px 0 4px; }
.kpi {
    flex: 1 1 190px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-left: 4px solid var(--accent, #3987e5);
    border-radius: 14px;
    padding: 14px 16px;
    transition: transform .12s ease, border-color .12s ease;
}
.kpi:hover { transform: translateY(-2px); }
.kpi .name  { color:#aab2c0; font-size:12.5px; font-weight:600; text-transform:uppercase; letter-spacing:.4px;
              white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.kpi .value { color:#fff; font-size:23px; font-weight:700; margin-top:4px; font-variant-numeric:tabular-nums; }
.kpi .sub   { color:#8b93a1; font-size:12px; margin-top:6px; font-variant-numeric:tabular-nums; }
.kpi .up    { color:#0ca30c; } .kpi .down { color:#e66767; }

/* ---- Section headers ---- */
.sec { font-size:19px; font-weight:700; color:#fff; margin: 10px 0 2px; }

/* ---- Tighten default blocks ---- */
[data-testid="stMetricValue"] { font-size: 22px; }
div[data-testid="stExpander"] { border-radius: 12px; }
section[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,0.06); }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
        <h1>☀️ Solar Power Plant — Trend Analyzer</h1>
        <p>Upload your Excel / CSV time-series, pick a date & parameters, and get an interactive
           multi-axis trend with live KPIs, statistics and correlation — all in one place.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
@st.cache_data(show_spinner="Loading CSV…")
def load_csv(file):
    return pd.read_csv(file)


@st.cache_data(show_spinner="Loading Excel sheet…")
def load_excel_sheet(file, sheet_name):
    return pd.read_excel(file, sheet_name=sheet_name)


def fmt(v):
    """Compact human number formatting for KPI cards."""
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return "—"
    a = abs(v)
    if a >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if a >= 1_000:
        return f"{v/1_000:.2f}k"
    if a >= 1:
        return f"{v:.2f}"
    return f"{v:.4g}"


def kpi_cards(df, params, dt_col):
    """Render one KPI card per selected parameter."""
    cards = []
    for i, p in enumerate(params):
        s = pd.to_numeric(df[p], errors="coerce").dropna()
        if s.empty:
            continue
        accent = SERIES_COLORS[i % len(SERIES_COLORS)]
        last, first = s.iloc[-1], s.iloc[0]
        delta = last - first
        arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "■")
        cls = "up" if delta > 0 else ("down" if delta < 0 else "")
        pct = (delta / abs(first) * 100) if first else 0
        cards.append(
            f"""
            <div class="kpi" style="--accent:{accent}">
                <div class="name" title="{p}">{p}</div>
                <div class="value">{fmt(last)}</div>
                <div class="sub">
                    <span class="{cls}">{arrow} {fmt(delta)} ({pct:+.1f}%)</span><br>
                    min {fmt(s.min())} · avg {fmt(s.mean())} · max {fmt(s.max())}
                </div>
            </div>"""
        )
    if cards:
        st.markdown('<div class="kpi-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def base_layout(fig, height=640):
    fig.update_layout(
        height=height,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=SURFACE,
        font=dict(color=INK, family="Segoe UI, system-ui, sans-serif"),
        hovermode="x unified",
        margin=dict(l=60, r=60, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


# ---------------------------------------------------------------
# Sidebar · Step 1 — Upload
# ---------------------------------------------------------------
st.sidebar.header("1️⃣  Upload Data")
uploaded_file = st.sidebar.file_uploader(
    "Excel (.xlsx/.xls) or CSV file", type=["xlsx", "xls", "csv"]
)

if uploaded_file is None:
    st.info("👈  Upload your Excel/CSV file from the sidebar to get started.")
    c1, c2, c3 = st.columns(3)
    c1.markdown("#### 1 · Upload\nAny interval — 1-min, 1-sec or millisecond time-series.")
    c2.markdown("#### 2 · Filter\nPick a date, range or full data — plus an optional time-of-day window.")
    c3.markdown("#### 3 · Analyze\nMulti-axis trend, KPI cards, statistics & correlation. Export anytime.")
    st.stop()

# ---- Load dataframe (handles multi-sheet excel) ----
if uploaded_file.name.lower().endswith(".csv"):
    df = load_csv(uploaded_file)
else:
    xls = pd.ExcelFile(uploaded_file)
    sheet = (
        st.sidebar.selectbox("Sheet", xls.sheet_names)
        if len(xls.sheet_names) > 1
        else xls.sheet_names[0]
    )
    df = load_excel_sheet(uploaded_file, sheet)

st.sidebar.success(f"Loaded  ·  {df.shape[0]:,} rows × {df.shape[1]} cols")

# ---------------------------------------------------------------
# Sidebar · Step 2 — Timestamp column (single column OR separate Date + Time)
# ---------------------------------------------------------------
st.sidebar.header("2️⃣  Timestamp Column")
all_cols = df.columns.tolist()

def _guess(keys, exclude=None):
    for c in all_cols:
        if c != exclude and any(k in c.lower() for k in keys):
            return c
    return None

ts_mode = st.sidebar.radio(
    "Timestamp format",
    ["One column", "Date + Time (separate)"],
    horizontal=True,
    help="Use 'Date + Time' if your date and time are in two separate columns.",
)

# columns to hide from the plottable-parameter list (source date/time columns)
extra_exclude = []

if ts_mode == "One column":
    default_dt_col = _guess(["date", "time"]) or all_cols[0]
    dt_col = st.sidebar.selectbox(
        "Which column is Date/Time?", all_cols, index=all_cols.index(default_dt_col)
    )
    try:
        df[dt_col] = pd.to_datetime(df[dt_col])
    except Exception:
        try:
            col = pd.to_numeric(df[dt_col], errors="raise")
            unit = "ms" if col.max() > 1e12 else "s"
            df[dt_col] = pd.to_datetime(col, unit=unit)
        except Exception as e:
            st.error(f"Could not convert '{dt_col}' to datetime: {e}")
            st.stop()
else:
    date_guess = _guess(["date"]) or all_cols[0]
    time_guess = _guess(["time"], exclude=date_guess) or next(
        (c for c in all_cols if c != date_guess), all_cols[0]
    )
    date_col = st.sidebar.selectbox("Date column", all_cols, index=all_cols.index(date_guess))
    time_col = st.sidebar.selectbox("Time column", all_cols, index=all_cols.index(time_guess))
    if date_col == time_col:
        st.sidebar.error("Date and Time columns must be different.")
        st.stop()

    dt_col = "Date + Time"
    extra_exclude = [date_col, time_col]
    try:
        date_part = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()
        tnum = pd.to_numeric(df[time_col], errors="coerce")
        # Excel stores a time-only cell as a fraction of a day (0–1)
        if tnum.notna().mean() > 0.8 and tnum.dropna().between(0, 1).mean() > 0.5:
            tod = pd.to_timedelta(tnum.fillna(0) * 24.0, unit="h")
        else:
            t = pd.to_datetime(df[time_col].astype(str), errors="coerce")
            tod = (t - t.dt.normalize()).fillna(pd.Timedelta(0))
        df[dt_col] = date_part + tod
        if df[dt_col].isna().all():
            raise ValueError("no valid combined datetimes were produced")
    except Exception as e:
        st.error(f"Could not combine '{date_col}' + '{time_col}': {e}")
        st.stop()

df = df.sort_values(by=dt_col).reset_index(drop=True)
df["__date_only__"] = df[dt_col].dt.date

# ---------------------------------------------------------------
# Sidebar · Step 3 — Date filter
# ---------------------------------------------------------------
st.sidebar.header("3️⃣  Select Date")
available_dates = sorted(df["__date_only__"].unique())

date_mode = st.sidebar.radio("Mode", ["Single Date", "Date Range", "Full Data"], index=0)

if date_mode == "Single Date":
    sel_date = st.sidebar.selectbox("Date", available_dates, index=len(available_dates) - 1)
    filtered_df = df[df["__date_only__"] == sel_date]
elif date_mode == "Date Range":
    if len(available_dates) > 1:
        start_date, end_date = st.sidebar.select_slider(
            "Range", options=available_dates, value=(available_dates[0], available_dates[-1])
        )
    else:
        start_date = end_date = available_dates[0]
    filtered_df = df[(df["__date_only__"] >= start_date) & (df["__date_only__"] <= end_date)]
else:
    filtered_df = df

# Optional time-of-day narrowing (for ms / high-frequency data)
if not filtered_df.empty and filtered_df[dt_col].min().time() != filtered_df[dt_col].max().time():
    if st.sidebar.checkbox("🔍  Narrow time-of-day window (ms / high-freq data)"):
        min_t = filtered_df[dt_col].min().time()
        max_t = filtered_df[dt_col].max().time()
        start_t, end_t = st.sidebar.slider(
            "Time window (HH:MM:SS)",
            min_value=min_t, max_value=max_t, value=(min_t, max_t),
            step=datetime.timedelta(seconds=1),
        )
        filtered_df = filtered_df[
            (filtered_df[dt_col].dt.time >= start_t) & (filtered_df[dt_col].dt.time <= end_t)
        ]

st.sidebar.info(f"Filtered rows  ·  {filtered_df.shape[0]:,}")

# ---------------------------------------------------------------
# Sidebar · Step 4 — Parameters & Axis
# ---------------------------------------------------------------
st.sidebar.header("4️⃣  Parameters & Axis")
numeric_cols = [
    c for c in df.columns
    if c not in [dt_col, "__date_only__", *extra_exclude] and pd.api.types.is_numeric_dtype(df[c])
]
if not numeric_cols:
    st.warning("No numeric columns found in the data.")
    st.stop()

selected_params = st.sidebar.multiselect(
    "Parameters to plot", numeric_cols, default=numeric_cols[: min(2, len(numeric_cols))]
)

view_mode = st.sidebar.radio(
    "Chart layout",
    ["Dual-axis (one chart)", "Separate panels (stacked)"],
    help="Separate panels avoid two mismatched y-scales sharing one axis — usually easier to read.",
)

axis_map = {}
if selected_params and view_mode.startswith("Dual"):
    st.sidebar.markdown("**Axis for each parameter:**")
    for param in selected_params:
        axis_map[param] = st.sidebar.radio(
            param, ["Primary (Left)", "Secondary (Right)"],
            key=f"axis_{param}", horizontal=True,
        )

# ---------------------------------------------------------------
# Sidebar · Step 5 — Rendering options
# ---------------------------------------------------------------
st.sidebar.header("5️⃣  Rendering")

chart_kind = st.sidebar.selectbox("Style", ["Line", "Line + markers", "Area"], index=0)

# Resampling — huge perf & clarity win for high-frequency data
resample_opts = {
    "None (raw)": None, "1 second": "1s", "5 seconds": "5s", "15 seconds": "15s",
    "30 seconds": "30s", "1 minute": "1min", "5 minutes": "5min", "15 minutes": "15min",
    "1 hour": "1h",
}
resample_choice = st.sidebar.selectbox("Resample / downsample", list(resample_opts.keys()), index=0)
resample_rule = resample_opts[resample_choice]
agg_func = st.sidebar.selectbox("Aggregation", ["mean", "max", "min", "last"], index=0) \
    if resample_rule else "mean"

smooth = st.sidebar.slider("Smoothing (rolling avg window)", 1, 60, 1,
                           help="1 = no smoothing. Higher = smoother line.")
show_peaks = st.sidebar.checkbox("Mark min / max peaks", value=False)

tick_options = {
    "Auto": None, "100 ms": 100, "500 ms": 500, "1 second": 1_000, "5 seconds": 5_000,
    "15 seconds": 15_000, "30 seconds": 30_000, "1 minute": 60_000, "5 minutes": 5 * 60_000,
    "15 minutes": 15 * 60_000, "30 minutes": 30 * 60_000, "1 hour": 3_600_000,
    "2 hours": 2 * 3_600_000, "3 hours": 3 * 3_600_000, "6 hours": 6 * 3_600_000,
}
tick_choice = st.sidebar.selectbox(
    "X-axis label interval", list(tick_options.keys()),
    index=list(tick_options.keys()).index("Auto"),
)
dtick_ms = tick_options[tick_choice]

# ---------------------------------------------------------------
# Prepare plot data (resample + smooth)
# ---------------------------------------------------------------
def prepare(data, params):
    d = data[[dt_col] + params].copy()
    if resample_rule:
        d = d.set_index(dt_col).resample(resample_rule).agg(agg_func).dropna(how="all").reset_index()
    if smooth > 1:
        for p in params:
            d[p] = d[p].rolling(smooth, min_periods=1).mean()
    return d


if not selected_params:
    st.info("Select at least one parameter from the sidebar to begin.")
    st.stop()

plot_df = prepare(filtered_df, selected_params)

if plot_df.empty:
    st.warning("No data after filtering. Adjust the date / time filters.")
    st.stop()

if filtered_df.shape[0] > 200_000 and resample_rule is None:
    st.warning(
        "⚠️ Over 200k points (likely millisecond data). Use **Resample / downsample** "
        "in the sidebar for a faster, clearer chart."
    )

# ---------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------
st.markdown('<div class="sec">Live Snapshot</div>', unsafe_allow_html=True)
kpi_cards(plot_df, selected_params, dt_col)

# X-axis tick format
if dtick_ms is not None and dtick_ms < 1_000:
    tick_fmt = "%H:%M:%S.%L"
elif dtick_ms is not None and dtick_ms < 60_000:
    tick_fmt = "%H:%M:%S"
else:
    tick_fmt = "%H:%M\n%d-%b"
xaxis_settings = dict(tickformat=tick_fmt, tickangle=0)
if dtick_ms is not None:
    xaxis_settings["dtick"] = dtick_ms


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def add_trace(fig, x, y, name, color, secondary=False, row=None):
    mode = {"Line": "lines", "Line + markers": "lines+markers", "Area": "lines"}[chart_kind]
    kw = dict(
        x=x, y=y, name=name, mode=mode,
        line=dict(color=color, width=1.8),
        marker=dict(size=5),
    )
    if chart_kind == "Area":
        kw["fill"] = "tozeroy"
        kw["fillcolor"] = _rgba(color, 0.18)
    trace = go.Scatter(**kw)
    if row is not None:
        fig.add_trace(trace, row=row, col=1)
    else:
        fig.add_trace(trace, secondary_y=secondary)


def add_peaks(fig, x, y, color, secondary=False, row=None):
    y = pd.to_numeric(y, errors="coerce")
    if y.dropna().empty:
        return
    imax, imin = y.idxmax(), y.idxmin()
    pts = go.Scatter(
        x=[x.loc[imax], x.loc[imin]], y=[y.loc[imax], y.loc[imin]],
        mode="markers+text", text=[f"max {fmt(y.loc[imax])}", f"min {fmt(y.loc[imin])}"],
        textposition="top center", marker=dict(color=color, size=10, symbol="diamond",
                                                line=dict(color="#fff", width=1)),
        showlegend=False, textfont=dict(size=10, color=MUTED),
    )
    if row is not None:
        fig.add_trace(pts, row=row, col=1)
    else:
        fig.add_trace(pts, secondary_y=secondary)


# ---------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------
tab_trend, tab_stats, tab_corr, tab_data = st.tabs(
    ["📈  Trend", "📊  Statistics", "🔗  Correlation", "📋  Data"]
)

# ---- TREND ----
with tab_trend:
    if view_mode.startswith("Dual"):
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        for i, param in enumerate(selected_params):
            color = SERIES_COLORS[i % len(SERIES_COLORS)]
            is_secondary = axis_map[param] == "Secondary (Right)"
            add_trace(fig, plot_df[dt_col], plot_df[param], param, color, secondary=is_secondary)
            if show_peaks:
                add_peaks(fig, plot_df[dt_col], plot_df[param], color, secondary=is_secondary)

        primary = [p for p in selected_params if axis_map[p] == "Primary (Left)"]
        secondary = [p for p in selected_params if axis_map[p] == "Secondary (Right)"]
        base_layout(fig)
        fig.update_layout(xaxis=xaxis_settings, xaxis_title="Time")
        fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06))
        fig.update_yaxes(title_text=" | ".join(primary) or "Primary", secondary_y=False)
        fig.update_yaxes(title_text=" | ".join(secondary) or "Secondary", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        n = len(selected_params)
        fig = make_subplots(rows=n, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                            subplot_titles=selected_params)
        for i, param in enumerate(selected_params):
            color = SERIES_COLORS[i % len(SERIES_COLORS)]
            add_trace(fig, plot_df[dt_col], plot_df[param], param, color, row=i + 1)
            if show_peaks:
                add_peaks(fig, plot_df[dt_col], plot_df[param], color, row=i + 1)
        base_layout(fig, height=max(320, 220 * n))
        fig.update_xaxes(**xaxis_settings, row=n, col=1)
        fig.update_layout(showlegend=False)
        for ann in fig["layout"]["annotations"]:
            ann["font"] = dict(size=13, color=INK)
        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Showing {plot_df.shape[0]:,} points"
        + (f" · resampled to {resample_choice} ({agg_func})" if resample_rule else " · raw")
        + (f" · smoothed ×{smooth}" if smooth > 1 else "")
    )

# ---- STATISTICS ----
with tab_stats:
    st.markdown('<div class="sec">Descriptive Statistics</div>', unsafe_allow_html=True)
    desc = plot_df[selected_params].describe().T
    desc["range"] = desc["max"] - desc["min"]
    desc = desc.rename(columns={"50%": "median"})
    styled = (
        desc[["count", "mean", "std", "min", "25%", "median", "75%", "max", "range"]]
        .style.format("{:.3f}")
        .bar(subset=["mean"], color="#3987e5")
        .bar(subset=["max"], color="#199e70")
    )
    st.dataframe(styled, use_container_width=True)

    st.markdown('<div class="sec">Data Quality</div>', unsafe_allow_html=True)
    total = len(plot_df)
    q = pd.DataFrame({
        "Missing": plot_df[selected_params].isna().sum(),
        "Missing %": (plot_df[selected_params].isna().mean() * 100).round(2),
        "Unique": plot_df[selected_params].nunique(),
        "Zeros": (plot_df[selected_params] == 0).sum(),
    })
    st.dataframe(q, use_container_width=True)
    st.caption(f"Time span: {plot_df[dt_col].min()}  →  {plot_df[dt_col].max()}  ·  {total:,} rows")

# ---- CORRELATION ----
with tab_corr:
    if len(selected_params) < 2:
        st.info("Select at least 2 parameters to see their correlation.")
    else:
        st.markdown('<div class="sec">Correlation Matrix (Pearson)</div>', unsafe_allow_html=True)
        corr = plot_df[selected_params].corr()
        heat = go.Figure(go.Heatmap(
            z=corr.values, x=corr.columns, y=corr.columns,
            colorscale=DIVERGING, zmid=0, zmin=-1, zmax=1,
            text=corr.round(2).values, texttemplate="%{text}",
            textfont=dict(size=12), colorbar=dict(title="r"),
        ))
        base_layout(heat, height=max(360, 90 * len(selected_params)))
        heat.update_layout(hovermode="closest")
        heat.update_xaxes(showgrid=False)
        heat.update_yaxes(showgrid=False, autorange="reversed")
        st.plotly_chart(heat, use_container_width=True)
        st.caption("Blue = positive, red = negative, gray ≈ no linear relationship.")

# ---- DATA ----
with tab_data:
    st.markdown('<div class="sec">Filtered Data</div>', unsafe_allow_html=True)
    show_cols = [dt_col] + selected_params
    st.dataframe(plot_df[show_cols], use_container_width=True, height=420)

    c1, c2 = st.columns(2)
    # CSV
    csv_buffer = io.StringIO()
    plot_df[show_cols].to_csv(csv_buffer, index=False)
    c1.download_button(
        "⬇️  Download CSV", csv_buffer.getvalue(),
        file_name="filtered_trend_data.csv", mime="text/csv", use_container_width=True,
    )
    # Excel
    xlsx_buffer = io.BytesIO()
    with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
        plot_df[show_cols].to_excel(writer, index=False, sheet_name="Trend")
        plot_df[selected_params].describe().T.to_excel(writer, sheet_name="Statistics")
    c2.download_button(
        "⬇️  Download Excel (data + stats)", xlsx_buffer.getvalue(),
        file_name="filtered_trend_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
