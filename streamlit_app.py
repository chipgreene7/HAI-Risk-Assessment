import streamlit as st
import datetime as dt
from typing import Optional, List

# ------------------------------------------------------------
# CLABSI & CAUTI Risk Calculator (NHSN-aligned device-day logic)
# - Calendar days: insertion day = Day 1; device eligible on Day 3 (>2 days)
# - Device association: in place on the assessment date or removed the calendar day before
# - IWP: 7 days (anchor ±3). For CAUTI, urine culture anchors IWP.
# - Inference FIX: If a device is removed ON the assessment date, it WAS in place on that date.
# ------------------------------------------------------------

st.set_page_config(
    page_title="CLABSI & CAUTI Risk Calculator",
    page_icon="💉",
    layout="centered"
)

# ===== Leadership wording (single place to change) =====
BLOOD_LEADERSHIP_LABEL = "TIMC Leadership"   # change to "Unit Leadership" if desired
URINE_LEADERSHIP_LABEL = "Unit Leadership"   # per your request

st.title("💉 CLABSI & CAUTI Risk Calculator")
st.caption(
    "Device days use calendar-day counting (insertion day = Day 1; eligible on Day 3). "
    "IWP is 7 days anchored on the first positive diagnostic test (anchor ± 3). "
    "For UTI/CAUTI, the urine culture anchors the IWP."
)

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
        return "(set assessment date or culture date)"
    start = anchor - dt.timedelta(days=3)
    end = anchor + dt.timedelta(days=3)
    fmt = "%b %d, %Y"
    return f"(IWP: {start.strftime(fmt)} – {end.strftime(fmt)})"

def c_to_f(c: float) -> float:
    return (c * 9/5) + 32

def f_to_c(f: float) -> float:
    return (f - 32) * 5/9

def show_errors(errors: List[str]) -> None:
    for e in errors:
        st.error(e)

def invalid_dates_guard(problems: List[str]) -> bool:
    """
    Non-blocking guard. Shows errors and returns True if invalid.
    IMPORTANT: We do NOT call st.stop() anywhere so other tabs still render.
    """
    if problems:
        show_errors(problems)
        return True
    return False

IWP_RULE = (
    "IWP = 7 days. The infection window period includes the date of the first positive diagnostic test "
    "used to meet the criterion plus the 3 calendar days before and the 3 calendar days after (anchor ±3)."
)

DEVICE_ASSOC_RULE = (
    "Device association: device must be in place on the assessment date, or removed the calendar day before the assessment date."
)

CAUTI_IWP_RULE = (
    "For UTI/CAUTI, the urine culture sets the IWP. Symptoms used must occur within the 7-day IWP "
    "(urine culture date ±3)."
)

TEMP_RULE = (
    "Enter the highest documented temperature during the IWP in °F. Fever threshold is strictly > 38 °C (> 100.4 °F). "
    "The app converts °F → °C and applies the strict > 38 °C rule."
)

# --------------------------
# New: Escalation tab renderers
# --------------------------
def render_blood_culture_escalation(leadership_label: str = BLOOD_LEADERSHIP_LABEL) -> None:
    st.header("Blood Culture Escalation")
    st.write("Use this quick pathway to determine whether to obtain a blood culture or escalate for leadership review.")

    # ✅ Unique keys to ensure no collisions if labels are reused elsewhere
    q1_has_cvc = st.radio(
        "Does the patient currently have a CVC?",
        ["Yes", "No"],
        horizontal=True,
        key="blood_q1_has_cvc",
    )

    if q1_has_cvc == "Yes":
        q2_recent_admit = st.radio(
            "Was the patient admitted to TIMC less than 2 calendar days ago?",
            ["Yes", "No"],
            horizontal=True,
            help="Use calendar days; admission day counts as Day 1.",
            key="blood_q2_recent_admit",
        )
        if q2_recent_admit == "Yes":
            st.success(f"Acquire blood culture — escalation to {leadership_label} not needed.")
        else:
            st.warning(f"Contact {leadership_label} to assist in clinical necessity.")
    else:
        q3_recent_cvc = st.radio(
            "Did the patient have a CVC within the last 3 calendar days?",
            ["Yes", "No"],
            horizontal=True,
            key="blood_q3_recent_cvc",
        )
        if q3_recent_cvc == "Yes":
            st.warning(f"Contact {leadership_label} to assist in clinical necessity.")
        else:
            st.success(f"Acquire blood culture — escalation to {leadership_label} not needed.")

    with st.expander("Things to Remember"):
        st.markdown(
            "- Does the patient have a wound? If yes, consider a wound culture.\n"
            "- Has the patient had any fevers greater than 100.4 °F?\n"
            "- Has the patient been hypotensive or tachycardic?\n"
            "- Any other known sources of infection?"
        )

