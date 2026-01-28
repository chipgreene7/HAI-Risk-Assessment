import streamlit as st
import datetime as dt
from typing import Optional

# ------------------------------------------------------------
# CLABSI & CAUTI Risk Calculator (NHSN-aligned device-day logic)
# - Calendar days: insertion day = Day 1; device eligible on Day 3 (>2 days)
# - Device association: in place on DOE or removed the calendar day before DOE
# - IWP: 7 days (anchor ±3). For CAUTI, urine culture anchors IWP.
# - Inference FIX: If a device is removed ON the DOE, it WAS in place on DOE.
# ------------------------------------------------------------

st.set_page_config(
    page_title="CLABSI & CAUTI Risk Calculator",
    page_icon="💉",
    layout="centered"
)

st.title("💉 CLABSI & CAUTI Risk Calculator")
st.caption(
    "Device days use calendar-day counting (insertion day = Day 1; eligible on Day 3). "
    "IWP is 7 days anchored on the first positive diagnostic test (anchor ± 3). "
    "For UTI/CAUTI, the urine culture anchors the IWP."
)

tab_clabsi, tab_cauti = st.tabs(["CLABSI", "CAUTI"])

# --------------------------
# Shared helpers
# --------------------------
def inclusive_days(start: dt.date, end: dt.date) -> int:
    """Inclusive calendar-day count. Returns 0 if start > end."""
    if start > end:
        return 0
    return (end - start).days + 1

def iwp_range_text(anchor: Optional[dt.date]) -> str:
    """Return a pretty IWP string like '(IWP: Jan 02, 2026 – Jan 08, 2026)'."""
    if not anchor:
        return "(set DOE or culture date)"
    start = anchor - dt.timedelta(days=3)
    end = anchor + dt.timedelta(days=3)
    fmt = "%b %d, %Y"
    return f"(IWP: {start.strftime(fmt)} – {end.strftime(fmt)})"

IWP_RULE = (
    "IWP = 7 days. The infection window period includes the date of the first positive diagnostic test "
    "used to meet the criterion plus the 3 calendar days before and the 3 calendar days after (anchor ±3)."
)

DEVICE_ASSOC_RULE = (
    "Device association: device must be in place on the DOE, or removed the calendar day before the DOE."
)

CAUTI_IWP_RULE = (
    "For UTI/CAUTI, the urine culture sets the IWP. Symptoms used must occur within the 7-day IWP "
    "(urine culture date ±3)."
)

