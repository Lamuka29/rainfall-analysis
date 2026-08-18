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
st.caption(
    "Pemprosesan, Quality Control dan Analisis Data Hujan Harian"
)


# ============================================================
# SIDEBAR SETTINGS
# ============================================================

st.sidebar.header("⚙️ Analysis Settings")


# ============================================================
# TAHUN CLIMATOLOGY
# ============================================================

START_YEAR = st.sidebar.number_input(
    "Start Year",
    min_value=1900,
    max_value=2100,
    value=2016,
    step=1
)

END_YEAR = st.sidebar.number_input(
    "End Year",
    min_value=1900,
    max_value=2100,
    value=2025,
    step=1
)

if START_YEAR > END_YEAR:
    st.sidebar.error(
        "Start Year mesti lebih kecil atau sama dengan End Year."
    )
    st.stop()

years = range(
    int(START_YEAR),
    int(END_YEAR) + 1
)

YEAR_RANGE_TEXT = (
    f"{int(START_YEAR)}–{int(END_YEAR)}"
)


# ============================================================
# TARGET YEAR
# ============================================================

target_year = st.sidebar.number_input(
    "Target Year",
    min_value=1900,
    max_value=2100,
    value=2018,
    step=1
)

target_year = int(target_year)

# ============================================================
# FILE UPLOAD
# ============================================================

uploaded_files = st.file_uploader(
    "📁 Upload Excel file",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if not uploaded_files:

    st.info(
        "Sila upload sekurang-kurangnya satu fail Excel."
    )

    st.stop()

# ============================================================
# WMO MISSING DATA RULE
# ============================================================

st.sidebar.subheader("WMO Missing Data Rule")

MAX_MISSING_DAYS = st.sidebar.number_input(
    "Maximum missing days",
    min_value=0,
    max_value=31,
    value=10,
    step=1,
    help=(
        "Bulan ditolak jika bilangan missing days melebihi "
        "nilai ini. Default 10 bermaksud >=11 missing days ditolak."
    )
)

MAX_CONSECUTIVE_MISSING = st.sidebar.number_input(
    "Maximum consecutive missing days",
    min_value=1,
    max_value=31,
    value=4,
    step=1,
    help=(
        "Bulan ditolak jika terdapat missing days berturut-turut "
        "melebihi nilai ini. Default 4 bermaksud >=5 berturut-turut ditolak."
    )
)


# ============================================================
# RAINFALL THRESHOLDS
# ============================================================

st.sidebar.subheader("🌧️ Rainfall Threshold")

VALID_MIN = 0.0

WET_DAY_MIN = st.sidebar.number_input(
    "Wet day threshold (mm)",
    min_value=0.0,
    value=0.1,
    step=0.1
)

SUSPECT_RAINFALL = st.sidebar.number_input(
    "Suspect threshold (mm)",
    min_value=0.0,
    value=150.0,
    step=10.0
)

EXTREME_RAINFALL = st.sidebar.number_input(
    "Extreme threshold (mm)",
    min_value=0.0,
    value=250.0,
    step=10.0
)


# ============================================================
# MONTHS
# ============================================================

months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]


# ============================================================
# GRAPH SETTINGS
# ============================================================

RAINFALL_MIN = 0
RAINFALL_MAX = 500

# ============================================================
# PLOT SETTINGS - USER BOLEH UBAH
# ============================================================

st.sidebar.header("🎨 Plot Settings")

# ------------------------------------------------------------
# FILE / STATION LIST
# ------------------------------------------------------------

file_names_for_color = [
    uploaded_file.name
    for uploaded_file in uploaded_files
]

# ============================================================
# BACKGROUND
# ============================================================

BG_COLOR = st.sidebar.color_picker(
    "Background Graf",
    "#FFFFFF"
)


# ============================================================
# DEFAULT BAR COLORS - MONTHLY RAINFALL
# ============================================================

default_colors = [
    "#4682B4",  # Jan
    "#87CEEB",  # Feb
    "#3CB371",  # Mar
    "#32CD32",  # Apr
    "#FFD700",  # May
    "#FFA500",  # Jun
    "#FF7F50",  # Jul
    "#FF6347",  # Aug
    "#9370DB",  # Sep
    "#DA70D6",  # Oct
    "#6A5ACD",  # Nov
    "#008080"   # Dec
]


# ============================================================
# SESSION STATE
# Supaya warna yang dipilih tidak reset
# ============================================================