def render_urine_culture_escalation(leadership_label: str = URINE_LEADERSHIP_LABEL) -> None:
    st.header("Urine Culture Escalation")
    st.write("Use this pathway to guide appropriate urine culture ordering and when to involve unit leadership.")

    q1_has_foley = st.radio(
        "Does the patient currently have a Foley catheter?",
        ["Yes", "No"],
        horizontal=True,
        key="urine_q1_has_foley",
    )

    if q1_has_foley == "Yes":
        q2_recent_admit = st.radio(
            "Was the patient admitted or transferred less than 2 calendar days ago?",
            ["Yes", "No"],
            horizontal=True,
            help="Use calendar days; admission/transfer day counts as Day 1.",
            key="urine_q2_recent_admit",
        )
        if q2_recent_admit == "Yes":
            st.success(f"Acquire urine culture — escalation to {leadership_label} not needed.")
        else:
            st.warning(f"Contact {leadership_label} to assist with determining clinical necessity.")
    else:
        q3_recent_foley = st.radio(
            "Did the patient have a Foley catheter within the last 3 calendar days?",
            ["Yes", "No"],
            horizontal=True,
            key="urine_q3_recent_foley",
        )
        if q3_recent_foley == "Yes":
            st.warning(f"Contact {leadership_label} to assist with determining clinical necessity.")
        else:
            st.success(f"Acquire urine culture — escalation to {leadership_label} not needed.")

    with st.expander("Things to Remember"):
        st.markdown(
            "- Are urinary symptoms present (dysuria, suprapubic pain, flank pain)?\n"
            "- Any systemic signs (fever, hypotension, tachycardia)?\n"
            "- Could this represent asymptomatic bacteriuria?\n"
            "- Is there another identifiable source of infection?"
        )

