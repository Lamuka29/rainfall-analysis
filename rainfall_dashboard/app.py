import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import calendar
import io
import zipfile
import streamlit as st

# ============================================================
# STREAMLIT CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Rainfall Analysis",
    page_icon="🌧️",
    layout="wide"
)

st.title("🌧️ Rainfall Data Analysis")
st.caption("Pemprosesan, Quality Control dan Analisis Data Hujan Harian")

# ============================================================
# SIDEBAR SETTINGS
# ============================================================
st.sidebar.header("⚙️ Analysis Settings")

START_YEAR = int(st.sidebar.number_input(
    "Start Year", min_value=1900, max_value=2100, value=2016, step=1
))
END_YEAR = int(st.sidebar.number_input(
    "End Year", min_value=1900, max_value=2100, value=2025, step=1
))

if START_YEAR > END_YEAR:
    st.sidebar.error("Start Year mesti lebih kecil atau sama dengan End Year.")
    st.stop()

years = range(START_YEAR, END_YEAR + 1)
YEAR_RANGE_TEXT = f"{START_YEAR}–{END_YEAR}"

target_year = int(st.sidebar.number_input(
    "Target Year", min_value=1900, max_value=2100, value=2018, step=1
))

st.sidebar.subheader("WMO Missing Data Rule")

MAX_MISSING_DAYS = int(st.sidebar.number_input(
    "Maximum missing days", min_value=0, max_value=31, value=10, step=1,
    help="Bulan ditolak jika missing days melebihi nilai ini."
))

MAX_CONSECUTIVE_MISSING = int(st.sidebar.number_input(
    "Maximum consecutive missing days", min_value=1, max_value=31, value=4, step=1,
    help="Bulan ditolak jika missing berturut-turut melebihi nilai ini."
))

st.sidebar.subheader("🌧️ Rainfall Threshold")

VALID_MIN = 0.0

WET_DAY_MIN = st.sidebar.number_input(
    "Wet day threshold (mm)", min_value=0.0, value=0.1, step=0.1
)

SUSPECT_RAINFALL = st.sidebar.number_input(
    "Suspect threshold (mm)", min_value=0.0, value=150.0, step=10.0
)

EXTREME_RAINFALL = st.sidebar.number_input(
    "Extreme threshold (mm)", min_value=0.0, value=250.0, step=10.0
)

months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

# ============================================================
# PLOT SETTINGS
# Semua warna di bawah boleh diubah oleh pengguna.
# ============================================================
st.sidebar.header("🎨 Plot Settings")

BG_COLOR = st.sidebar.color_picker(
    "Background Graf", "#FFFFFF"
)

st.sidebar.markdown("**🌈 Warna Bar Mengikut Bulan**")

default_colors = [
    "#4682B4", "#87CEEB", "#3CB371", "#32CD32",
    "#FFD700", "#FFA500", "#FF7F50", "#FF6347",
    "#9370DB", "#DA70D6", "#6A5ACD", "#008080"
]

BAR_COLORS = []
for month, default_color in zip(months, default_colors):
    BAR_COLORS.append(
        st.sidebar.color_picker(f"{month} Bar", default_color)
    )

st.sidebar.markdown("**📈 Warna Garisan / Penanda**")

LINE_COLOR = st.sidebar.color_picker("Mean Line", "#000000")
MIN_COLOR = st.sidebar.color_picker("Minimum", "#008000")
MAX_COLOR = st.sidebar.color_picker("Maximum", "#FF0000")

st.sidebar.markdown("**📊 Warna Graf Lain**")

MAX_DAILY_COLOR = st.sidebar.color_picker(
    "Maximum Daily Rainfall", "#FF6347"
)
WET_DAY_COLOR = st.sidebar.color_picker(
    "Wet Days", "#3CB371"
)
STD_COLOR = st.sidebar.color_picker(
    "Standard Deviation", "#9370DB"
)
HIST_COLOR = st.sidebar.color_picker(
    "Histogram", "#4682B4"
)

