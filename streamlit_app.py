import streamlit as st
import datetime as dt

# ------------------------------------------------------------
# CLABSI & CAUTI Risk Calculator (NHSN-aligned device-day logic)
# ------------------------------------------------------------

st.set_page_config(
    page_title="CLABSI & CAUTI Risk Calculator",
    page_icon="💉",
    layout="centered"
)

st.title("💉 CLABSI & CAUTI Risk Calculator")
st.caption(
    "Device days use calendar-day counting (day of insertion = Day 1). "
    "IWP (Infection Window Period) is a 7-day span anchored on the first positive diagnostic test "
    "(anchor date ± 3 days)."
)

tab_clabsi, tab_cauti = st.tabs(["CLABSI", "CAUTI"])

# ------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------

def inclusive_days(start: dt.date, end: dt.date) -> int:
    if start > end:
        return 0
    return (end - start).days + 1


def iwp_range_text(anchor: dt.date | None) -> str:
    """Return formatted IWP label string."""
    if not anchor:
        return "(set DOE or culture date)"
    start = anchor - dt.timedelta(days=3)
    end = anchor + dt.timedelta(days=3)
    return f"(IWP: {start:%b %d, %Y} – {end:%b %d, %Y})"


# Tooltip reference notes
IWP_RULE = (
    "IWP = 7 days. The infection window period includes "
    "the date of the first positive diagnostic test used to meet the criterion "
    "plus the 3 days before and 3 days after (anchor ±3)."
)

DEVICE_ASSOC_RULE = (
    "Device must be in place on the DOE or removed the day before to be device-associated."
)

CAUTI_IWP_RULE = (
    "For UTI/CAUTI, the urine culture sets the IWP. Symptoms must fall within the urine-culture IWP."
)


# ============================================================
# ============================ CLABSI ========================
# ============================================================

with tab_clabsi:

    st.header("CLABSI")
    st.write("Enter patient information to calculate CLABSI risk.")

    # --- Input dates ---
    cl_insertion_date = st.date_input(
        "Central line insertion date",
        value=dt.date.today(),
        help="Day of insertion counts as Day 1 (calendar days). Device eligibility begins on Day 3."
    )

    cl_eval_date = st.date_input(
        "Date of evaluation (DOE)",
        value=dt.date.today(),
        help="DOE = date first element of the criterion occurs (within IWP)."
    )

    cl_in_place = (
        st.radio(
            "Is the central line in place on the DOE?",
            ["Yes", "No"],
            help=DEVICE_ASSOC_RULE
        ) == "Yes"
    )

    cl_removal_date = None
    if not cl_in_place:
        cl_removal_date = st.date_input(
            "Central line removal date",
            max_value=cl_eval_date,
            help="If removed yesterday: still device-associated."
        )

    # Optional blood culture date
    use_bcx_date = st.checkbox(
        "Specify first positive blood culture date",
        value=False,
        help=IWP_RULE
    )

    if use_bcx_date:
        cl_bcx_date = st.date_input(
            "First positive blood culture collection date",
            value=cl_eval_date
        )
    else:
        cl_bcx_date = None

    # --- Validation ---
    problems = []
    cl_effective_end = cl_eval_date if cl_in_place else (cl_removal_date or cl_eval_date)

    if cl_insertion_date > cl_eval_date:
        problems.append("Insertion date cannot be after DOE.")
    if cl_insertion_date > cl_effective_end:
        problems.append("Insertion date cannot be after removal/evaluation date.")

    if problems:
        for p in problems:
            st.error(p)
        st.stop()

    # Device-day logic
    cl_days = inclusive_days(cl_insertion_date, cl_effective_end)
    cl_eligible = cl_days > 2

    if cl_in_place:
        cl_device_associated = True
    else:
        cl_device_associated = (
            cl_removal_date == cl_eval_date - dt.timedelta(days=1)
        )

    cl_iwp_anchor = cl_bcx_date or cl_eval_date
    cl_iwp_label = iwp_range_text(cl_iwp_anchor)

    # --- Symptoms ---
    fever = (
        st.radio(
            f"Fever (≥ 38°C)? {cl_iwp_label}",
            ["Yes", "No"],
            help=IWP_RULE
        ) == "Yes"
    )

    hypotension = (
        st.radio(
            f"Hypotension present? {cl_iwp_label}",
            ["Yes", "No"],
            help=IWP_RULE
        ) == "Yes"
    )

    chills = (
        st.radio(
            f"Chills present? {cl_iwp_label}",
            ["Yes", "No"],
            help=IWP_RULE
        ) == "Yes"
    )

    positive_bcx = (
        st.radio(
            "Positive blood culture?",
            ["Yes", "No"],
            help="Required for CLABSI criteria."
        ) == "Yes"
    )

    cl_at_risk = fever or chills or hypotension

    # Risk scoring
    cl_score = 0
    if cl_eligible: cl_score += 1
    if fever: cl_score += 1
    if hypotension: cl_score += 1
    if chills: cl_score += 1
    if positive_bcx: cl_score += 2

    # Final message
    if positive_bcx and cl_eligible and cl_device_associated:
        cl_msg = "Patient meets CLABSI Criteria – Evaluate secondary options"
    elif cl_at_risk or cl_score >= 2:
        cl_msg = "At risk – Monitor closely and consider blood cultures"
    else:
        cl_msg = "Low Risk"

    # --- Output ---
    st.subheader("CLABSI Results")
    st.markdown(f"Insertion date: **{cl_insertion_date}**")
    st.markdown(f"Evaluation date (DOE): **{cl_eval_date}**")

    if cl_removal_date:
        st.markdown(f"Line removal date: **{cl_removal_date}**")

    if cl_bcx_date:
        st.markdown(f"Blood culture date: **{cl_bcx_date}**")

    st.markdown(f"IWP: **{iwp_range_text(cl_iwp_anchor)}**")
    st.markdown(f"Central line days: **{cl_days}**")
    st.markdown(f"Device-day eligible (>2 days): **{cl_eligible}**")
    st.markdown(f"Device-associated: **{cl_device_associated}**")
    st.markdown(f"Result: **{cl_msg}**")