if "bar_colors" not in st.session_state:

    st.session_state.bar_colors = default_colors.copy()


if "max_daily_color" not in st.session_state:

    st.session_state.max_daily_color = "#FF6347"


if "wet_days_color" not in st.session_state:

    st.session_state.wet_days_color = "#3CB371"


if "std_color" not in st.session_state:

    st.session_state.std_color = "#9370DB"


if "hist_color" not in st.session_state:

    st.session_state.hist_color = "#4682B4"


# ============================================================
# SELECT BAR CHART
# ============================================================

chart_options = [
    "Monthly Rainfall",
    "Maximum Daily Rainfall",
    "Wet Days",
    "Standard Deviation",
    "Histogram"
]

selected_chart = st.sidebar.selectbox(
    "Select Bar Chart",
    chart_options
)


# ============================================================
# MONTHLY RAINFALL
# ============================================================

if selected_chart == "Monthly Rainfall":

    selected_month = st.sidebar.selectbox(
        "Select Month",
        months
    )

    selected_index = months.index(
        selected_month
    )

    st.session_state.bar_colors[
        selected_index
    ] = st.sidebar.color_picker(
        f"{selected_month} Bar Colour",
        st.session_state.bar_colors[selected_index]
    )


# ============================================================
# MAXIMUM DAILY RAINFALL
# ============================================================

elif selected_chart == "Maximum Daily Rainfall":

    st.session_state.max_daily_color = (
        st.sidebar.color_picker(
            "Maximum Daily Rainfall Colour",
            st.session_state.max_daily_color
        )
    )


# ============================================================
# WET DAYS
# ============================================================

elif selected_chart == "Wet Days":

    st.session_state.wet_days_color = (
        st.sidebar.color_picker(
            "Wet Days Colour",
            st.session_state.wet_days_color
        )
    )


# ============================================================
# STANDARD DEVIATION
# ============================================================

elif selected_chart == "Standard Deviation":

    st.session_state.std_color = (
        st.sidebar.color_picker(
            "Standard Deviation Colour",
            st.session_state.std_color
        )
    )


# ============================================================
# HISTOGRAM
# ============================================================

elif selected_chart == "Histogram":

    st.session_state.hist_color = (
        st.sidebar.color_picker(
            "Histogram Colour",
            st.session_state.hist_color
        )
    )


# ============================================================
# MEAN LINE
# ============================================================

LINE_COLOR = st.sidebar.color_picker(
    "Mean Line",
    "#000000"
)


# ============================================================
# MINIMUM
# ============================================================

MIN_COLOR = st.sidebar.color_picker(
    "Minimum",
    "#008000"
)


# ============================================================
# MAXIMUM
# ============================================================

MAX_COLOR = st.sidebar.color_picker(
    "Maximum",
    "#FF0000"
)


# ============================================================
# FIGURE SIZE
# ============================================================

FIG_WIDTH = 14
FIG_HEIGHT = 9

# ============================================================
# BACKGROUND COLORS
# ============================================================

BACKGROUND_COLORS = {
    "_ PUSAT PEMULIHAN ORANG UTAN SEPILOK.xlsx": "#EAF4F8",
    "Tawau Agriculture 1995 - 2025.xlsx": "#F5F0E6"
}

# ============================================================
# FUNCTION
# MAXIMUM CONSECUTIVE MISSING
# ============================================================

def max_consecutive_missing(values):

    is_missing = values.isna()

    max_missing = 0
    current_missing = 0

    for missing in is_missing:

        if missing:

            current_missing += 1

            if current_missing > max_missing:
                max_missing = current_missing

        else:

            current_missing = 0

    return max_missing


# ============================================================
# FUNCTION
# READ YEAR SHEET
# ============================================================