# --------------------------
# Calculator tabs as functions (no st.stop) + opt-in entry
# --------------------------
def render_clabsi_tab():
    st.header("CLABSI")
    st.write("Enter patient information to calculate CLABSI risk and determine if CLABSI criteria are met.")

    # ✅ Unique key to avoid duplicate element id for a toggle with the same label in another tab
    enable = st.toggle(
        "Enter dates now",
        value=False,
        help="Turn on to input dates and run the calculator.",
        key="clabsi_enable"
    )
    if not enable:
        st.info("Turn on **Enter dates now** to input dates. Other tabs (including Escalation) remain available.")
        return

    # If your Streamlit supports value=None for date_input, you can set value=None and guard for None.
    cl_insertion_date = st.date_input(
        "Central line insertion date",
        value=dt.date.today(),
        help="Insertion day counts as Day 1 (calendar days). Eligible starting Day 3 (>2 days).",
        key="clabsi_insertion_date"
    )

    cl_eval_date = st.date_input(
        "Assessment date",
        value=dt.date.today(),
        help="Assessment date = the date the first element used to meet CLABSI criterion occurs (within IWP).",
        key="clabsi_assessment_date"
    )

    cl_in_place = (
        st.radio(
            "Is the central line in place on the assessment date?",
            ["Yes", "No"],
            help=DEVICE_ASSOC_RULE,
            key="clabsi_in_place"
        ) == "Yes"
    )

    cl_removal_date = None
    if not cl_in_place:
        cl_removal_date = st.date_input(
            "Central line removal date",
            min_value=cl_insertion_date,
            max_value=cl_eval_date,
            help="If removed yesterday (assessment date − 1), still device-associated. "
                 "If removed on the assessment date, it WAS in place on the assessment date.",
            key="clabsi_removal_date"
        )

    st.markdown("**Microbiology timing (optional, improves IWP accuracy)**")
    use_bcx_date = st.checkbox(
        "Specify first positive blood culture collection date",
        value=False,
        help=IWP_RULE,
        key="clabsi_use_bcx_date"
    )
    if use_bcx_date:
        cl_bcx_date = st.date_input(
            "First positive blood culture collection date",
            value=cl_eval_date,
            help=IWP_RULE,
            key="clabsi_bcx_date"
        )
    else:
        cl_bcx_date = None

    if not cl_in_place and cl_removal_date and cl_removal_date == cl_eval_date:
        cl_in_place = True  # infer in place on assessment date

    problems = []
    cl_effective_end = cl_eval_date if cl_in_place else (cl_removal_date or cl_eval_date)

    if cl_insertion_date > cl_eval_date:
        problems.append("Insertion date cannot be after the assessment date.")
    if cl_insertion_date > cl_effective_end:
        problems.append("Insertion date cannot be after the removal/assessment date.")

    if invalid_dates_guard(problems):
        return  # do NOT stop app; just end this tab's logic

    cl_days = inclusive_days(cl_insertion_date, cl_effective_end)
    cl_eligible = cl_days > 2  # Eligible starting Day 3

    if cl_in_place:
        cl_device_associated = True
    else:
        cl_device_associated = bool(cl_removal_date) and (
            cl_removal_date == cl_eval_date - dt.timedelta(days=1)
        )

    cl_iwp_anchor = cl_bcx_date or cl_eval_date
    cl_iwp_label = iwp_range_text(cl_iwp_anchor)

    cl_temp_f = st.number_input(
        f"Highest documented temperature during IWP? (°F)  (> 100.4 °F / > 38 °C) {cl_iwp_label}",
        min_value=80.0, max_value=113.0, value=98.6, step=0.1, format="%.1f",
        help=TEMP_RULE,
        key="clabsi_temp_f"
    )
    cl_temp_c = f_to_c(cl_temp_f)
    st.caption(f"Entered temperature ≈ **{cl_temp_c:.1f} °C**")
    cl_fever = (cl_temp_c > 38.0)

    hypotension = (
        st.radio(
            f"Hypotension present? {cl_iwp_label}",
            ["Yes", "No"],
            help=IWP_RULE,
            key="clabsi_hypotension"
        ) == "Yes"
    )
    chills = (
        st.radio(
            f"Chills present? {cl_iwp_label}",
            ["Yes", "No"],
            help=IWP_RULE,
            key="clabsi_chills"
        ) == "Yes"
    )

    positive_bcx = (
        st.radio(
            "Positive blood culture?",
            ["Yes", "No"],
            help="Positive blood culture is required (with eligibility and device association) to meet CLABSI criteria.",
            key="clabsi_positive_bcx"
        ) == "Yes"
    )

    cl_symptom_any = cl_fever or hypotension or chills

    meets_clabsi_criteria = (positive_bcx and cl_eligible and cl_device_associated)

    st.subheader("CLABSI Results")
    st.markdown(f"Insertion date: **{cl_insertion_date.isoformat()}**")
    st.markdown(f"Assessment date: **{cl_eval_date.isoformat()}**")
    if cl_removal_date:
        st.markdown(f"Central line removal date: **{cl_removal_date.isoformat()}**")
    if cl_bcx_date:
        st.markdown(f"First positive blood culture date (IWP anchor): **{cl_bcx_date.isoformat()}**")

    st.markdown(f"IWP for symptom eligibility: **{iwp_range_text(cl_iwp_anchor)}** (7 day window: anchor date ± 3 days)")
    st.markdown(f"Central line days (calendar days): **{cl_days}**")
    st.markdown(f"NHSN device-day eligibility (>2 consecutive calendar days): **{cl_eligible}**")
    st.markdown(f"Device association (in place on assessment date or removed yesterday): **{cl_device_associated}**")

    if meets_clabsi_criteria:
        st.error("Patient **meets** NHSN CLABSI Criteria (as of assessment date).")
    elif cl_symptom_any:
        st.warning("**At risk** — symptoms within IWP; continue evaluation and monitoring.")
    else:
        st.success("Patient **does not meet** NHSN CLABSI Criteria (as of assessment date).")

    if not meets_clabsi_criteria:
        reasons = []
        if not positive_bcx: reasons.append("No positive blood culture.")
        if not cl_eligible: reasons.append("Not eligible (>2 central-line days) by assessment date (eligible starting Day 3).")
        if not cl_device_associated: reasons.append("Not device-associated (not in place on assessment date or removed day before).")
        if reasons:
            st.caption("Reason(s) criteria not met: " + " ".join(reasons))