# ============================================================
# FILE UPLOAD
# ============================================================
uploaded_files = st.file_uploader(
    "📁 Upload Excel file",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Sila upload sekurang-kurangnya satu fail Excel.")
    st.markdown("""
    **Format data yang diperlukan:**

    - Sheet dinamakan mengikut tahun, contoh `2016`, `2017`, ..., `2025`
    - Header berada pada baris ke-7 Excel
    - Column A = `hari`
    - Column B:M = `Jan` hingga `Dec`
    - `N.A.` / kosong = missing
    - `0.0 mm` = data sah
    """)
    st.stop()

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def max_consecutive_missing(values):
    is_missing = values.isna()
    max_missing = 0
    current_missing = 0

    for missing in is_missing:
        if missing:
            current_missing += 1
            max_missing = max(max_missing, current_missing)
        else:
            current_missing = 0

    return max_missing


def read_year_sheet(uploaded_file, year):
    try:
        df = pd.read_excel(
            io.BytesIO(uploaded_file.getvalue()),
            sheet_name=str(year),
            header=6
        )
    except Exception as e:
        return None, str(e)

    if df is None or df.empty:
        return None, "Sheet kosong."

    if df.shape[1] < 13:
        return None, (
            f"Bilangan column tidak mencukupi ({df.shape[1]} dikesan). "
            "Minimum 13 column diperlukan."
        )

    df = df.iloc[:, :13].copy()
    df.columns = ["hari"] + months

    df["hari"] = pd.to_numeric(df["hari"], errors="coerce")
    df = df[df["hari"].between(1, 31)].copy()

    for month in months:
        df[month] = pd.to_numeric(df[month], errors="coerce")
        df.loc[df[month] < VALID_MIN, month] = np.nan

    df["Year"] = int(year)
    return df, None


def analyze_file(uploaded_file):
    file_name = os.path.splitext(uploaded_file.name)[0]
    original_file_name = uploaded_file.name

    daily_results = []
    read_errors = []

    for year in years:
        df, error = read_year_sheet(uploaded_file, year)
        if df is not None:
            daily_results.append(df)
        else:
            read_errors.append({"Year": year, "Error": error})

    if not daily_results:
        return {
            "success": False,
            "file_name": file_name,
            "original_file_name": original_file_name,
            "error": "Tiada sheet tahun berjaya dibaca."
        }

    all_daily = pd.concat(daily_results, ignore_index=True)

    for month in months:
        all_daily.loc[all_daily[month] < VALID_MIN, month] = np.nan

    # ---------------- Suspect / extreme ----------------
    suspect_records = []
    extreme_records = []

    for _, row in all_daily.iterrows():
        year = int(row["Year"])
        day = int(row["hari"])

        for month in months:
            value = row[month]

            if pd.isna(value):
                continue

            if value > EXTREME_RAINFALL:
                extreme_records.append({
                    "Year": year, "Day": day, "Month": month,
                    "Rainfall (mm)": value,
                    "Status": "EXTREME - DOUBLE CHECK"
                })
            elif value > SUSPECT_RAINFALL:
                suspect_records.append({
                    "Year": year, "Day": day, "Month": month,
                    "Rainfall (mm)": value,
                    "Status": "SUSPECT - SEMAK"
                })

    suspect_df = pd.DataFrame(
        suspect_records,
        columns=["Year", "Day", "Month", "Rainfall (mm)", "Status"]
    )
    extreme_df = pd.DataFrame(
        extreme_records,
        columns=["Year", "Day", "Month", "Rainfall (mm)", "Status"]
    )

    # ---------------- Monthly QC ----------------
    available_years = sorted(all_daily["Year"].unique())

    yearly_monthly_total = pd.DataFrame(
        index=available_years, columns=months, dtype=float
    )
    monthly_missing_count = pd.DataFrame(
        index=available_years, columns=months, dtype=float
    )
    monthly_valid_count = pd.DataFrame(
        index=available_years, columns=months, dtype=float
    )
    monthly_max_consecutive_missing = pd.DataFrame(
        index=available_years, columns=months, dtype=float
    )
    monthly_qc_status = pd.DataFrame(
        index=available_years, columns=months, dtype=object
    )

    for year in available_years:
        year_data = all_daily[all_daily["Year"] == year]

        for month in months:
            month_index = months.index(month) + 1
            days_expected = calendar.monthrange(int(year), month_index)[1]

            values = year_data[month].iloc[:days_expected].copy()
            valid_values = values[
                values.notna() & (values >= VALID_MIN)
            ]

            valid_count = len(valid_values)
            missing_count = days_expected - valid_count
            max_consecutive = max_consecutive_missing(values)

            monthly_valid_count.loc[year, month] = valid_count
            monthly_missing_count.loc[year, month] = missing_count
            monthly_max_consecutive_missing.loc[
                year, month
            ] = max_consecutive

            if (
                missing_count <= MAX_MISSING_DAYS
                and max_consecutive <= MAX_CONSECUTIVE_MISSING
            ):
                yearly_monthly_total.loc[year, month] = valid_values.sum()
                monthly_qc_status.loc[year, month] = "ACCEPT"
            else:
                yearly_monthly_total.loc[year, month] = np.nan

                if missing_count > MAX_MISSING_DAYS:
                    monthly_qc_status.loc[year, month] = (
                        f"REJECT: >{MAX_MISSING_DAYS} MISSING"
                    )
                elif max_consecutive > MAX_CONSECUTIVE_MISSING:
                    monthly_qc_status.loc[year, month] = (
                        f"REJECT: >{MAX_CONSECUTIVE_MISSING} "
                        "CONSECUTIVE MISSING"
                    )
                else:
                    monthly_qc_status.loc[year, month] = "REJECT"

    if target_year not in yearly_monthly_total.index:
        return {
            "success": False,
            "file_name": file_name,
            "original_file_name": original_file_name,
            "error": f"Data tahun {target_year} tidak dijumpai.",
            "available_years": available_years
        }

    rainfall_target = yearly_monthly_total.loc[target_year].reindex(months)

    mean_monthly_total = (
        yearly_monthly_total.mean(axis=0, skipna=True).reindex(months)
    )

    anomaly_percent = (
        (rainfall_target - mean_monthly_total) / mean_monthly_total
    ) * 100
    anomaly_percent[mean_monthly_total == 0] = np.nan

    # ---------------- Min / max ----------------
    valid_target = rainfall_target.dropna()
    if len(valid_target):
        min_target_month = valid_target.idxmin()
        min_target_value = valid_target.min()
        max_target_month = valid_target.idxmax()
        max_target_value = valid_target.max()
    else:
        min_target_month = min_target_value = None
        max_target_month = max_target_value = None

    valid_mean = mean_monthly_total.dropna()
    if len(valid_mean):
        min_mean_month = valid_mean.idxmin()
        min_mean_value = valid_mean.min()
        max_mean_month = valid_mean.idxmax()
        max_mean_value = valid_mean.max()
    else:
        min_mean_month = min_mean_value = None
        max_mean_month = max_mean_value = None

    # ---------------- Daily statistics ----------------
    median_daily = []
    std_daily = []
    max_daily = []
    min_daily = []
    wet_days = []
    valid_data_percent = []
    suspect_count = []
    extreme_count = []

    target_data = all_daily[all_daily["Year"] == target_year].copy()

    for month in months:
        month_index = months.index(month) + 1
        days_expected = calendar.monthrange(target_year, month_index)[1]

        raw_values = target_data[month].iloc[:days_expected].copy()

        qc_values = raw_values[
            raw_values.notna() & (raw_values >= VALID_MIN)
        ]
        values = qc_values[qc_values >= WET_DAY_MIN]

        valid_count = len(qc_values)
        valid_data_percent.append((valid_count / days_expected) * 100)

        median_daily.append(
            values.median() if len(values) else np.nan
        )
        std_daily.append(
            values.std() if len(values) > 1 else np.nan
        )
        max_daily.append(
            values.max() if len(values) else np.nan
        )
        min_daily.append(
            values.min() if len(values) else np.nan
        )
        wet_days.append(int((qc_values >= WET_DAY_MIN).sum()))
        suspect_count.append(int((values > SUSPECT_RAINFALL).sum()))
        extreme_count.append(int((values > EXTREME_RAINFALL).sum()))

    analysis_table = pd.DataFrame({
        "Month": months,
        f"Total {target_year} (mm)": rainfall_target.values,
        f"Mean {YEAR_RANGE_TEXT} (mm)": mean_monthly_total.values,
        f"Anomaly {target_year} (%)": anomaly_percent.values,
        "Median Daily (>=0.1 mm)": median_daily,
        "SD Daily (>=0.1 mm)": std_daily,
        "Maximum Daily (>=0.1 mm)": max_daily,
        "Minimum Daily (>=0.1 mm)": min_daily,
        "Wet Days (>=0.1 mm)": wet_days,
        f"Suspect Days (>{SUSPECT_RAINFALL:.0f} mm)": suspect_count,
        f"Extreme Days (>{EXTREME_RAINFALL:.0f} mm)": extreme_count,
        "Valid Data (>=0.0 mm) (%)": valid_data_percent
    })

    # ---------------- Histogram / category data ----------------
    hist_values = []
    pie_values = []

    for month in months:
        month_index = months.index(month) + 1
        days_expected = calendar.monthrange(target_year, month_index)[1]

        raw_values = target_data[month].iloc[:days_expected].copy()
        valid_values = raw_values[
            raw_values.notna() & (raw_values >= VALID_MIN)
        ]

        hist_values.extend(
            valid_values[valid_values >= WET_DAY_MIN].tolist()
        )
        pie_values.extend(valid_values.tolist())

    no_rain = sum(value == 0.0 for value in pie_values)
    light_rain = sum(0.1 <= value <= 10.0 for value in pie_values)
    moderate_rain = sum(10.0 < value <= 50.0 for value in pie_values)
    heavy_rain = sum(value > 50.0 for value in pie_values)

    category_values = [no_rain, light_rain, moderate_rain, heavy_rain]
    category_labels = [
        "No Rain (0.0 mm)",
        "Light Rain (0.1–10 mm)",
        "Moderate Rain (>10–50 mm)",
        "Heavy Rain (>50 mm)"
    ]

    return {
        "success": True,
        "file_name": file_name,
        "original_file_name": original_file_name,
        "all_daily": all_daily,
        "yearly_monthly_total": yearly_monthly_total,
        "monthly_missing_count": monthly_missing_count,
        "monthly_valid_count": monthly_valid_count,
        "monthly_max_consecutive_missing": monthly_max_consecutive_missing,
        "monthly_qc_status": monthly_qc_status,
        "rainfall_target": rainfall_target,
        "mean_monthly_total": mean_monthly_total,
        "anomaly_percent": anomaly_percent,
        "min_target_month": min_target_month,
        "min_target_value": min_target_value,
        "max_target_month": max_target_month,
        "max_target_value": max_target_value,
        "min_mean_month": min_mean_month,
        "min_mean_value": min_mean_value,
        "max_mean_month": max_mean_month,
        "max_mean_value": max_mean_value,
        "median_daily": median_daily,
        "std_daily": std_daily,
        "max_daily": max_daily,
        "min_daily": min_daily,
        "wet_days": wet_days,
        "valid_data_percent": valid_data_percent,
        "suspect_count": suspect_count,
        "extreme_count": extreme_count,
        "analysis_table": analysis_table,
        "suspect_df": suspect_df,
        "extreme_df": extreme_df,
        "hist_values": hist_values,
        "category_values": category_values,
        "category_labels": category_labels,
        "read_errors": read_errors
    }


def apply_plot_style(fig, ax):
    """Apply user-selected background to every Matplotlib plot."""
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)