# ============================================================
# ============================ CAUTI =========================
# ============================================================

with tab_cauti:

    st.header("CAUTI")
    st.write("Enter urinary catheter information and symptoms for CAUTI risk.")

    cauti_insertion_date = st.date_input(
        "Catheter insertion date",
        value=dt.date.today(),
        help="Day 1 = insertion day."
    )

    cauti_eval_date = st.date_input(
        "Date of evaluation (DOE)",
        value=dt.date.today(),
        help="DOE = date first element of criterion occurs."
    )

    cauti_in_place = (
        st.radio(
            "Catheter in place on DOE?",
            ["Yes", "No"],
            help=DEVICE_ASSOC_RULE
        ) == "Yes"
    )

    # Removal date always shown but disabled appropriately
    cauti_removal_date = st.date_input(
        "Catheter removal date",
        value=cauti_eval_date,
        min_value=cauti_insertion_date,
        max_value=cauti_eval_date,
        disabled=cauti_in_place
    )

    use_ucx_date = st.checkbox(
        "Specify urine culture date",
        value=False,
        help=CAUTI_IWP_RULE
    )

    if use_ucx_date:
        cauti_ucx_date = st.date_input("Urine culture collection date")
    else:
        cauti_ucx_date = None

    # Validation
    problems = []
    effective_end = cauti_eval_date if cauti_in_place else cauti_removal_date

    if cauti_insertion_date > cauti_eval_date:
        problems.append("Insertion date cannot be after DOE.")
    if cauti_insertion_date > effective_end:
        problems.append("Insertion date cannot be after removal/evaluation.")

    if problems:
        for p in problems:
            st.error(p)
        st.stop()

    cauti_days = inclusive_days(cauti_insertion_date, effective_end)
    cauti_eligible_days = cauti_days > 2

    if cauti_in_place:
        cauti_device_associated = True
    else:
        cauti_device_associated = (
            cauti_removal_date == cauti_eval_date - dt.timedelta(days=1)
        )

    cauti_iwp_anchor = cauti_ucx_date or cauti_eval_date
    cauti_iwp_label = iwp_range_text(cauti_iwp_anchor)

    st.divider()
    st.subheader("Symptoms")

    # Symptoms
    fever_u = (
        st.radio(
            f"Fever ≥ 38°C? {cauti_iwp_label}",
            ["Yes", "No"]
        ) == "Yes"
    )

    suprapubic = (
        st.radio(
            f"Suprapubic tenderness? {cauti_iwp_label}",
            ["Yes", "No"]
        ) == "Yes"
    )

    cva = (
        st.radio(
            f"CVA pain or tenderness? {cauti_iwp_label}",
            ["Yes", "No"]
        ) == "Yes"
    )

    urgency_raw = (
        st.radio(
            f"Urinary urgency? {cauti_iwp_label}",
            ["Yes", "No"]
        ) == "Yes"
    )

    frequency_raw = (
        st.radio(
            f"Urinary frequency? {cauti_iwp_label}",
            ["Yes", "No"]
        ) == "Yes"
    )

    dysuria_raw = (
        st.radio(
            f"Dysuria? {cauti_iwp_label}",
            ["Yes", "No"]
        ) == "Yes"
    )

    if cauti_in_place:
        urgency = frequency = dysuria = False
        st.info("Catheter is in place: urgency/frequency/dysuria excluded.")
    else:
        urgency, frequency, dysuria = urgency_raw, frequency_raw, dysuria_raw

    positive_ucx = (
        st.radio(
            "Positive urine culture?",
            ["Yes", "No"]
        ) == "Yes"
    )

    u_symptom_any = any([fever_u, suprapubic, cva, urgency, frequency, dysuria])

    u_score = 0
    if cauti_eligible_days: u_score += 1
    if fever_u: u_score += 1
    if suprapubic: u_score += 1
    if cva: u_score += 1
    if urgency: u_score += 1
    if frequency: u_score += 1
    if dysuria: u_score += 1
    if positive_ucx: u_score += 2

    if positive_ucx and cauti_eligible_days and cauti_device_associated:
        u_msg = "Patient meets CAUTI Criteria – Evaluate secondary options"
    elif u_symptom_any or u_score >= 2:
        u_msg = "At risk – Monitor closely and consider urine culture"
    else:
        u_msg = "Low Risk"

    st.subheader("CAUTI Results")
    st.markdown(f"Insertion date: **{cauti_insertion_date}**")
    st.markdown(f"Evaluation date: **{cauti_eval_date}**")
    if not cauti_in_place:
        st.markdown(f"Removal date: **{cauti_removal_date}**")
    if cauti_ucx_date:
        st.markdown(f"Urine culture date: **{cauti_ucx_date}**")

    st.markdown(f"IWP: **{iwp_range_text(cauti_iwp_anchor)}**")
    st.markdown(f"Catheter days: **{cauti_days}**")
    st.markdown(f"Eligible (>2 days): **{cauti_eligible_days}**")
    st.markdown(f"Device-associated: **{cauti_device_associated}**")
    st.markdown(f"Result: **{u_msg}**")