def read_year_sheet(uploaded_file, year):

    try:

        file_bytes = uploaded_file.getvalue()

        df = pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=str(year),
            header=6
        )

    except Exception as e:

        return None, str(e)

    if df is None or df.empty:

        return None, "Sheet kosong."

    # --------------------------------------------------------
    # Ambil 13 column pertama
    # --------------------------------------------------------

    if df.shape[1] < 13:

        return None, (
            f"Bilangan column tidak mencukupi "
            f"({df.shape[1]} column dikesan). "
            f"Minimum 13 column diperlukan."
        )

    df = df.iloc[:, :13].copy()

    df.columns = [
        "hari",
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    # --------------------------------------------------------
    # Convert day
    # --------------------------------------------------------

    df["hari"] = pd.to_numeric(
        df["hari"],
        errors="coerce"
    )

    df = df[
        df["hari"].between(1, 31)
    ].copy()

    # --------------------------------------------------------
    # Convert rainfall
    # --------------------------------------------------------

    for month in months:

        df[month] = pd.to_numeric(
            df[month],
            errors="coerce"
        )

        # Negative = invalid
        df.loc[
            df[month] < VALID_MIN,
            month
        ] = np.nan

    df["Year"] = int(year)

    return df, None


# ============================================================
# FUNCTION
# ANALYZE ONE FILE
# ============================================================

def analyze_file(uploaded_file):

    file_name = os.path.splitext(
        uploaded_file.name
    )[0]

    original_file_name = uploaded_file.name

    daily_results = []
    read_errors = []

    # ========================================================
    # READ ALL YEARS
    # ========================================================

    for year in years:

        df, error = read_year_sheet(
            uploaded_file,
            year
        )

        if df is not None:

            daily_results.append(df)

        else:

            read_errors.append({
                "Year": int(year),
                "Error": error
            })

    # ========================================================
    # CHECK DATA
    # ========================================================

    if len(daily_results) == 0:

        return {
            "success": False,
            "file_name": file_name,
            "original_file_name": original_file_name,
            "error": "Tiada sheet tahun berjaya dibaca."
        }

    # ========================================================
    # COMBINE DATA
    # ========================================================

    all_daily = pd.concat(
        daily_results,
        ignore_index=True
    )

    # ========================================================
    # QUALITY CONTROL
    # ========================================================

    for month in months:

        all_daily.loc[
            all_daily[month] < VALID_MIN,
            month
        ] = np.nan

    # ========================================================
    # SUSPECT & EXTREME
    # ========================================================

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
                    "Year": year,
                    "Day": day,
                    "Month": month,
                    "Rainfall (mm)": value,
                    "Status": "EXTREME - DOUBLE CHECK"
                })

            elif value > SUSPECT_RAINFALL:

                suspect_records.append({
                    "Year": year,
                    "Day": day,
                    "Month": month,
                    "Rainfall (mm)": value,
                    "Status": "SUSPECT - SEMAK"
                })

    suspect_df = pd.DataFrame(
        suspect_records,
        columns=[
            "Year",
            "Day",
            "Month",
            "Rainfall (mm)",
            "Status"
        ]
    )

    extreme_df = pd.DataFrame(
        extreme_records,
        columns=[
            "Year",
            "Day",
            "Month",
            "Rainfall (mm)",
            "Status"
        ]
    )

    # ========================================================
    # YEARLY MONTHLY TOTAL
    # ========================================================

    available_years = sorted(
        all_daily["Year"].unique()
    )

    yearly_monthly_total = pd.DataFrame(
        index=available_years,
        columns=months,
        dtype=float
    )

    monthly_missing_count = pd.DataFrame(
        index=available_years,
        columns=months,
        dtype=float
    )

    monthly_valid_count = pd.DataFrame(
        index=available_years,
        columns=months,
        dtype=float
    )

    monthly_max_consecutive_missing = pd.DataFrame(
        index=available_years,
        columns=months,
        dtype=float
    )

    monthly_qc_status = pd.DataFrame(
        index=available_years,
        columns=months,
        dtype=object
    )

    # ========================================================
    # LOOP YEAR & MONTH
    # ========================================================

    for year in available_years:

        year_data = all_daily[
            all_daily["Year"] == year
        ]

        for month in months:

            month_index = (
                months.index(month) + 1
            )

            days_expected = calendar.monthrange(
                int(year),
                month_index
            )[1]

            values = (
                year_data[month]
                .iloc[:days_expected]
                .copy()
            )

            valid_values = values[
                values.notna() &
                (values >= VALID_MIN)
            ]

            valid_count = len(
                valid_values
            )

            missing_count = (
                days_expected -
                valid_count
            )

            max_consecutive = (
                max_consecutive_missing(values)
            )

            monthly_valid_count.loc[
                year,
                month
            ] = valid_count

            monthly_missing_count.loc[
                year,
                month
            ] = missing_count

            monthly_max_consecutive_missing.loc[
                year,
                month
            ] = max_consecutive

            # ------------------------------------------------
            # ACCEPT / REJECT
            #
            # Default:
            # >10 missing = reject
            # >=5 consecutive = reject
            # ------------------------------------------------

            if (
                missing_count <= MAX_MISSING_DAYS
                and
                max_consecutive <= MAX_CONSECUTIVE_MISSING
            ):

                yearly_monthly_total.loc[
                    year,
                    month
                ] = valid_values.sum()

                monthly_qc_status.loc[
                    year,
                    month
                ] = "ACCEPT"

            else:

                yearly_monthly_total.loc[
                    year,
                    month
                ] = np.nan

                if missing_count > MAX_MISSING_DAYS:

                    monthly_qc_status.loc[
                        year,
                        month
                    ] = (
                        f"REJECT: >{MAX_MISSING_DAYS} "
                        f"MISSING"
                    )

                elif (
                    max_consecutive >
                    MAX_CONSECUTIVE_MISSING
                ):

                    monthly_qc_status.loc[
                        year,
                        month
                    ] = (
                        f"REJECT: >"
                        f"{MAX_CONSECUTIVE_MISSING} "
                        f"CONSECUTIVE MISSING"
                    )

                else:

                    monthly_qc_status.loc[
                        year,
                        month
                    ] = "REJECT"

    # ========================================================
    # TARGET YEAR CHECK
    # ========================================================

    if target_year not in yearly_monthly_total.index:

        return {
            "success": False,
            "file_name": file_name,
            "original_file_name": original_file_name,
            "error": (
                f"Data tahun {target_year} tidak dijumpai."
            ),
            "available_years": available_years
        }

    # ========================================================
    # TARGET YEAR MONTHLY TOTAL
    # ========================================================

    rainfall_target = (
        yearly_monthly_total
        .loc[target_year]
        .reindex(months)
    )

    # ========================================================
    # CLIMATOLOGICAL MONTHLY MEAN
    # ========================================================

    mean_monthly_total = (
        yearly_monthly_total
        .mean(
            axis=0,
            skipna=True
        )
        .reindex(months)
    )

    # ========================================================
    # ANOMALY
    # ========================================================

    anomaly_percent = (
        (
            rainfall_target -
            mean_monthly_total
        )
        /
        mean_monthly_total
    ) * 100

    anomaly_percent[
        mean_monthly_total == 0
    ] = np.nan

    # ========================================================
    # TARGET YEAR MINIMUM / MAXIMUM
    # ========================================================

    valid_target = rainfall_target.dropna()

    if len(valid_target) > 0:

        min_target_month = valid_target.idxmin()
        min_target_value = valid_target.min()

        max_target_month = valid_target.idxmax()
        max_target_value = valid_target.max()

    else:

        min_target_month = None
        min_target_value = None

        max_target_month = None
        max_target_value = None

    # ========================================================
    # MEAN MINIMUM / MAXIMUM
    # ========================================================

    valid_mean = mean_monthly_total.dropna()

    if len(valid_mean) > 0:

        min_mean_month = valid_mean.idxmin()
        min_mean_value = valid_mean.min()

        max_mean_month = valid_mean.idxmax()
        max_mean_value = valid_mean.max()

    else:

        min_mean_month = None
        min_mean_value = None

        max_mean_month = None
        max_mean_value = None

    # ========================================================
    # DAILY STATISTICS
    # ========================================================

    median_daily = []
    std_daily = []
    max_daily = []
    min_daily = []

    wet_days = []
    valid_data_percent = []

    suspect_count = []
    extreme_count = []

    target_data = all_daily[
        all_daily["Year"] == target_year
    ].copy()

    for month in months:

        month_index = (
            months.index(month) + 1
        )

        days_expected = calendar.monthrange(
            target_year,
            month_index
        )[1]

        raw_values = target_data[
            month
        ].iloc[:days_expected].copy()

        # ----------------------------------------------------
        # QC VALUES
        # ----------------------------------------------------

        qc_values = raw_values[
            raw_values.notna() &
            (raw_values >= VALID_MIN)
        ]

        # ----------------------------------------------------
        # WET DAY VALUES
        # ----------------------------------------------------

        values = qc_values[
            qc_values >= WET_DAY_MIN
        ]

        # ----------------------------------------------------
        # VALID DATA %
        # ----------------------------------------------------

        valid_count = len(qc_values)

        percent = (
            valid_count /
            days_expected
        ) * 100

        valid_data_percent.append(
            percent
        )

        # ----------------------------------------------------
        # MEDIAN
        # ----------------------------------------------------

        if len(values) > 0:
            median_daily.append(
                values.median()
            )
        else:
            median_daily.append(np.nan)

        # ----------------------------------------------------
        # STANDARD DEVIATION
        # ----------------------------------------------------

        if len(values) > 1:
            std_daily.append(
                values.std()
            )
        else:
            std_daily.append(np.nan)

        # ----------------------------------------------------
        # MAX
        # ----------------------------------------------------

        if len(values) > 0:
            max_daily.append(
                values.max()
            )
        else:
            max_daily.append(np.nan)

        # ----------------------------------------------------
        # MIN
        # ----------------------------------------------------

        if len(values) > 0:
            min_daily.append(
                values.min()
            )
        else:
            min_daily.append(np.nan)

        # ----------------------------------------------------
        # WET DAYS
        # ----------------------------------------------------

        wet_days.append(
            (
                qc_values >= WET_DAY_MIN
            ).sum()
        )

        # ----------------------------------------------------
        # SUSPECT DAYS
        # ----------------------------------------------------

        suspect_count.append(
            (
                values >
                SUSPECT_RAINFALL
            ).sum()
        )

        # ----------------------------------------------------
        # EXTREME DAYS
        # ----------------------------------------------------

        extreme_count.append(
            (
                values >
                EXTREME_RAINFALL
            ).sum()
        )

    # ========================================================
    # ANALYSIS TABLE
    # ========================================================

    analysis_table = pd.DataFrame({

        "Month":
            months,

        f"Total {target_year} (mm)":
            rainfall_target.values,

        f"Mean {YEAR_RANGE_TEXT} (mm)":
            mean_monthly_total.values,

        f"Anomaly {target_year} (%)":
            anomaly_percent.values,

        "Median Daily (>=0.1 mm)":
            median_daily,

        "SD Daily (>=0.1 mm)":
            std_daily,

        "Maximum Daily (>=0.1 mm)":
            max_daily,

        "Minimum Daily (>=0.1 mm)":
            min_daily,

        "Wet Days (>=0.1 mm)":
            wet_days,

        "Suspect Days (>150 mm)":
            suspect_count,

        "Extreme Days (>250 mm)":
            extreme_count,

        "Valid Data (>=0.0 mm) (%)":
            valid_data_percent
    })

    # ========================================================
    # HISTOGRAM DATA
    # ========================================================

    hist_values = []

    for month in months:

        month_index = (
            months.index(month) + 1
        )

        days_expected = calendar.monthrange(
            target_year,
            month_index
        )[1]

        raw_values = target_data[
            month
        ].iloc[:days_expected].copy()

        values = raw_values[
            raw_values.notna() &
            (raw_values >= VALID_MIN)
        ]

        values = values[
            values >= WET_DAY_MIN
        ]

        hist_values.extend(
            values.tolist()
        )

    # ========================================================
    # PIE DATA
    # ========================================================

    pie_values = []

    for month in months:

        month_index = (
            months.index(month) + 1
        )

        days_expected = calendar.monthrange(
            target_year,
            month_index
        )[1]

        raw_values = target_data[
            month
        ].iloc[:days_expected].copy()

        values = raw_values[
            raw_values.notna() &
            (raw_values >= VALID_MIN)
        ]

        pie_values.extend(
            values.tolist()
        )

    no_rain = sum(
        value == 0.0
        for value in pie_values
    )

    light_rain = sum(
        0.1 <= value <= 10.0
        for value in pie_values
    )

    moderate_rain = sum(
        10.0 < value <= 50.0
        for value in pie_values
    )

    heavy_rain = sum(
        value > 50.0
        for value in pie_values
    )

    category_values = [
        no_rain,
        light_rain,
        moderate_rain,
        heavy_rain
    ]

    category_labels = [
        "No Rain (0.0 mm)",
        "Light Rain (0.1–10 mm)",
        "Moderate Rain (>10–50 mm)",
        "Heavy Rain (>50 mm)"
    ]

    # ========================================================
    # RETURN RESULTS
    # ========================================================

    return {

        "success": True,

        "file_name": file_name,

        "original_file_name":
            original_file_name,

        "all_daily":
            all_daily,

        "yearly_monthly_total":
            yearly_monthly_total,

        "monthly_missing_count":
            monthly_missing_count,

        "monthly_valid_count":
            monthly_valid_count,

        "monthly_max_consecutive_missing":
            monthly_max_consecutive_missing,

        "monthly_qc_status":
            monthly_qc_status,

        "rainfall_target":
            rainfall_target,

        "mean_monthly_total":
            mean_monthly_total,

        "anomaly_percent":
            anomaly_percent,

        "min_target_month":
            min_target_month,

        "min_target_value":
            min_target_value,

        "max_target_month":
            max_target_month,

        "max_target_value":
            max_target_value,

        "min_mean_month":
            min_mean_month,

        "min_mean_value":
            min_mean_value,

        "max_mean_month":
            max_mean_month,

        "max_mean_value":
            max_mean_value,

        "median_daily":
            median_daily,

        "std_daily":
            std_daily,

        "max_daily":
            max_daily,

        "min_daily":
            min_daily,

        "wet_days":
            wet_days,

        "valid_data_percent":
            valid_data_percent,

        "suspect_count":
            suspect_count,

        "extreme_count":
            extreme_count,

        "analysis_table":
            analysis_table,

        "suspect_df":
            suspect_df,

        "extreme_df":
            extreme_df,

        "hist_values":
            hist_values,

        "category_values":
            category_values,

        "category_labels":
            category_labels,

        "read_errors":
            read_errors
    }