def finish_plot(fig):
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


# ============================================================
# PROCESS ALL FILES
# ============================================================
with st.spinner("⏳ Sedang memproses semua fail Excel..."):
    results = []
    progress_bar = st.progress(0)

    for i, uploaded_file in enumerate(uploaded_files):
        results.append(analyze_file(uploaded_file))
        progress_bar.progress(int(((i + 1) / len(uploaded_files)) * 100))

    progress_bar.empty()

successful_results = [
    result for result in results if result.get("success", False)
]
failed_results = [
    result for result in results if not result.get("success", False)
]

st.success(
    f"✅ {len(successful_results)} daripada "
    f"{len(uploaded_files)} fail berjaya dianalisis."
)

if failed_results:
    st.warning(f"⚠️ {len(failed_results)} fail tidak berjaya dianalisis.")
    for result in failed_results:
        st.error(
            f"{result.get('original_file_name', 'Unknown')}: "
            f"{result.get('error', 'Unknown error')}"
        )

if not successful_results:
    st.stop()

# ============================================================
# GLOBAL AUTO Y-AXIS
# ============================================================
global_max_total = 0
global_max_mean = 0
max_total_file = max_total_month = None
max_mean_file = max_mean_month = None

for result in successful_results:
    rainfall_target = result["rainfall_target"]
    mean_monthly_total = result["mean_monthly_total"]

    if rainfall_target.notna().any():
        local_max = rainfall_target.max()
        if local_max > global_max_total:
            global_max_total = local_max
            max_total_file = result["original_file_name"]
            max_total_month = rainfall_target.idxmax()

    if mean_monthly_total.notna().any():
        local_max = mean_monthly_total.max()
        if local_max > global_max_mean:
            global_max_mean = local_max
            max_mean_file = result["original_file_name"]
            max_mean_month = mean_monthly_total.idxmax()