def render_cauti_tab():
    st.header("CAUTI")
    st.write("Enter urinary catheter information and symptoms for CAUTI risk and determination.")

    # ✅ Unique key; prevents collision with the CLABSI toggle
    enable = st.toggle(
        "Enter dates now",
        value=False,
        help="Turn on to input dates and run the calculator.",
        key="cauti_enable"
    )
    if not enable:
        st.info("Turn on **Enter dates now** to input dates. Other tabs (including Escalation) remain available.")
        return

    cauti_insertion_date = st.date_input(
        "Indwelling urinary catheter insertion date",
        value=dt.date.today(),
        help="Insertion day counts as Day 1. Eligible starting Day 3 (>2 days).",
        key="cauti_insertion_date"
    )

    cauti_eval_date = st.date_input(
        "Assessment date",
        value=dt.date.today(),
        help="Assessment date = the date the first element used to meet the UTI/CAUTI criterion occurs (within IWP).",
        key="cauti_assessment_date"
    )

    cauti_in_place = (
        st.radio(
            "Is the indwelling urinary catheter in place on the assessment date?",
            ["Yes", "No"],
            help=DEVICE_ASSOC_RULE,
            key="cauti_in_place"
        ) == "Yes"
    )

    cauti_removal_date = st.date_input(
        "Date of catheter removal",
        value=cauti_eval_date,
        min_value=cauti_insertion_date,
        max_value=cauti_eval_date,
        help="If removed yesterday (assessment date − 1), event can still be CAUTI-associated. "
             "If removed on the assessment date, it WAS in place on the assessment date.",
        disabled=cauti_in_place,
        key="cauti_removal_date"
    )

    st.markdown("**Microbiology timing (recommended for IWP accuracy)**")
    use_ucx_date = st.checkbox(
        "Specify urine culture collection date (IWP anchor)",
        value=True,
        help=CAUTI_IWP_RULE,
        key="cauti_use_ucx_date"
    )
    if use_ucx_date:
        cauti_ucx_date = st.date_input(
            "Urine culture collection date used for determination",
            value=cauti_eval_date,
            help=CAUTI_IWP_RULE,
            key="cauti_ucx_date"
        )
    else:
        cauti_ucx_date = None

    if not cauti_in_place and cauti_removal_date and cauti_removal_date == cauti_eval_date:
        cauti_in_place = True  # infer in place on assessment date

    problems = []
    effective_end = cauti_eval_date if cauti_in_place else cauti_removal_date

    if cauti_insertion_date > cauti_eval_date:
        problems.append("Insertion date cannot be after the assessment date.")
    if cauti_insertion_date > effective_end:
        problems.append("Insertion date cannot be after the removal/assessment date.")

    if invalid_dates_guard(problems):
        return  # do NOT stop app; just end this tab's logic

    cauti_days = inclusive_days(cauti_insertion_date, effective_end)
    cauti_eligible_days = cauti_days > 2  # Eligible starting Day 3

    if cauti_in_place:
        cauti_device_associated = True
    else:
        cauti_device_associated = (cauti_removal_date == cauti_eval_date - dt.timedelta(days=1))

    cauti_iwp_anchor = cauti_ucx_date or cauti_eval_date
    cauti_iwp_label = iwp_range_text(cauti_iwp_anchor)

    st.divider()
    st.subheader("Signs & Symptoms")
    st.caption(
        "When an indwelling catheter is in place on symptom onset, eligible symptoms are fever (>38 °C), "
        "suprapubic tenderness, and CVA pain/tenderness. Urgency, frequency, and dysuria apply only when "
        "the catheter has been removed."
    )

    u_temp_f = st.number_input(
        f"Highest documented temperature during IWP? (°F)  (> 100.4 °F / > 38 °C) {cauti_iwp_label}",
        min_value=80.0, max_value=113.0, value=98.6, step=0.1, format="%.1f",
        help=TEMP_RULE,
        key="cauti_temp_f"
    )
    u_temp_c = f_to_c(u_temp_f)
    st.caption(f"Entered temperature ≈ **{u_temp_c:.1f} °C**")
    fever_u = (u_temp_c > 38.0)

    suprapubic = (
        st.radio(f"Suprapubic tenderness? {cauti_iwp_label}", ["Yes", "No"], help=CAUTI_IWP_RULE, key="cauti_suprapubic") == "Yes"
    )
    cva = (
        st.radio(f"CVA pain/tenderness? {cauti_iwp_label}", ["Yes", "No"], help=CAUTI_IWP_RULE, key="cauti_cva") == "Yes"
    )

    urgency_raw = (
        st.radio(f"Urinary urgency? {cauti_iwp_label}", ["Yes", "No"],
                 help="Only eligible after catheter removal; exclude when IUC is in place.", key="cauti_urgency") == "Yes"
    )
    frequency_raw = (
        st.radio(f"Urinary frequency? {cauti_iwp_label}", ["Yes", "No"],
                 help="Only eligible after catheter removal; exclude when IUC is in place.", key="cauti_frequency") == "Yes"
    )
    dysuria_raw = (
        st.radio(f"Dysuria? {cauti_iwp_label}", ["Yes", "No"],
                 help="Only eligible after catheter removal; exclude when IUC is in place.", key="cauti_dysuria") == "Yes"
    )

    if cauti_in_place:
        urgency = frequency = dysuria = False
        st.info("Catheter is in place on the assessment date: urgency, frequency, and dysuria are excluded by NHSN.")
    else:
        urgency, frequency, dysuria = urgency_raw, frequency_raw, dysuria_raw

    positive_ucx = (
        st.radio(
            "Positive urine culture?",
            ["Yes", "No"],
            help="Positive urine culture is required (with device eligibility and association) to meet CAUTI criteria.",
            key="cauti_positive_ucx"
        ) == "Yes"
    )

    u_symptom_any = any([fever_u, suprapubic, cva, urgency, frequency, dysuria])

    meets_cauti_criteria = (
        positive_ucx and
        cauti_eligible_days and
        cauti_device_associated and
        u_symptom_any
    )

    st.subheader("CAUTI Results")
    st.markdown(f"Insertion date: **{cauti_insertion_date.isoformat()}**")
    st.markdown(f"Assessment date: **{cauti_eval_date.isoformat()}**")
    if cauti_removal_date:
        st.markdown(f"Catheter removal date: **{cauti_removal_date.isoformat()}**")
    if cauti_ucx_date:
        st.markdown(f"Urine culture date (IWP anchor): **{cauti_ucx_date.isoformat()}**")

    st.markdown(f"IWP for symptom eligibility: **{iwp_range_text(cauti_iwp_anchor)}** "
                "(7 day window: anchor date ± 3 days; for UTI/CAUTI, the urine culture sets the IWP)")
    st.markdown(f"Catheter days (calendar days): **{cauti_days}**")
    st.markdown(f"NHSN catheter-day eligibility (> 2 consecutive calendar days): **{cauti_eligible_days}**")
    st.markdown(f"Device association (in place on assessment date or removed yesterday): **{cauti_device_associated}**")

    if meets_cauti_criteria:
        st.error("Patient **meets** NHSN CAUTI Criteria (as of assessment date).")
    elif u_symptom_any:
        st.warning("**At risk** — symptoms within IWP; continue evaluation and monitoring.")
    else:
        st.success("Patient **does not meet** NHSN CAUTI Criteria (as of assessment date).")

    if not meets_cauti_criteria:
        reasons = []
        if not positive_ucx: reasons.append("No positive urine culture.")
        if not cauti_eligible_days: reasons.append("Not eligible (>2 catheter-days) by assessment date (eligible starting Day 3).")
        if not cauti_device_associated: reasons.append("Not device-associated (not in place on assessment date or removed day before).")
        if not u_symptom_any: reasons.append("No eligible symptom within IWP.")
        if reasons:
            st.caption("Reason(s) criteria not met: " + " ".join(reasons))


# ============================================================
# ======================= MAIN TABS ==========================
# ============================================================
tab_clabsi, tab_cauti, tab_blood, tab_urine = st.tabs(
    ["CLABSI", "CAUTI", "Blood Culture Escalation", "Urine Culture Escalation"]
)

with tab_clabsi:
    render_clabsi_tab()

with tab_cauti:
    render_cauti_tab()

with tab_blood:
    render_blood_culture_escalation(BLOOD_LEADERSHIP_LABEL)

with tab_urine:
    render_urine_culture_escalation(URINE_LEADERSHIP_LABEL)