# ============================================================
# PROCESS ALL UPLOADED FILES
# ============================================================

with st.spinner(
    "⏳ Sedang memproses semua fail Excel..."
):

    results = []

    progress_bar = st.progress(0)

    for i, uploaded_file in enumerate(
        uploaded_files
    ):

        result = analyze_file(
            uploaded_file
        )

        results.append(result)

        progress_bar.progress(
            int(
                ((i + 1) /
                 len(uploaded_files)) * 100
            )
        )

    progress_bar.empty()


# ============================================================
# CHECK RESULTS
# ============================================================

successful_results = [
    result
    for result in results
    if result.get("success", False)
]

failed_results = [
    result
    for result in results
    if not result.get("success", False)
]


# ============================================================
# FILE SUMMARY
# ============================================================

st.success(
    f"✅ {len(successful_results)} daripada "
    f"{len(uploaded_files)} fail berjaya dianalisis."
)

if failed_results:

    st.warning(
        f"⚠️ {len(failed_results)} fail tidak berjaya dianalisis."
    )

    for result in failed_results:

        st.error(
            f"{result.get('original_file_name', 'Unknown')}: "
            f"{result.get('error', 'Unknown error')}"
        )


if not successful_results:
    st.stop()

# ============================================================
# STATION SELECTION
# ============================================================