selected_max = max(global_max_total, global_max_mean)
RAINFALL_MAX = (
    (int(selected_max / 100) + 1) * 100
    if selected_max > 0 else 100
)

# ============================================================
# GLOBAL SUMMARY
# ============================================================
st.subheader("📌 Overall Analysis Summary")

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

with summary_col1:
    st.metric("Files Analysed", len(successful_results))

with summary_col2:
    st.metric("Target Year", target_year)

with summary_col3:
    st.metric("Climatology", YEAR_RANGE_TEXT)

with summary_col4:
    st.metric("Auto Y-Axis Maximum", f"{RAINFALL_MAX:.0f} mm")

with st.expander("🔎 Auto Y-Axis Information"):
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Maximum Target-Year Monthly Total**")
        st.write(f"Value: {global_max_total:.2f} mm")
        st.write(f"File: {max_total_file}")
        st.write(f"Month: {max_total_month}")

    with col2:
        st.write("**Maximum Climatological Monthly Mean**")
        st.write(f"Value: {global_max_mean:.2f} mm")
        st.write(f"File: {max_mean_file}")
        st.write(f"Month: {max_mean_month}")

# ============================================================
# DISPLAY EACH FILE
# ============================================================
for result in successful_results:
    file_name = result["file_name"]
    original_file_name = result["original_file_name"]

    all_daily = result["all_daily"]
    yearly_monthly_total = result["yearly_monthly_total"]
    monthly_missing_count = result["monthly_missing_count"]
    monthly_valid_count = result["monthly_valid_count"]
    monthly_max_consecutive_missing = result[
        "monthly_max_consecutive_missing"
    ]
    monthly_qc_status = result["monthly_qc_status"]
    rainfall_target = result["rainfall_target"]
    mean_monthly_total = result["mean_monthly_total"]
    anomaly_percent = result["anomaly_percent"]

    min_target_month = result["min_target_month"]
    min_target_value = result["min_target_value"]
    max_target_month = result["max_target_month"]
    max_target_value = result["max_target_value"]
    min_mean_month = result["min_mean_month"]
    min_mean_value = result["min_mean_value"]
    max_mean_month = result["max_mean_month"]
    max_mean_value = result["max_mean_value"]

    median_daily = result["median_daily"]
    std_daily = result["std_daily"]
    max_daily = result["max_daily"]
    min_daily = result["min_daily"]
    wet_days = result["wet_days"]
    valid_data_percent = result["valid_data_percent"]

    analysis_table = result["analysis_table"]
    suspect_df = result["suspect_df"]
    extreme_df = result["extreme_df"]
    hist_values = result["hist_values"]
    category_values = result["category_values"]
    category_labels = result["category_labels"]
    read_errors = result["read_errors"]

    st.divider()
    st.header(f"📁 {original_file_name}")

    if read_errors:
        with st.expander("⚠️ Sheet yang tidak berjaya dibaca"):
            st.dataframe(
                pd.DataFrame(read_errors),
                use_container_width=True,
                hide_index=True
            )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            f"Minimum {target_year}",
            f"{min_target_value:.2f} mm" if min_target_value is not None else "N.A.",
            min_target_month if min_target_month else None
        )

    with col2:
        st.metric(
            f"Maximum {target_year}",
            f"{max_target_value:.2f} mm" if max_target_value is not None else "N.A.",
            max_target_month if max_target_month else None
        )

    with col3:
        st.metric(
            "Minimum Mean",
            f"{min_mean_value:.2f} mm" if min_mean_value is not None else "N.A.",
            min_mean_month if min_mean_month else None
        )

    with col4:
        st.metric(
            "Maximum Mean",
            f"{max_mean_value:.2f} mm" if max_mean_value is not None else "N.A.",
            max_mean_month if max_mean_month else None
        )

    qc_col1, qc_col2, qc_col3 = st.columns(3)

    with qc_col1:
        st.metric("Suspect Records", len(suspect_df))
    with qc_col2:
        st.metric("Extreme Records", len(extreme_df))
    with qc_col3:
        st.metric(
            "Valid Daily Records",
            int(all_daily[months].notna().sum().sum())
        )

    tabs = st.tabs([
        "📊 Bar + Line",
        "🔥 Heatmap",
        "📉 Anomaly",
        "📋 Statistics",
        "📈 Max Daily",
        "🌧️ Wet Days",
        "📐 Standard Deviation",
        "📊 Histogram",
        "🥧 Rainfall Category",
        "⚠️ QC"
    ])

    x = np.arange(len(months))

    # ========================================================
    # TAB 1 - BAR + LINE
    # ========================================================
    with tabs[0]:
        st.subheader(
            f"Monthly Rainfall {target_year} vs "
            f"Mean Monthly Rainfall {YEAR_RANGE_TEXT}"
        )

        fig, ax = plt.subplots(figsize=(14, 9))
        apply_plot_style(fig, ax)

        ax.bar(
            x, rainfall_target.values,
            width=0.60,
            color=BAR_COLORS,
            edgecolor="black",
            linewidth=0.8,
            label=f"Total Rainfall {target_year}"
        )

        ax.plot(
            x, mean_monthly_total.values,
            color=LINE_COLOR,
            marker="o",
            linewidth=2.5,
            markersize=7,
            label=f"Mean Monthly Rainfall {YEAR_RANGE_TEXT}"
        )

        for i, value in enumerate(mean_monthly_total.values):
            if pd.notna(value):
                ax.annotate(
                    f"{value:.1f}",
                    (i, value),
                    xytext=(0, 10),
                    textcoords="offset points",
                    ha="center",
                    fontsize=11,
                    fontweight="bold"
                )

        if min_target_month is not None:
            min_index = months.index(min_target_month)
            ax.scatter(
                min_index, min_target_value,
                s=50, color=MIN_COLOR, edgecolor="black",
                linewidth=1, zorder=5,
                label=f"Minimum {target_year}: {min_target_month} "
                      f"({min_target_value:.1f} mm)"
            )

        if max_target_month is not None:
            max_index = months.index(max_target_month)
            ax.scatter(
                max_index, max_target_value,
                s=50, color=MAX_COLOR, edgecolor="black",
                linewidth=1, zorder=5,
                label=f"Maximum {target_year}: {max_target_month} "
                      f"({max_target_value:.1f} mm)"
            )

        ax.set_title(
            f"{file_name}\nMonthly Rainfall {target_year} vs "
            f"Mean Monthly Rainfall {YEAR_RANGE_TEXT}",
            fontsize=16, fontweight="bold"
        )
        ax.set_xlabel("Month", fontsize=12)
        ax.set_ylabel("Rainfall (mm)", fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(months)
        ax.set_ylim(RAINFALL_MIN, RAINFALL_MAX)
        ax.grid(True, axis="y", linestyle="--", alpha=0.4)
        ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)

        finish_plot(fig)

    # ========================================================
    # TAB 2 - HEATMAP
    # ========================================================
    with tabs[1]:
        st.subheader(f"Monthly Total Rainfall Heatmap {YEAR_RANGE_TEXT}")

        heatmap_data = yearly_monthly_total.reindex(columns=months)
        fig, ax = plt.subplots(figsize=(14, 8))
        apply_plot_style(fig, ax)

        valid_values = heatmap_data.values[~pd.isna(heatmap_data.values)]
        if len(valid_values):
            vmin, vmax = valid_values.min(), valid_values.max()
            if vmin == vmax:
                vmax = vmin + 1
        else:
            vmin, vmax = 0, 1

        im = ax.imshow(
            heatmap_data.values,
            aspect="auto",
            cmap="YlGnBu",
            vmin=vmin,
            vmax=vmax
        )

        ax.set_xticks(range(len(months)))
        ax.set_xticklabels(months)
        ax.set_yticks(range(len(heatmap_data.index)))
        ax.set_yticklabels(heatmap_data.index.astype(str))

        ax.set_xticks([i - 0.5 for i in range(len(months) + 1)], minor=True)
        ax.set_yticks(
            [i - 0.5 for i in range(len(heatmap_data.index) + 1)],
            minor=True
        )
        ax.grid(which="minor", color="white", linestyle="-", linewidth=1)
        ax.tick_params(which="minor", bottom=False, left=False)

        for i in range(len(heatmap_data.index)):
            for j in range(len(months)):
                value = heatmap_data.iloc[i, j]

                if pd.notna(value):
                    ax.text(
                        j, i, f"{value:.0f}",
                        ha="center", va="center", fontsize=7
                    )
                else:
                    ax.add_patch(
                        plt.Rectangle(
                            (j - 0.5, i - 0.5), 1, 1,
                            facecolor="lightgray",
                            edgecolor="white",
                            linewidth=1
                        )
                    )
                    ax.text(
                        j, i, "N.A.",
                        ha="center", va="center", fontsize=7
                    )

        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Total Rainfall (mm)", fontsize=11)

        ax.set_title(
            f"{file_name}\nMonthly Total Rainfall Heatmap, "
            f"{YEAR_RANGE_TEXT}",
            fontsize=16, fontweight="bold"
        )
        ax.set_xlabel("Month", fontsize=12)
        ax.set_ylabel("Year", fontsize=12)

        finish_plot(fig)

    # ========================================================
    # TAB 3 - ANOMALY
    # ========================================================
    with tabs[2]:
        st.subheader(
            f"Rainfall Anomaly {target_year} Relative to Mean {YEAR_RANGE_TEXT}"
        )

        fig, ax = plt.subplots(figsize=(14, 8))
        apply_plot_style(fig, ax)

        anomaly_colors = [
            "lightgray" if pd.isna(value)
            else ("darkorange" if value >= 0 else "steelblue")
            for value in anomaly_percent.values
        ]

        bars = ax.bar(
            x, anomaly_percent.values,
            width=0.60,
            color=anomaly_colors,
            edgecolor="black",
            linewidth=0.8
        )

        ax.axhline(0, color="black", linewidth=1)

        for bar, value in zip(bars, anomaly_percent.values):
            if pd.notna(value):
                offset = 4 if value >= 0 else -12
                vertical = "bottom" if value >= 0 else "top"

                ax.annotate(
                    f"{value:.1f}%",
                    (
                        bar.get_x() + bar.get_width() / 2,
                        value
                    ),
                    xytext=(0, offset),
                    textcoords="offset points",
                    ha="center",
                    va=vertical,
                    fontsize=8
                )

        ax.set_title(
            f"{file_name}\nRainfall Anomaly {target_year} "
            f"Relative to Mean {YEAR_RANGE_TEXT}",
            fontsize=16, fontweight="bold"
        )
        ax.set_xlabel("Month", fontsize=12)
        ax.set_ylabel("Anomaly (%)", fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(months)
        ax.grid(True, axis="y", linestyle="--", alpha=0.4)

        finish_plot(fig)

    # ========================================================
    # TAB 4 - STATISTICS
    # ========================================================
    with tabs[3]:
        st.subheader("📋 Rainfall Statistical Analysis")

        display_table = analysis_table.copy()

        numeric_columns = display_table.columns[
            display_table.columns != "Month"
        ]

        for column in numeric_columns:
            display_table[column] = pd.to_numeric(
                display_table[column], errors="coerce"
            ).round(2)

        st.dataframe(
            display_table,
            use_container_width=True,
            hide_index=True
        )

        csv_data = analysis_table.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            label="📥 Download Statistical Analysis CSV",
            data=csv_data,
            file_name=(
                f"{file_name}_Statistical_Analysis_"
                f"{YEAR_RANGE_TEXT}.csv"
            ),
            mime="text/csv",
            key=f"stats_{file_name}"
        )

    # ========================================================
    # TAB 5 - MAX DAILY
    # ========================================================
    with tabs[4]:
        st.subheader(
            f"Maximum Daily Rainfall by Month - {target_year}"
        )

        fig, ax = plt.subplots(figsize=(14, 8))
        apply_plot_style(fig, ax)

        bars = ax.bar(
            x, max_daily,
            width=0.60,
            color=MAX_DAILY_COLOR,
            edgecolor="black",
            linewidth=0.8
        )

        for bar, value in zip(bars, max_daily):
            if pd.notna(value):
                ax.annotate(
                    f"{value:.1f}",
                    (
                        bar.get_x() + bar.get_width() / 2,
                        value
                    ),
                    xytext=(0, 6),
                    textcoords="offset points",
                    ha="center",
                    fontsize=10,
                    fontweight="bold"
                )

        ax.set_title(
            f"{file_name}\nMaximum Daily Rainfall by Month - "
            f"{target_year}",
            fontsize=16, fontweight="bold"
        )
        ax.set_xlabel("Month", fontsize=12)
        ax.set_ylabel("Maximum Daily Rainfall (mm)", fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(months)
        ax.grid(True, axis="y", linestyle="--", alpha=0.4)

        finish_plot(fig)

    # ========================================================
    # TAB 6 - WET DAYS
    # ========================================================
    with tabs[5]:
        st.subheader(
            f"Number of Wet Days (≥{WET_DAY_MIN:.1f} mm) - "
            f"{target_year}"
        )

        fig, ax = plt.subplots(figsize=(14, 8))
        apply_plot_style(fig, ax)

        bars = ax.bar(
            x, wet_days,
            width=0.60,
            color=WET_DAY_COLOR,
            edgecolor="black",
            linewidth=0.8
        )

        for bar, value in zip(bars, wet_days):
            if pd.notna(value):
                ax.annotate(
                    f"{int(value)}",
                    (
                        bar.get_x() + bar.get_width() / 2,
                        value
                    ),
                    xytext=(0, 6),
                    textcoords="offset points",
                    ha="center",
                    fontsize=10,
                    fontweight="bold"
                )

        ax.set_title(
            f"{file_name}\nNumber of Wet Days "
            f"(≥{WET_DAY_MIN:.1f} mm) - {target_year}",
            fontsize=16, fontweight="bold"
        )
        ax.set_xlabel("Month", fontsize=12)
        ax.set_ylabel("Number of Wet Days", fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(months)
        ax.grid(True, axis="y", linestyle="--", alpha=0.4)

        finish_plot(fig)

    # ========================================================
    # TAB 7 - STANDARD DEVIATION
    # ========================================================
    with tabs[6]:
        st.subheader(
            f"Daily Rainfall Standard Deviation - {target_year}"
        )

        fig, ax = plt.subplots(figsize=(14, 8))
        apply_plot_style(fig, ax)

        bars = ax.bar(
            x, std_daily,
            width=0.60,
            color=STD_COLOR,
            edgecolor="black",
            linewidth=0.8
        )

        for bar, value in zip(bars, std_daily):
            if pd.notna(value):
                ax.annotate(
                    f"{value:.1f}",
                    (
                        bar.get_x() + bar.get_width() / 2,
                        value
                    ),
                    xytext=(0, 6),
                    textcoords="offset points",
                    ha="center",
                    fontsize=10,
                    fontweight="bold"
                )

        ax.set_title(
            f"{file_name}\nDaily Rainfall Standard Deviation - "
            f"{target_year}",
            fontsize=16, fontweight="bold"
        )
        ax.set_xlabel("Month", fontsize=12)
        ax.set_ylabel("Standard Deviation (mm)", fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(months)
        ax.grid(True, axis="y", linestyle="--", alpha=0.4)

        finish_plot(fig)

    # ========================================================
    # TAB 8 - HISTOGRAM
    # ========================================================
    with tabs[7]:
        st.subheader(
            f"Distribution of Daily Rainfall - {target_year}"
        )

        if len(hist_values) > 0:
            fig, ax = plt.subplots(figsize=(14, 8))
            apply_plot_style(fig, ax)

            ax.hist(
                hist_values,
                bins=15,
                color=HIST_COLOR,
                edgecolor="black",
                linewidth=0.8
            )

            ax.set_title(
                f"{file_name}\nDistribution of Daily Rainfall - "
                f"{target_year}",
                fontsize=16, fontweight="bold"
            )
            ax.set_xlabel("Daily Rainfall (mm)", fontsize=12)
            ax.set_ylabel("Number of Days", fontsize=12)
            ax.grid(True, axis="y", linestyle="--", alpha=0.4)

            finish_plot(fig)
        else:
            st.warning(
                f"Tiada data hujan ≥ {WET_DAY_MIN:.1f} mm untuk histogram."
            )

    # ========================================================
    # TAB 9 - PIE CHART
    # ========================================================
    with tabs[8]:
        st.subheader(
            f"Percentage of Days by Rainfall Category - {target_year}"
        )

        if sum(category_values) > 0:
            fig, ax = plt.subplots(figsize=(10, 8))
            apply_plot_style(fig, ax)

            wedges, texts, autotexts = ax.pie(
                category_values,
                labels=category_labels,
                autopct="%1.1f%%",
                startangle=90,
                counterclock=False,
                wedgeprops={
                    "edgecolor": "black",
                    "linewidth": 0.8
                }
            )

            for autotext in autotexts:
                autotext.set_fontsize(11)
                autotext.set_fontweight("bold")

            ax.set_title(
                f"{file_name}\nPercentage of Days by Rainfall "
                f"Category - {target_year}",
                fontsize=16, fontweight="bold"
            )

            finish_plot(fig)

            total_days = sum(category_values)

            category_table = pd.DataFrame({
                "Rainfall Category": category_labels,
                "Number of Days": category_values,
                "Percentage (%)": [
                    (count / total_days) * 100
                    for count in category_values
                ]
            })
            category_table["Percentage (%)"] = (
                category_table["Percentage (%)"].round(2)
            )

            st.dataframe(
                category_table,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("Tiada data sah untuk pie chart.")

    # ========================================================
    # TAB 10 - QC
    # ========================================================
    with tabs[9]:
        st.subheader("⚠️ Quality Control")

        st.markdown(f"""
        **QC Rules**

        - `0.0 mm` = data sah
        - `≥ {WET_DAY_MIN:.1f} mm` = wet day
        - `> {SUSPECT_RAINFALL:.0f} mm` = suspect
        - `> {EXTREME_RAINFALL:.0f} mm` = extreme
        - Negative rainfall = invalid / dibuang
        - Missing days `> {MAX_MISSING_DAYS}` = bulan ditolak
        - Missing berturut-turut `> {MAX_CONSECUTIVE_MISSING}` = bulan ditolak
        """)

        qc_tabs = st.tabs([
            "⚠️ Suspect",
            "🚨 Extreme",
            "📅 Missing Count",
            "🔢 Valid Count",
            "🔁 Consecutive Missing",
            "📋 QC Status"
        ])

        with qc_tabs[0]:
            st.write(
                f"Jumlah suspect rainfall > {SUSPECT_RAINFALL:.0f} mm: "
                f"**{len(suspect_df)}**"
            )

            if len(suspect_df):
                st.dataframe(
                    suspect_df,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "📥 Download Suspect CSV",
                    suspect_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name=(
                        f"{file_name}_Suspect_Rainfall_GT"
                        f"{SUSPECT_RAINFALL:.0f}mm.csv"
                    ),
                    mime="text/csv",
                    key=f"suspect_{file_name}"
                )
            else:
                st.success("Tiada rainfall suspect dikesan.")

        with qc_tabs[1]:
            st.write(
                f"Jumlah extreme rainfall > {EXTREME_RAINFALL:.0f} mm: "
                f"**{len(extreme_df)}**"
            )

            if len(extreme_df):
                st.dataframe(
                    extreme_df,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "📥 Download Extreme CSV",
                    extreme_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name=(
                        f"{file_name}_Extreme_Rainfall_GT"
                        f"{EXTREME_RAINFALL:.0f}mm.csv"
                    ),
                    mime="text/csv",
                    key=f"extreme_{file_name}"
                )
            else:
                st.success("Tiada rainfall extreme dikesan.")

        with qc_tabs[2]:
            st.dataframe(
                monthly_missing_count,
                use_container_width=True
            )

        with qc_tabs[3]:
            st.dataframe(
                monthly_valid_count,
                use_container_width=True
            )

        with qc_tabs[4]:
            st.dataframe(
                monthly_max_consecutive_missing,
                use_container_width=True
            )

        with qc_tabs[5]:
            st.dataframe(
                monthly_qc_status,
                use_container_width=True
            )

# ============================================================
# DOWNLOAD ALL RESULTS AS ZIP
# ============================================================
st.divider()
st.header("📦 Download Analysis Results")
st.write(
    "Muat turun semua jadual analisis, QC dan data suspect/extreme "
    "sebagai satu fail ZIP."
)

zip_buffer = io.BytesIO()

with zipfile.ZipFile(
    zip_buffer, "w", zipfile.ZIP_DEFLATED
) as zip_file:

    for result in successful_results:
        file_name = result["file_name"]

        outputs = {
            f"{file_name}_Statistical_Analysis_{YEAR_RANGE_TEXT}.csv":
                result["analysis_table"].to_csv(index=False),
            f"{file_name}_Monthly_Total_{YEAR_RANGE_TEXT}.csv":
                result["yearly_monthly_total"].to_csv(),
            f"{file_name}_Missing_Days_{YEAR_RANGE_TEXT}.csv":
                result["monthly_missing_count"].to_csv(),
            f"{file_name}_Valid_Days_{YEAR_RANGE_TEXT}.csv":
                result["monthly_valid_count"].to_csv(),
            f"{file_name}_Consecutive_Missing_{YEAR_RANGE_TEXT}.csv":
                result["monthly_max_consecutive_missing"].to_csv(),
            f"{file_name}_QC_Status_{YEAR_RANGE_TEXT}.csv":
                result["monthly_qc_status"].to_csv(),
            f"{file_name}_Suspect_Rainfall.csv":
                result["suspect_df"].to_csv(index=False),
            f"{file_name}_Extreme_Rainfall.csv":
                result["extreme_df"].to_csv(index=False)
        }

        for output_name, content in outputs.items():
            zip_file.writestr(
                f"{file_name}/{output_name}",
                content
            )

zip_buffer.seek(0)

st.download_button(
    label="📦 Download All Results (ZIP)",
    data=zip_buffer.getvalue(),
    file_name=(
        f"Rainfall_Analysis_{YEAR_RANGE_TEXT}_"
        f"Target_{target_year}.zip"
    ),
    mime="application/zip",
    key="download_all_results"
)

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption(
    "🌧️ Rainfall Data Analysis | Quality Control, "
    "Climatological Mean, Anomaly and Statistical Analysis"
)

print(f"Created {path}")
print(f"Lines: {len(app_code.splitlines())}")