# =========================
# ========= CLABSI ========
# =========================
with tab_clabsi:
    st.header("CLABSI")
    st.write("Enter patient information to calculate CLABSI risk.")

    # --- Dates & device presence/removal ---
    cl_insertion_date = st.date_input(
        "Central line insertion date",
        value=dt.date.today(),
        help="Insertion day counts as Day 1 (calendar days). Eligible starting Day 3 (>2 days)."
    )

    cl_eval_date = st.date_input(
        "Date of evaluation (DOE)",
        value=dt.date.today(),
        help="DOE = the date the first element used to meet CLABSI criterion occurs (within IWP)."
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
            min_value=cl_insertion_date,
            max_value=cl_eval_date,
            help="If removed yesterday (DOE-1), still device-associated. If removed on DOE, it WAS in place on the DOE."
        )

    # Optional: first positive blood culture date (IWP anchor for BSI)
    st.markdown("**Microbiology timing (optional, improves IWP accuracy)**")
    use_bcx_date = st.checkbox(
        "Specify first positive blood culture collection date",
        value=False,
        help=IWP_RULE
    )
    if use_bcx_date:
        cl_bcx_date = st.date_input(
            "First positive blood culture collection date",
            value=cl_eval_date,
            help=IWP_RULE
        )
    else:
        cl_bcx_date = None

    # --- NHSN inference: if removed ON the DOE, device WAS in place on DOE ---
    if not cl_in_place and cl_removal_date and cl_removal_date == cl_eval_date:
        cl_in_place = True  # infer in place on DOE

    # --- Validate & compute device days ---
    problems = []
    cl_effective_end = cl_eval_date if cl_in_place else (cl_removal_date or cl_eval_date)

    if cl_insertion_date > cl_eval_date:
        problems.append("Insertion date cannot be after the evaluation/DOE.")
    if cl_insertion_date > cl_effective_end:
        problems.append("Insertion date cannot be after the removal/evaluation date.")

    if problems:
        for p in problems:
            st.error(p)
        st.stop()

    cl_days = inclusive_days(cl_insertion_date, cl_effective_end)
    cl_eligible = cl_days > 2  # Eligible starting Day 3

    # Device association: in place on DOE OR removed yesterday
    if cl_in_place:
        cl_device_associated = True
    else:
        cl_device_associated = bool(cl_removal_date) and (
            cl_removal_date == cl_eval_date - dt.timedelta(days=1)
        )

    # IWP anchor for display (blood culture preferred; fallback to DOE)
    cl_iwp_anchor = cl_bcx_date or cl_eval_date
    cl_iwp_label = iwp_range_text(cl_iwp_anchor)

    # --- Clinical inputs with IWP shown ---
    fever = (
        st.radio(
            f"Fever (≥ 38°C / 100.4°F)? {cl_iwp_label}",
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
            help="Positive blood culture is required (with eligibility and device association) to meet CLABSI criteria."
        ) == "Yes"
    )

    cl_symptom_any = fever or chills or hypotension

    # ====== Criteria determination (CLABSI) ======
    # For adult CLABSI per NHSN: positive blood culture + eligible device days + device-associated.
    # (Symptoms are not required to meet CLABSI, but indicate risk.)
    meets_clabsi_criteria = (
        positive_bcx and cl_eligible and cl_device_associated
    )

    # Criteria-first messaging
    if meets_clabsi_criteria:
        cl_msg = "Patient meets NHSN CLABSI Criteria (as of DOE)"
        cl_banner = "error"  # red banner to emphasize criteria met
    elif cl_symptom_any:
        cl_msg = "At risk – Monitor closely and consider blood cultures"
        cl_banner = "warning"
    else:
        cl_msg = "Low Risk"
        cl_banner = "info"

    # Output
    st.subheader("CLABSI Results")
    st.markdown(f"Insertion date: **{cl_insertion_date.isoformat()}**")
    st.markdown(f"Evaluation date (DOE): **{cl_eval_date.isoformat()}**")
    if cl_removal_date:
        st.markdown(f"Central line removal date: **{cl_removal_date.isoformat()}**")
    if cl_bcx_date:
        st.markdown(f"First positive blood culture date (IWP anchor): **{cl_bcx_date.isoformat()}**")

    st.markdown(f"IWP for symptom eligibility: **{iwp_range_text(cl_iwp_anchor)}** "
                "(7 day window: anchor date ± 3 days)")
    st.markdown(f"Central line days (calendar days): **{cl_days}**")
    st.markdown(f"NHSN device-day eligibility (>2 consecutive calendar days): **{cl_eligible}**")
    st.markdown(f"Device association (in place on DOE or removed yesterday): **{cl_device_associated}**")

    if cl_banner == "error":
        st.error(cl_msg)
    elif cl_banner == "warning":
        st.warning(cl_msg)
    else:
        st.info(cl_msg)

    # Diagnostics: why not criteria?
    if not meets_clabsi_criteria:
        reasons = []
        if not positive_bcx: reasons.append("No positive blood culture.")
        if not cl_eligible: reasons.append("Not eligible (>2 central-line days) by DOE (eligible starting Day 3).")
        if not cl_device_associated: reasons.append("Not device-associated (not in place on DOE or removed day before).")
        if reasons:
            st.caption("Reason(s) criteria not met: " + " ".join(reasons))