station_options = {
    result["original_file_name"]: result
    for result in successful_results
}

selected_station = st.sidebar.selectbox(
    "📍 Select Station",
    list(station_options.keys())
)

selected_result = station_options[selected_station]


# ============================================================
# DISPLAY SELECTED STATION ONLY
# ============================================================

result = selected_result

file_name = result["file_name"]
original_file_name = result["original_file_name"]

all_daily = result["all_daily"]
yearly_monthly_total = result["yearly_monthly_total"]


# ============================================================
# GLOBAL AUTO Y-AXIS
# ============================================================

global_max_total = 0
global_max_mean = 0

max_total_file = None
max_total_month = None

max_mean_file = None
max_mean_month = None


rainfall_target = result["rainfall_target"]
mean_monthly_total = result["mean_monthly_total"]


if rainfall_target.notna().any():

    local_max = rainfall_target.max()

    if local_max > global_max_total:

        global_max_total = local_max

        max_total_file = result[
            "original_file_name"
        ]

        max_total_month = rainfall_target.idxmax()


if mean_monthly_total.notna().any():

    local_max = mean_monthly_total.max()

    if local_max > global_max_mean:

        global_max_mean = local_max

        max_mean_file = result[
            "original_file_name"
        ]

        max_mean_month = mean_monthly_total.idxmax()


