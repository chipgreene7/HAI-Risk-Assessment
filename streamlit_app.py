import streamlit as st
import datetime as dt
from typing import Optional

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

    q1_has_cvc = st.radio("Does the patient currently have a CVC?", ["Yes", "No"], horizontal=True)

    if q1_has_cvc == "Yes":
        q2_recent_admit = st.radio(
            "Was the patient admitted to TIMC less than 2 calendar days ago?",
            ["Yes", "No"], horizontal=True,
            help="Use calendar days; admission day counts as Day 1."
        )
        if q2_recent_admit == "Yes":
            st.success(f"Acquire blood culture — escalation to {leadership_label} not needed.")
        else:
            st.warning(f"Contact {leadership_label} to assist in clinical necessity.")
    else:
        q3_recent_cvc = st.radio(
            "Did the patient have a CVC within the last 3 calendar days?",
            ["Yes", "No"], horizontal=True
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

    q1_has_foley = st.radio("Does the patient currently have a Foley catheter?", ["Yes", "No"], horizontal=True)

    if q1_has_foley == "Yes":
        q2_recent_admit = st.radio(
            "Was the patient admitted or transferred less than 2 calendar days ago?",
            ["Yes", "No"], horizontal=True,
            help="Use calendar days; admission/transfer day counts as Day 1."
        )
        if q2_recent_admit == "Yes":
            st.success(f"Acquire urine culture — escalation to {leadership_label} not needed.")
        else:
            st.warning(f"Contact {leadership_label} to assist with determining clinical necessity.")
    else:
        q3_recent_foley = st.radio(
            "Did the patient have a Foley catheter within the last 3 calendar days?",
            ["Yes", "No"], horizontal=True
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

# ============================================================
# ======================= MAIN TABS ==========================
# ============================================================
tab_clabsi, tab_cauti, tab_blood, tab_urine = st.tabs(
    ["CLABSI", "CAUTI", "Blood Culture Escalation", "Urine Culture Escalation"]
)

# =========================
# ========= CLABSI ========
# =========================
with tab_clabsi:
    st.header("CLABSI")
    st.write("Enter patient information to calculate CLABSI risk and determine if CLABSI criteria are met.")

    # --- Dates & device presence/removal ---
    cl_insertion_date = st.date_input(
        "Central line insertion date",
        value=dt.date.today(),
        help="Insertion day counts as Day 1 (calendar days). Eligible starting Day 3 (>2 days)."
    )

    cl_eval_date = st.date_input(
        "Assessment date",
        value=dt.date.today(),
        help="Assessment date = the date the first element used to meet CLABSI criterion occurs (within IWP)."
    )

    cl_in_place = (
        st.radio(
            "Is the central line in place on the assessment date?",
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
            help="If removed yesterday (assessment date − 1), still device-associated. "
                 "If removed on the assessment date, it WAS in place on the assessment date."
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

    # --- NHSN inference: if removed ON the assessment date, device WAS in place on that date ---
    if not cl_in_place and cl_removal_date and cl_removal_date == cl_eval_date:
        cl_in_place = True  # infer in place on assessment date

    # --- Validate & compute device days ---
    problems = []
    cl_effective_end = cl_eval_date if cl_in_place else (cl_removal_date or cl_eval_date)

    if cl_insertion_date > cl_eval_date:
        problems.append("Insertion date cannot be after the assessment date.")
    if cl_insertion_date > cl_effective_end:
        problems.append("Insertion date cannot be after the removal/assessment date.")

    if problems:
        for p in problems:
            st.error(p)
        st.stop()

    cl_days = inclusive_days(cl_insertion_date, cl_effective_end)
    cl_eligible = cl_days > 2  # Eligible starting Day 3

    # Device association: in place on assessment date OR removed yesterday
    if cl_in_place:
        cl_device_associated = True
    else:
        cl_device_associated = bool(cl_removal_date) and (
            cl_removal_date == cl_eval_date - dt.timedelta(days=1)
        )

    # IWP anchor for display (blood culture preferred; fallback to assessment date)
    cl_iwp_anchor = cl_bcx_date or cl_eval_date
    cl_iwp_label = iwp_range_text(cl_iwp_anchor)

    # --- Clinical inputs with IWP shown ---
    # Temperature entry in °F; logic uses > 38 °C after converting
    cl_temp_f = st.number_input(
        f"Highest documented temperature during IWP? (°F)  (> 100.4 °F / > 38 °C) {cl_iwp_label}",
        min_value=80.0, max_value=113.0, value=98.6, step=0.1, format="%.1f",
        help=TEMP_RULE
    )
    cl_temp_c = f_to_c(cl_temp_f)
    st.caption(f"Entered temperature ≈ **{cl_temp_c:.1f} °C**")
    cl_fever = (cl_temp_c > 38.0)

    # Additional clinical context (not required for CLABSI criterion)
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

    # Build an 'at risk' signal for CLABSI based on symptoms (even though symptoms are not required to meet CLABSI)
    cl_symptom_any = cl_fever or hypotension or chills

    # ====== Criteria determination (CLABSI) ======
    # NHSN CLABSI (adult): positive blood culture + eligible device days + device-associated.
    meets_clabsi_criteria = (
        positive_bcx and cl_eligible and cl_device_associated
    )

    # Output
    st.subheader("CLABSI Results")
    st.markdown(f"Insertion date: **{cl_insertion_date.isoformat()}**")
    st.markdown(f"Assessment date: **{cl_eval_date.isoformat()}**")
    if cl_removal_date:
        st.markdown(f"Central line removal date: **{cl_removal_date.isoformat()}**")
    if cl_bcx_date:
        st.markdown(f"First positive blood culture date (IWP anchor): **{cl_bcx_date.isoformat()}**")

    st.markdown(f"IWP for symptom eligibility: **{iwp_range_text(cl_iwp_anchor)}** "
                "(7 day window: anchor date ± 3 days)")
    st.markdown(f"Central line days (calendar days): **{cl_days}**")
    st.markdown(f"NHSN device-day eligibility (>2 consecutive calendar days): **{cl_eligible}**")
    st.markdown(f"Device association (in place on assessment date or removed yesterday): **{cl_device_associated}**")

    # Three-state highlighting: Red (meets), Yellow (at risk with symptoms), Green (does not meet and no symptoms)
    if meets_clabsi_criteria:
        st.error("Patient **meets** NHSN CLABSI Criteria (as of assessment date).")
    elif cl_symptom_any:
        st.warning("**At risk** — symptoms within IWP; continue evaluation and monitoring.")
    else:
        st.success("Patient **does not meet** NHSN CLABSI Criteria (as of assessment date).")

    # Diagnostics: why not criteria?
    if not meets_clabsi_criteria:
        reasons = []
        if not positive_bcx: reasons.append("No positive blood culture.")
        if not cl_eligible: reasons.append("Not eligible (>2 central-line days) by assessment date (eligible starting Day 3).")
        if not cl_device_associated: reasons.append("Not device-associated (not in place on assessment date or removed day before).")
        if reasons:
            st.caption("Reason(s) criteria not met: " + " ".join(reasons))

# =========================
# ========= CAUTI =========
# =========================
with tab_cauti:
    st.header("CAUTI")
    st.write("Enter urinary catheter information and symptoms for CAUTI risk and determination.")

    # --- Dates & device presence/removal ---
    cauti_insertion_date = st.date_input(
        "Indwelling urinary catheter insertion date",
        value=dt.date.today(),
        help="Insertion day counts as Day 1. Eligible starting Day 3 (>2 days)."
    )

    cauti_eval_date = st.date_input(
        "Assessment date",
        value=dt.date.today(),
        help="Assessment date = the date the first element used to meet the UTI/CAUTI criterion occurs (within IWP)."
    )

    cauti_in_place = (
        st.radio(
            "Is the indwelling urinary catheter in place on the assessment date?",
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
        help="If removed yesterday (assessment date − 1), event can still be CAUTI-associated. "
             "If removed on the assessment date, it WAS in place on the assessment date.",
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

    # --- NHSN inference: if removed ON the assessment date, device WAS in place on that date ---
    if not cauti_in_place and cauti_removal_date and cauti_removal_date == cauti_eval_date:
        cauti_in_place = True  # infer in place on assessment date

    # --- Validate & compute device days ---
    problems = []
    effective_end = cauti_eval_date if cauti_in_place else cauti_removal_date

    if cauti_insertion_date > cauti_eval_date:
        problems.append("Insertion date cannot be after the assessment date.")
    if cauti_insertion_date > effective_end:
        problems.append("Insertion date cannot be after the removal/assessment date.")

    if problems:
        for p in problems:
            st.error(p)
        st.stop()

    cauti_days = inclusive_days(cauti_insertion_date, effective_end)
    cauti_eligible_days = cauti_days > 2  # Eligible starting Day 3

    # Device association: in place on assessment date OR removed yesterday
    if cauti_in_place:
        cauti_device_associated = True
    else:
        cauti_device_associated = (cauti_removal_date == cauti_eval_date - dt.timedelta(days=1))

    # IWP anchor for CAUTI (urine culture preferred; fallback to assessment date)
    cauti_iwp_anchor = cauti_ucx_date or cauti_eval_date
    cauti_iwp_label = iwp_range_text(cauti_iwp_anchor)

    st.divider()
    st.subheader("Signs & Symptoms")
    st.caption(
        "When an indwelling catheter is in place on symptom onset, eligible symptoms are fever (>38 °C), "
        "suprapubic tenderness, and CVA pain/tenderness. Urgency, frequency, and dysuria apply only when "
        "the catheter has been removed."
    )

    # --- Temperature entry in °F; strict rule > 38 °C after converting ---
    u_temp_f = st.number_input(
        f"Highest documented temperature during IWP? (°F)  (> 100.4 °F / > 38 °C) {cauti_iwp_label}",
        min_value=80.0, max_value=113.0, value=98.6, step=0.1, format="%.1f",
        help=TEMP_RULE
    )
    u_temp_c = f_to_c(u_temp_f)
    st.caption(f"Entered temperature ≈ **{u_temp_c:.1f} °C**")
    fever_u = (u_temp_c > 38.0)

    # --- Symptoms (respect catheter status on assessment date) ---
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

    # Enforce NHSN symptom eligibility based on catheter status on assessment date
    if cauti_in_place:
        urgency = frequency = dysuria = False
        st.info("Catheter is in place on the assessment date: urgency, frequency, and dysuria are excluded by NHSN.")
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

    # Output
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

    # Three-state highlighting: Red (meets), Yellow (at risk with symptoms), Green (does not meet and no symptoms)
    if meets_cauti_criteria:
        st.error("Patient **meets** NHSN CAUTI Criteria (as of assessment date).")
    elif u_symptom_any:
        st.warning("**At risk** — symptoms within IWP; continue evaluation and monitoring.")
    else:
        st.success("Patient **does not meet** NHSN CAUTI Criteria (as of assessment date).")

    # Diagnostics: why not criteria?
    if not meets_cauti_criteria:
        reasons = []
        if not positive_ucx: reasons.append("No positive urine culture.")
        if not cauti_eligible_days: reasons.append("Not eligible (>2 catheter-days) by assessment date (eligible starting Day 3).")
        if not cauti_device_associated: reasons.append("Not device-associated (not in place on assessment date or removed day before).")
        if not u_symptom_any: reasons.append("No eligible symptom within IWP.")
        if reasons:
            st.caption("Reason(s) criteria not met: " + " ".join(reasons))

# =============================
# == Blood Culture Escalation ==
# =============================
with tab_blood:
    render_blood_culture_escalation(BLOOD_LEADERSHIP_LABEL)

# =============================
# == Urine Culture Escalation ==
# =============================
with tab_urine:
    render_urine_culture_escalation(URINE_LEADERSHIP_LABEL)