# =========================
# ========= CAUTI =========
# =========================
with tab_cauti:
    st.header("CAUTI")
    st.write("Enter urinary catheter information and symptoms for CAUTI risk.")

    # --- Dates & device presence/removal ---
    cauti_insertion_date = st.date_input(
        "Indwelling urinary catheter insertion date",
        value=dt.date.today(),
        help="Insertion day counts as Day 1. Eligible starting Day 3 (>2 days)."
    )

    cauti_eval_date = st.date_input(
        "Date of evaluation (DOE)",
        value=dt.date.today(),
        help="DOE = date the first element used to meet the UTI/CAUTI criterion occurs (within IWP)."
    )

    cauti_in_place = (
        st.radio(
            "Is the indwelling urinary catheter in place on the DOE?",
            ["Yes", "No"],
            help=DEVICE_ASSOC_RULE
        ) == "Yes"
    )

    # Always show removal date; disable if still in place
    cauti_removal_date = st.date_input(
        "Date of catheter removal",
        value=cauti_eval_date,
        min_value=cauti_insertion_date,
        max_value=cauti_eval_date,
        help="If removed yesterday (DOE-1), event can still be CAUTI-associated. "
             "If removed on DOE, it WAS in place on the DOE.",
        disabled=cauti_in_place
    )

    # Optional: urine culture collection date (IWP anchor for UTI/CAUTI)
    st.markdown("**Microbiology timing (recommended for IWP accuracy)**")
    use_ucx_date = st.checkbox(
        "Specify urine culture collection date (IWP anchor)",
        value=True,
        help=CAUTI_IWP_RULE
    )
    if use_ucx_date:
        cauti_ucx_date = st.date_input(
            "Urine culture collection date used for determination",
            value=cauti_eval_date,
            help=CAUTI_IWP_RULE
        )
    else:
        cauti_ucx_date = None

    # --- NHSN inference: if removed ON the DOE, device WAS in place on DOE ---
    if not cauti_in_place and cauti_removal_date and cauti_removal_date == cauti_eval_date:
        cauti_in_place = True  # infer in place on DOE

    # --- Validate & compute device days ---
    problems = []
    effective_end = cauti_eval_date if cauti_in_place else cauti_removal_date

    if cauti_insertion_date > cauti_eval_date:
        problems.append("Insertion date cannot be after the evaluation/DOE.")
    if cauti_insertion_date > effective_end:
        problems.append("Insertion date cannot be after the removal/evaluation date.")

    if problems:
        for p in problems:
            st.error(p)
        st.stop()

    cauti_days = inclusive_days(cauti_insertion_date, effective_end)
    cauti_eligible_days = cauti_days > 2  # Eligible starting Day 3

    # Device association: in place on DOE OR removed yesterday
    if cauti_in_place:
        cauti_device_associated = True
    else:
        cauti_device_associated = (cauti_removal_date == cauti_eval_date - dt.timedelta(days=1))

    # IWP anchor for CAUTI (urine culture preferred; fallback to DOE)
    cauti_iwp_anchor = cauti_ucx_date or cauti_eval_date
    cauti_iwp_label = iwp_range_text(cauti_iwp_anchor)

    st.divider()
    st.subheader("Signs & Symptoms")
    st.caption(
        "When an indwelling catheter is in place on symptom onset, eligible symptoms are fever (≥38 °C), "
        "suprapubic tenderness, and CVA pain/tenderness. Urgency, frequency, and dysuria apply only when "
        "the catheter has been removed."
    )

    # --- Symptoms (respect catheter status on DOE) ---
    fever_u = (
        st.radio(f"Fever (≥ 38 °C / 100.4 °F)? {cauti_iwp_label}", ["Yes", "No"], help=CAUTI_IWP_RULE) == "Yes"
    )
    suprapubic = (
        st.radio(f"Suprapubic tenderness? {cauti_iwp_label}", ["Yes", "No"], help=CAUTI_IWP_RULE) == "Yes"
    )
    cva = (
        st.radio(f"CVA pain/tenderness? {cauti_iwp_label}", ["Yes", "No"], help=CAUTI_IWP_RULE) == "Yes"
    )

    urgency_raw = (
        st.radio(f"Urinary urgency? {cauti_iwp_label}", ["Yes", "No"],
                 help="Only eligible after catheter removal; exclude when IUC is in place.") == "Yes"
    )
    frequency_raw = (
        st.radio(f"Urinary frequency? {cauti_iwp_label}", ["Yes", "No"],
                 help="Only eligible after catheter removal; exclude when IUC is in place.") == "Yes"
    )
    dysuria_raw = (
        st.radio(f"Dysuria? {cauti_iwp_label}", ["Yes", "No"],
                 help="Only eligible after catheter removal; exclude when IUC is in place.") == "Yes"
    )

    # Enforce NHSN symptom eligibility based on catheter status on DOE
    if cauti_in_place:
        urgency = frequency = dysuria = False
        st.info("Catheter is in place on DOE: urgency, frequency, and dysuria are excluded by NHSN.")
    else:
        urgency, frequency, dysuria = urgency_raw, frequency_raw, dysuria_raw

    positive_ucx = (
        st.radio(
            "Positive urine culture?",
            ["Yes", "No"],
            help="Positive urine culture is required (with device eligibility and association) to meet CAUTI criteria."
        ) == "Yes"
    )

    # Any eligible symptom (depending on catheter status)
    u_symptom_any = any([fever_u, suprapubic, cva, urgency, frequency, dysuria])

    # ====== Criteria determination (CAUTI) ======
    meets_cauti_criteria = (
        positive_ucx and
        cauti_eligible_days and
        cauti_device_associated and
        u_symptom_any
    )

    # Criteria-first messaging
    if meets_cauti_criteria:
        u_msg = "Patient meets NHSN CAUTI Criteria (as of DOE)"
        u_banner = "error"  # red
    elif u_symptom_any:
        u_msg = "At risk – Monitor closely and consider urine culture"
        u_banner = "warning"
    else:
        u_msg = "Low Risk"
        u_banner = "info"

    # Output
    st.subheader("CAUTI Results")
    st.markdown(f"Insertion date: **{cauti_insertion_date.isoformat()}**")
    st.markdown(f"Evaluation date (DOE): **{cauti_eval_date.isoformat()}**")
    # Show removal date if provided by user (even if inferred as 'in place' for DOE)
    if cauti_removal_date:
        st.markdown(f"Catheter removal date: **{cauti_removal_date.isoformat()}**")
    if cauti_ucx_date:
        st.markdown(f"Urine culture date (IWP anchor): **{cauti_ucx_date.isoformat()}**")

    st.markdown(f"IWP for symptom eligibility: **{iwp_range_text(cauti_iwp_anchor)}** "
                "(7 day window: anchor date ± 3 days; for UTI/CAUTI, the urine culture sets the IWP)")
    st.markdown(f"Catheter days (calendar days): **{cauti_days}**")
    st.markdown(f"NHSN catheter-day eligibility (> 2 consecutive calendar days): **{cauti_eligible_days}**")
    st.markdown(f"Device association (in place on DOE or removed yesterday): **{cauti_device_associated}**")

    if u_banner == "error":
        st.error(u_msg)
    elif u_banner == "warning":
        st.warning(u_msg)
    else:
        st.info(u_msg)

    # Diagnostics: why not criteria?
    if not meets_cauti_criteria:
        reasons = []
        if not positive_ucx: reasons.append("No positive urine culture.")
        if not cauti_eligible_days: reasons.append("Not eligible (>2 catheter-days) by DOE (eligible starting Day 3).")
        if not cauti_device_associated: reasons.append("Not device-associated (not in place on DOE or removed day before).")
        if not u_symptom_any: reasons.append("No eligible symptom within IWP.")
        if reasons:
            st.caption("Reason(s) criteria not met: " + " ".join(reasons))