selected_max = max(
    global_max_total,
    global_max_mean
)


if selected_max > 0:

    RAINFALL_MAX = (
        int(selected_max / 100) + 1
    ) * 100

else:

    RAINFALL_MAX = 100


# ============================================================
# GLOBAL SUMMARY
# ============================================================

st.subheader("📌 Overall Analysis Summary")

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)


with summary_col1:

    st.metric(
        "Files Analysed",
        len(successful_results)
    )


with summary_col2:

    st.metric(
        "Target Year",
        target_year
    )


with summary_col3:

    st.metric(
        "Climatology",
        YEAR_RANGE_TEXT
    )


with summary_col4:

    st.metric(
        "Auto Y-Axis Maximum",
        f"{RAINFALL_MAX:.0f} mm"
    )


# ============================================================
# GLOBAL AUTO Y-AXIS INFORMATION
# ============================================================

with st.expander(
    "🔎 Auto Y-Axis Information"
):

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            "**Maximum Target-Year Monthly Total**"
        )

        st.write(
            f"Value: {global_max_total:.2f} mm"
        )

        st.write(
            f"File: {max_total_file}"
        )

        st.write(
            f"Month: {max_total_month}"
        )


    with col2:

        st.write(
            "**Maximum Climatological Monthly Mean**"
        )

        st.write(
            f"Value: {global_max_mean:.2f} mm"
        )

        st.write(
            f"File: {max_mean_file}"
        )

        st.write(
            f"Month: {max_mean_month}"
        )


# ============================================================
# DISPLAY SELECTED FILE
# ============================================================

result = selected_result

file_name = result["file_name"]

original_file_name = result[
    "original_file_name"
]

all_daily = result[
    "all_daily"
]

yearly_monthly_total = result[
    "yearly_monthly_total"
]

monthly_missing_count = result[
    "monthly_missing_count"
]

monthly_valid_count = result[
    "monthly_valid_count"
]

monthly_max_consecutive_missing = result[
    "monthly_max_consecutive_missing"
]

monthly_qc_status = result[
    "monthly_qc_status"
]

rainfall_target = result[
    "rainfall_target"
]

mean_monthly_total = result[
    "mean_monthly_total"
]

anomaly_percent = result[
    "anomaly_percent"
]

min_target_month = result[
    "min_target_month"
]

min_target_value = result[
    "min_target_value"
]

max_target_month = result[
    "max_target_month"
]

max_target_value = result[
    "max_target_value"
]

min_mean_month = result[
    "min_mean_month"
]

min_mean_value = result[
    "min_mean_value"
]

max_mean_month = result[
    "max_mean_month"
]

max_mean_value = result[
    "max_mean_value"
]

median_daily = result[
    "median_daily"
]

std_daily = result[
    "std_daily"
]

max_daily = result[
    "max_daily"
]

min_daily = result[
    "min_daily"
]

wet_days = result[
    "wet_days"
]

valid_data_percent = result[
    "valid_data_percent"
]

analysis_table = result[
    "analysis_table"
]

suspect_df = result[
    "suspect_df"
]

extreme_df = result[
    "extreme_df"
]

hist_values = result[
    "hist_values"
]

category_values = result[
    "category_values"
]

category_labels = result[
    "category_labels"
]

read_errors = result[
    "read_errors"
]


# ========================================================
# FILE HEADER
# ========================================================

st.divider()

st.header(
    f"📁 {original_file_name}"
)


# ========================================================
# READ ERROR
# ========================================================

if read_errors:

    with st.expander(
        "⚠️ Sheet yang tidak berjaya dibaca"
    ):

        error_df = pd.DataFrame(
            read_errors
        )

        st.dataframe(
            error_df,
            use_container_width=True,
            hide_index=True
        )


# ========================================================
# BASIC METRICS
# ========================================================

col1, col2, col3, col4 = st.columns(4)


with col1:

    if (
        min_target_month is not None
        and min_target_value is not None
    ):

        st.metric(
            f"Minimum {target_year}",
            f"{min_target_value:.2f} mm",
            min_target_month
        )

    else:

        st.metric(
            f"Minimum {target_year}",
            "N.A."
        )


with col2:

    if (
        max_target_month is not None
        and max_target_value is not None
    ):

        st.metric(
            f"Maximum {target_year}",
            f"{max_target_value:.2f} mm",
            max_target_month
        )

    else:

        st.metric(
            f"Maximum {target_year}",
            "N.A."
        )


with col3:

    if (
        min_mean_month is not None
        and min_mean_value is not None
    ):

        st.metric(
            "Minimum Mean",
            f"{min_mean_value:.2f} mm",
            min_mean_month
        )

    else:

        st.metric(
            "Minimum Mean",
            "N.A."
        )


with col4:

    if (
        max_mean_month is not None
        and max_mean_value is not None
    ):

        st.metric(
            "Maximum Mean",
            f"{max_mean_value:.2f} mm",
            max_mean_month
        )

    else:

        st.metric(
            "Maximum Mean",
            "N.A."
        )


# ========================================================
# QC SUMMARY
# ========================================================

qc_col1, qc_col2, qc_col3 = st.columns(3)


with qc_col1:

    st.metric(
        "Suspect Records",
        len(suspect_df)
    )


with qc_col2:

    st.metric(
        "Extreme Records",
        len(extreme_df)
    )


with qc_col3:

    st.metric(
        "Valid Daily Records",
        int(
            (
                all_daily[months]
                .notna()
                .sum()
                .sum()
            )
        )
    )


# ========================================================
# TABS
# ========================================================

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

# ============================================================
# DOWNLOAD ALL RESULTS AS ZIP
# ============================================================

st.divider()

st.header(
    "📦 Download Analysis Results"
)

st.write(
    "Muat turun semua jadual analisis, QC dan data "
    "suspect/extreme sebagai satu fail ZIP."
)


zip_buffer = io.BytesIO()


with zipfile.ZipFile(
    zip_buffer,
    "w",
    zipfile.ZIP_DEFLATED
) as zip_file:

    result = selected_result

    file_name = result[
        "file_name"
    ]

    analysis_table = result[
        "analysis_table"
    ]

    suspect_df = result[
        "suspect_df"
    ]

    extreme_df = result[
        "extreme_df"
    ]

    yearly_monthly_total = result[
        "yearly_monthly_total"
    ]

    monthly_missing_count = result[
        "monthly_missing_count"
    ]

    monthly_valid_count = result[
        "monthly_valid_count"
    ]

    monthly_max_consecutive_missing = result[
        "monthly_max_consecutive_missing"
    ]

    monthly_qc_status = result[
        "monthly_qc_status"
    ]

    # --------------------------------------------------------
    # Statistical Analysis
    # --------------------------------------------------------

    zip_file.writestr(
        (
            f"{file_name}/"
            f"{file_name}_"
            f"Statistical_Analysis_"
            f"{YEAR_RANGE_TEXT}.csv"
        ),
        analysis_table.to_csv(
            index=False
        )
    )

    # --------------------------------------------------------
    # Monthly Total
    # --------------------------------------------------------

    zip_file.writestr(
        (
            f"{file_name}/"
            f"{file_name}_"
            f"Monthly_Total_"
            f"{YEAR_RANGE_TEXT}.csv"
        ),
        yearly_monthly_total.to_csv()
    )

    # --------------------------------------------------------
    # Missing
    # --------------------------------------------------------

    zip_file.writestr(
        (
            f"{file_name}/"
            f"{file_name}_"
            f"Missing_Days_"
            f"{YEAR_RANGE_TEXT}.csv"
        ),
        monthly_missing_count.to_csv()
    )

    # --------------------------------------------------------
    # Valid
    # --------------------------------------------------------

    zip_file.writestr(
        (
            f"{file_name}/"
            f"{file_name}_"
            f"Valid_Days_"
            f"{YEAR_RANGE_TEXT}.csv"
        ),
        monthly_valid_count.to_csv()
    )

    # --------------------------------------------------------
    # Consecutive Missing
    # --------------------------------------------------------

    zip_file.writestr(
        (
            f"{file_name}/"
            f"{file_name}_"
            f"Consecutive_Missing_"
            f"{YEAR_RANGE_TEXT}.csv"
        ),
        monthly_max_consecutive_missing.to_csv()
    )

    # --------------------------------------------------------
    # QC Status
    # --------------------------------------------------------

    zip_file.writestr(
        (
            f"{file_name}/"
            f"{file_name}_"
            f"QC_Status_"
            f"{YEAR_RANGE_TEXT}.csv"
        ),
        monthly_qc_status.to_csv()
    )

    # --------------------------------------------------------
    # Suspect
    # --------------------------------------------------------

    zip_file.writestr(
        (
            f"{file_name}/"
            f"{file_name}_"
            f"Suspect_Rainfall.csv"
        ),
        suspect_df.to_csv(
            index=False
        )
    )

    # --------------------------------------------------------
    # Extreme
    # --------------------------------------------------------

    zip_file.writestr(
        (
            f"{file_name}/"
            f"{file_name}_"
            f"Extreme_Rainfall.csv"
        ),
        extreme_df.to_csv(
            index=False
        )
    )


zip_buffer.seek(0)


st.download_button(
    label="📦 Download All Results (ZIP)",
    data=zip_buffer.getvalue(),
    file_name=(
        f"Rainfall_Analysis_"
        f"{YEAR_RANGE_TEXT}_"
        f"Target_{target_year}.zip"
    ),
    mime="application/zip"
)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🌧️ Rainfall Data Analysis | "
    "Quality Control, Climatological Mean, Anomaly "
    "and Statistical Analysis"
)
