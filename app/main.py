from __future__ import annotations

from datetime import date
import html
from pathlib import Path
import sys

# Streamlit may execute this file with app/ as the import root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from core.assessment_pipeline import run_assessment
from core.condition import (
    DOCUMENT_FIELDS,
    GARAGE_TYPES,
    PHYSICAL_FIELDS,
    REPAIR_CATEGORIES,
    TEST_DRIVE_FIELDS,
    ConditionRecord,
    Repair,
    Service,
    YES_NO_UNKNOWN,
)
from core.database import Database
from core.demo_scenarios import build_demo_scenarios
from core.memory_recall import recall_vehicle_history, recall_vehicle_memory
from core.memory_sync import sync_condition_to_memory
from core.models import Car, UNKNOWN, clean_optional_text, new_car_id
from core.pdf_report import build_assessment_pdf
from app.ui_helpers import history_status_copy, humanize_history_finding, verdict_copy


st.set_page_config(
    page_title="VeriCar — Know the car before you buy it",
    page_icon="V",
    layout="wide",
    initial_sidebar_state="collapsed",
)

db = Database()

st.markdown(
    """
    <style>
    :root {
        --ink: var(--text-color, #17283d);
        --muted: color-mix(in srgb, var(--text-color, #17283d) 58%, var(--background-color, #f7f8f6));
        --line: color-mix(in srgb, var(--text-color, #17283d) 16%, var(--background-color, #f7f8f6));
        --paper: var(--background-color, #f7f8f6);
        --white: var(--secondary-background-color, #ffffff);
        --accent: #e16d45;
        --accent-soft: color-mix(in srgb, var(--background-color, #f7f8f6) 88%, var(--accent) 12%);
        --green: #17795c;
        --green-soft: color-mix(in srgb, var(--background-color, #f7f8f6) 88%, var(--green) 12%);
        --amber: #9a6515;
        --amber-soft: color-mix(in srgb, var(--background-color, #f7f8f6) 88%, var(--amber) 12%);
        --red: #a43b38;
        --red-soft: color-mix(in srgb, var(--background-color, #f7f8f6) 88%, var(--red) 12%);
        --blue-soft: color-mix(in srgb, var(--background-color, #f7f8f6) 88%, #4f86ad 12%);
        --shadow: color-mix(in srgb, var(--text-color, #17283d) 10%, transparent);
        --finding-line: color-mix(in srgb, var(--text-color, #17283d) 12%, transparent);
        --expander-bg: color-mix(in srgb, var(--secondary-background-color, #ffffff) 88%, var(--background-color, #f7f8f6));
        --pill-bg: color-mix(in srgb, var(--secondary-background-color, #ffffff) 82%, var(--text-color, #17283d));
    }
    .stApp { background: var(--paper); color: var(--ink); }
    .block-container { max-width: 1120px; padding: 2.1rem 2rem 4rem; }
    [data-testid="stHeader"] { background: transparent; }
    h1, h2, h3 { color: var(--ink); letter-spacing: -0.035em; }
    h1 { font-size: clamp(2.1rem, 4vw, 3.8rem); line-height: .98; margin-bottom: .8rem; }
    h2 { margin-top: 0; }
    h3 { font-size: 1.16rem; }
    .vericar-nav { display:flex; align-items:center; justify-content:space-between; margin-bottom: 2rem; }
    .brand-mark { display:flex; align-items:center; gap:.65rem; color:var(--ink); font-weight:800; letter-spacing:-.04em; font-size:1.25rem; }
    .brand-dot { display:inline-flex; align-items:center; justify-content:center; width:2rem; height:2rem; background:var(--ink); color:white; border-radius:9px; font-size:.9rem; }
    .nav-note { color:var(--muted); font-size:.78rem; letter-spacing:.08em; text-transform:uppercase; }
    .eyebrow { color:var(--accent); font-size:.7rem; font-weight:800; letter-spacing:.16em; text-transform:uppercase; margin:1.65rem 0 .45rem; }
    .lede { color:var(--muted); max-width:650px; font-size:1.05rem; line-height:1.55; }
    .vehicle-card, .history-card, .verdict-card, .soft-card { background:var(--white); border:1px solid var(--line); border-radius:18px; padding:1.25rem 1.4rem; box-shadow:0 12px 28px var(--shadow); }
    .vehicle-card { border-top:4px solid var(--accent); }
    .vehicle-kicker { color:var(--muted); font-size:.76rem; letter-spacing:.12em; text-transform:uppercase; font-weight:800; }
    .vehicle-name { color:var(--ink); font-size:2rem; font-weight:800; letter-spacing:-.05em; margin:.25rem 0 .65rem; }
    .vehicle-meta { color:var(--muted); font-size:.95rem; }
    .price { color:var(--accent); font-weight:800; font-size:1.08rem; }
    .section-rule { border-top:1px solid var(--line); margin:2.25rem 0 1.35rem; }
    .helper { color:var(--muted); font-size:.88rem; line-height:1.5; }
    .status-title { font-weight:800; color:var(--ink); font-size:1.25rem; margin-bottom:.35rem; }
    .status-body { color:var(--muted); line-height:1.5; }
    .status-action { display:inline-block; color:var(--red); font-weight:800; margin-top:.7rem; }
    .history-card.matched { border-left:5px solid var(--green); background:var(--green-soft); }
    .history-card.changed { border-left:5px solid var(--amber); background:var(--amber-soft); }
    .history-card.contradiction { border-left:5px solid var(--red); background:var(--red-soft); }
    .history-card.insufficient, .history-card.no-history, .history-card.unavailable { border-left:5px solid #8495a7; background:var(--blue-soft); }
    .finding-line { border-top:1px solid var(--finding-line); padding:.6rem 0; color:var(--ink); font-size:.92rem; }
    .verdict-card { display:flex; justify-content:space-between; gap:1.5rem; align-items:flex-start; }
    .verdict-card.buy { border-top:5px solid var(--green); }
    .verdict-card.negotiate { border-top:5px solid var(--amber); }
    .verdict-card.avoid { border-top:5px solid var(--red); }
    .verdict-label { font-size:.76rem; letter-spacing:.15em; font-weight:900; }
    .verdict-title { font-size:1.35rem; line-height:1.18; font-weight:800; margin:.35rem 0 .35rem; max-width:620px; }
    .confidence { color:var(--ink); font-size:1.45rem; font-weight:900; white-space:nowrap; }
    .confidence-note { color:var(--muted); font-size:.76rem; max-width:160px; line-height:1.35; }
    .pill { display:inline-block; padding:.22rem .55rem; border-radius:99px; font-size:.72rem; font-weight:800; background:var(--pill-bg); color:var(--muted); }
    .metric-label { color:var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; }
    .metric-value { color:var(--ink); font-size:1.12rem; font-weight:800; margin-top:.2rem; }
    .stButton > button, .stDownloadButton > button { border-radius:10px; min-height:2.8rem; font-weight:800; }
    .stButton > button[kind="primary"] { background:var(--accent); border-color:var(--accent); }
    div[data-testid="stExpander"] { border:1px solid var(--line); border-radius:12px; background:var(--expander-bg); }
    @media (max-width: 700px) {
        .block-container { padding:1.2rem 1rem 3rem; }
        .verdict-card { flex-direction:column; }
        .confidence { white-space:normal; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _safe(value: object) -> str:
    return html.escape(str(value))


def _inr(value: int | None) -> str:
    return UNKNOWN if value is None else f"₹{value:,}"


def _render_history_check(result, memory_result) -> None:
    reconciliation = getattr(result, "history_reconciliation", None)
    status = reconciliation.status if reconciliation is not None else "UNAVAILABLE"
    copy = history_status_copy(status)
    findings = reconciliation.findings if reconciliation is not None else ()
    action_html = (
        f'<div class="status-action">{_safe(copy["action"])}</div>'
        if copy["action"]
        else ""
    )

    st.markdown('<div class="eyebrow">HISTORICAL CHECK</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="history-card {copy["tone"]}">'
        f'<div class="status-title">{_safe(copy["title"])}</div>'
        f'<div class="status-body">{_safe(copy["body"])}</div>'
        f'{action_html}'
        '</div>',
        unsafe_allow_html=True,
    )

    if findings:
        st.markdown("**What we could compare**")
        for finding in findings[:4]:
            st.markdown(f'<div class="finding-line">{_safe(humanize_history_finding(finding))}</div>', unsafe_allow_html=True)
        if len(findings) > 4:
            with st.expander(f"See {len(findings) - 4} more comparisons"):
                for finding in findings[4:]:
                    st.write(humanize_history_finding(finding))
    elif status == "NO_HISTORY":
        st.caption("A first record gives VeriCar nothing earlier to compare yet.")
    elif status == "UNAVAILABLE" and getattr(memory_result, "error", None):
        st.caption("The assessment remains deterministic; history availability is shown separately from the verdict.")







def _render_india_checks() -> None:
    with st.expander("India-specific document checks", expanded=False):
        st.caption(
            "VeriCar is designed for Indian used-car buyers. These checks use the "
            "documents and records you provide; no extra API key is required."
        )
        st.markdown(
            """
            **Before relying on a seller's history, verify:**
            - **RC / registration:** Compare the registration number, chassis/VIN and vehicle details with the physical car and the official registration record.
            - **Insurance:** Check the current policy, insurer, validity and claim information with the insurer.
            - **PUC:** Verify the pollution certificate and its validity.
            - **Service history:** Prefer dated workshop/dealer invoices and odometer readings over an unsupported service-history claim.
            - **Accident / repair history:** Cross-check seller statements against invoices, inspection findings and insurance records where available.
            - **Pending challans:** Check the official government e-challan service separately using the vehicle details it requires.
            """
        )
        st.info(
            "VeriCar does not currently claim direct access to VAHAN, mParivahan, "
            "insurance, workshop, or e-challan databases. Those services require "
            "authorized access or provider-specific APIs. We will not invent an "
            "integration or ask you for a random API key."
        )


def _render_memory_insights(result) -> None:
    analysis = getattr(result, "memory_analysis", None)
    reconciliation = getattr(result, "history_reconciliation", None)
    if analysis is None:
        return

    influential = analysis.influential_memories
    longitudinal = getattr(reconciliation, "longitudinal_findings", ()) if reconciliation else ()
    model_observations = analysis.model_observations

    if not (influential or longitudinal or model_observations):
        return

    with st.expander("Historical memory insights", expanded=False):
        if influential:
            st.markdown("**Influential historical evidence**")
            for item in influential:
                observed = item.observed_at.isoformat() if item.observed_at else "date unavailable"
                st.write(f"- **{item.field}** — {item.reason} ({observed}; source: {item.source_type})")

        if longitudinal:
            st.markdown("**Longitudinal changes**")
            for finding in longitudinal:
                st.write(f"- {finding.message}")

        if model_observations:
            st.markdown("**Model-level observations**")
            st.caption("These are repeated observations from this vehicle's history, not manufacturer specifications or reliability statistics.")
            for observation in model_observations:
                st.write(f"- {observation.pattern} Reports: {observation.count}.")


def _render_verdict(assessment) -> None:
    copy = verdict_copy(assessment.verdict)
    st.markdown('<div class="eyebrow">VERICAR ASSESSMENT</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="verdict-card {copy["tone"]}">'
        f'<div><div class="verdict-label">{_safe(copy["label"])}</div>'
        f'<div class="verdict-title">{_safe(copy["title"])}</div>'
        '<div class="helper">The verdict is based on the evidence provided, not a guarantee of vehicle condition.</div></div>'
        f'<div><div class="confidence">Confidence: {_safe(assessment.confidence)}%</div>'
        '<div class="confidence-note">Confidence reflects how complete and consistent the available evidence is.</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_findings(assessment) -> None:
    st.markdown('<div class="eyebrow">WHY THIS RESULT</div>', unsafe_allow_html=True)
    st.subheader("What stood out")
    groups = (
        ("Important", assessment.critical_findings, "red"),
        ("Needs attention", assessment.warning_findings, "amber"),
        ("Good signs", assessment.info_findings, "green"),
    )
    shown = False
    for label, findings, _tone in groups:
        if findings:
            shown = True
            st.markdown(f"**{label}**")
            for finding in findings:
                st.write(f"• {finding}")
    if not shown:
        st.caption("No additional findings were recorded from the available inputs.")


def _render_next_checks(assessment) -> None:
    st.markdown('<div class="eyebrow">BEFORE YOU PAY</div>', unsafe_allow_html=True)
    st.subheader("Check these next")
    st.caption("These actions help you verify the evidence before making a payment or signing anything.")
    for check in assessment.next_checks:
        st.markdown(f"- {check}")


st.markdown(
    '<div class="vericar-nav"><div class="brand-mark"><span class="brand-dot">V</span> VeriCar</div><div class="nav-note">Know the car before you buy it.</div></div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="eyebrow">USED-CAR HISTORY CHECK</div>', unsafe_allow_html=True)
st.title("Check this car with more confidence.")
st.markdown(
    '<div class="lede">Record what you know, compare it with any previous VeriCar record, and get a clear next step before you buy.</div>',
    unsafe_allow_html=True,
)

with st.expander("Load a synthetic demo", expanded=False):
    st.caption("Demo scenarios use synthetic data. They are useful for exploring the flow and never represent a real vehicle.")
    demo_scenarios = build_demo_scenarios()
    demo_names = {scenario.name: scenario for scenario in demo_scenarios}
    selected_demo_name = st.selectbox("Choose a scenario", ["Select a scenario"] + list(demo_names), key="demo_scenario_name")
    if st.button("Load demo scenario", use_container_width=True):
        if selected_demo_name == "Select a scenario":
            st.warning("Choose a demo scenario first.")
        else:
            scenario = demo_names[selected_demo_name]
            db.save_car(scenario.car)
            db.save_condition(scenario.condition)
            st.session_state.car_id = scenario.car.car_id
            st.session_state.saved_car = scenario.car
            st.session_state.editing_car = scenario.car.to_record()
            st.session_state.saved_condition = scenario.condition
            st.session_state.pop("assessment_result", None)
            st.session_state.pop("memory_result", None)
            st.success(f"Loaded synthetic scenario: {scenario.name}.")
            st.caption(scenario.description)

if "car_id" not in st.session_state:
    st.session_state.car_id = new_car_id()

existing = st.session_state.get("editing_car")
fuel_options = [UNKNOWN, "Petrol", "Diesel", "CNG", "Hybrid", "Electric"]
transmission_options = [UNKNOWN, "Manual", "Automatic", "AMT", "CVT", "DCT"]

st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">1 · VEHICLE SETUP</div>', unsafe_allow_html=True)
st.subheader("Start with the car’s identity")
st.caption("Unknown values are valid. VeriCar keeps them unknown instead of guessing.")

with st.form("car_setup"):
    identity = st.columns(3)
    with identity[0]:
        brand = st.text_input("Brand *", value=existing["brand"] if existing else "")
    with identity[1]:
        model = st.text_input("Model *", value=existing["model"] if existing else "")
    with identity[2]:
        current_year = date.today().year
        manufacture_year = st.number_input("Manufacture year *", min_value=1950, max_value=current_year, value=int(existing["manufacture_year"]) if existing else current_year, step=1)

    details = st.columns(3)
    with details[0]:
        variant = st.text_input("Variant", value=(existing["variant"] or "") if existing else "")
        fuel_type = st.selectbox("Fuel type", fuel_options, index=fuel_options.index(existing["fuel_type"]) if existing and existing["fuel_type"] in fuel_options else 0)
    with details[1]:
        transmission = st.selectbox("Transmission", transmission_options, index=transmission_options.index(existing["transmission"]) if existing and existing["transmission"] in transmission_options else 0)
        month_options = [None, *range(1, 13)]
        manufacture_month = st.selectbox("Manufacture month", month_options, format_func=lambda value: UNKNOWN if value is None else date(2000, value, 1).strftime("%B"), index=int(existing["manufacture_month"]) if existing and existing["manufacture_month"] else 0)
    with details[2]:
        vin = st.text_input("VIN / chassis number", value=(existing["vin"] or "") if existing else "")
        registration_state = st.text_input("Registration state", value=(existing["registration_state"] or "") if existing else "")

    with st.expander("Dates and ownership details"):
        dates = st.columns(2)
        with dates[0]:
            registration_date = st.date_input("Registration date", value=date.fromisoformat(existing["registration_date"]) if existing and existing["registration_date"] else None)
        with dates[1]:
            purchase_date = st.date_input("Purchase date", value=date.fromisoformat(existing["purchase_date"]) if existing and existing["purchase_date"] else None)
        usage = st.columns(3)
        with usage[0]:
            previous_owners = st.number_input("Previous owners", min_value=0, max_value=20, value=int(existing["previous_owners"]) if existing and existing["previous_owners"] is not None else 0)
        with usage[1]:
            odometer_km = st.number_input("Current odometer (km)", min_value=0, max_value=2_000_000, value=int(existing["odometer_km"]) if existing and existing["odometer_km"] is not None else 0, step=100)
        with usage[2]:
            asking_price_inr = st.number_input("Asking price (INR)", min_value=0, max_value=100_000_000, value=int(existing["asking_price_inr"]) if existing and existing["asking_price_inr"] is not None else 0, step=10_000)

    submitted = st.form_submit_button("Save vehicle and continue", type="primary", use_container_width=True)

if submitted:
    if not brand.strip() or not model.strip():
        st.error("Brand and model are required.")
    else:
        car = Car(
            car_id=st.session_state.car_id,
            brand=brand.strip(), model=model.strip(), manufacture_year=int(manufacture_year),
            variant=clean_optional_text(variant), fuel_type=fuel_type, transmission=transmission,
            manufacture_month=manufacture_month, registration_date=registration_date,
            purchase_date=purchase_date, vin=clean_optional_text(vin),
            registration_state=clean_optional_text(registration_state),
            previous_owners=previous_owners or None, odometer_km=odometer_km or None,
            asking_price_inr=asking_price_inr or None,
        )
        db.save_car(car)
        st.session_state.saved_car = car
        st.session_state.editing_car = car.to_record()
        st.success("Vehicle saved. Add the condition details below.")

if "saved_car" in st.session_state:
    car: Car = st.session_state.saved_car
    vehicle_meta = " · ".join(filter(None, [str(car.manufacture_year), car.fuel_type if car.fuel_type != UNKNOWN else None, car.transmission if car.transmission != UNKNOWN else None]))
    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="vehicle-card"><div class="vehicle-kicker">YOUR VEHICLE</div><div class="vehicle-name">{_safe(car.brand)} {_safe(car.model)}</div>'
        f'<div class="vehicle-meta">{_safe(vehicle_meta or UNKNOWN)} · {_safe(f"{car.odometer_km:,} km" if car.odometer_km is not None else UNKNOWN)}</div>'
        f'<div class="price">{_safe(_inr(car.asking_price_inr))} asking price</div></div>',
        unsafe_allow_html=True,
    )

    condition = db.get_condition(car.car_id) or ConditionRecord.empty(car.car_id)
    st.markdown('<div class="eyebrow">2 · CONDITION INPUT</div>', unsafe_allow_html=True)
    st.subheader("Tell us what you know about the car")
    st.caption("Short sections keep the check manageable. Select Unknown when you do not have enough information.")

    with st.form("condition_input"):
        with st.expander("Seller & history", expanded=True):
            st.caption("Record what the seller says and what can be supported by service or repair records.")
            repair_count = st.number_input("Number of repairs", min_value=0, max_value=30, value=len(condition.repairs), step=1)
            repairs: list[Repair] = []
            for index in range(int(repair_count)):
                prior = condition.repairs[index] if index < len(condition.repairs) else None
                st.markdown(f"**Repair {index + 1}**")
                cols = st.columns(3)
                with cols[0]:
                    repair_date = st.date_input("Date", value=prior.observed_at if prior else date.today(), key=f"repair_date_{car.car_id}_{index}")
                with cols[1]:
                    repair_odo = st.number_input("Odometer (km)", min_value=0, max_value=2_000_000, value=prior.odometer_km or 0 if prior else 0, step=100, key=f"repair_odo_{car.car_id}_{index}")
                with cols[2]:
                    category = st.selectbox("Category", REPAIR_CATEGORIES, index=REPAIR_CATEGORIES.index(prior.category) if prior and prior.category in REPAIR_CATEGORIES else 0, key=f"repair_category_{car.car_id}_{index}")
                description = st.text_input("What was repaired?", value=prior.description if prior else "", key=f"repair_description_{car.car_id}_{index}")
                cols = st.columns(2)
                with cols[0]:
                    cost = st.number_input("Cost (INR)", min_value=0, max_value=10_000_000, value=prior.cost_inr or 0 if prior else 0, step=1_000, key=f"repair_cost_{car.car_id}_{index}")
                with cols[1]:
                    garage = st.selectbox("Garage type", GARAGE_TYPES, index=GARAGE_TYPES.index(prior.garage_type) if prior and prior.garage_type in GARAGE_TYPES else 0, key=f"repair_garage_{car.car_id}_{index}")
                repairs.append(Repair(observed_at=repair_date, odometer_km=repair_odo or None, category=category, description=description.strip(), cost_inr=cost or None, garage_type=garage))
            st.markdown("**Service history**")
            service_count = st.number_input("Number of recorded services", min_value=0, max_value=40, value=len(condition.services), step=1)
            services: list[Service] = []
            for index in range(int(service_count)):
                prior = condition.services[index] if index < len(condition.services) else None
                cols = st.columns(3)
                with cols[0]:
                    service_date = st.date_input("Service date", value=prior.observed_at if prior else date.today(), key=f"service_date_{car.car_id}_{index}")
                with cols[1]:
                    service_odo = st.number_input("Odometer (km)", min_value=0, max_value=2_000_000, value=prior.odometer_km or 0 if prior else 0, step=100, key=f"service_odo_{car.car_id}_{index}")
                with cols[2]:
                    service_description = st.text_input("What was done?", value=prior.description if prior else "", key=f"service_description_{car.car_id}_{index}")
                gap_notes = st.text_input("Service gap / interval notes", value=prior.gap_notes or "" if prior else "", key=f"service_gap_{car.car_id}_{index}")
                services.append(Service(observed_at=service_date, odometer_km=service_odo or None, description=service_description.strip(), gap_notes=gap_notes.strip() or None))

            accident_status, repainted_panels, airbag_deployed = st.columns(3)
            with accident_status:
                accident_status_value = st.selectbox("Accident history", YES_NO_UNKNOWN, index=YES_NO_UNKNOWN.index(condition.accident_status) if condition.accident_status in YES_NO_UNKNOWN else 2)
            with repainted_panels:
                repainted_panels_value = st.selectbox("Repainted panels", YES_NO_UNKNOWN, index=YES_NO_UNKNOWN.index(condition.repainted_panels) if condition.repainted_panels in YES_NO_UNKNOWN else 2)
            with airbag_deployed:
                airbag_deployed_value = st.selectbox("Airbag deployed", YES_NO_UNKNOWN, index=YES_NO_UNKNOWN.index(condition.airbag_deployed) if condition.airbag_deployed in YES_NO_UNKNOWN else 2)

            seller_claims = st.text_area("Seller claims", value=condition.seller_claims or "", height=90, placeholder='Examples: “Never accidented” or “Full service history”.')

        with st.expander("Documents", expanded=False):
            st.caption("Documents often resolve the biggest uncertainties before a purchase.")
            documents: dict[str, str] = {}
            doc_items = list(DOCUMENT_FIELDS.items())
            for start in range(0, len(doc_items), 2):
                cols = st.columns(2)
                for column, (key, label) in zip(cols, doc_items[start:start + 2]):
                    with column:
                        current = condition.documents.get(key, UNKNOWN)
                        documents[key] = st.selectbox(label, YES_NO_UNKNOWN, index=YES_NO_UNKNOWN.index(current) if current in YES_NO_UNKNOWN else 2, key=f"document_{car.car_id}_{key}")

        with st.expander("Exterior & interior", expanded=False):
            st.caption("A walkaround can reveal repairs, water exposure, and wear that paperwork misses.")
            physical: dict[str, str] = {}
            physical_items = list(PHYSICAL_FIELDS.items())
            for start in range(0, len(physical_items), 2):
                cols = st.columns(2)
                for column, (key, label) in zip(cols, physical_items[start:start + 2]):
                    with column:
                        current = condition.physical_inspection.get(key, UNKNOWN)
                        physical[key] = st.selectbox(label, YES_NO_UNKNOWN, index=YES_NO_UNKNOWN.index(current) if current in YES_NO_UNKNOWN else 2, key=f"physical_{car.car_id}_{key}")

        with st.expander("Under the hood", expanded=False):
            st.caption("Record observations from the engine bay or a mechanic; do not guess at a diagnosis.")
            obd_notes = st.text_area("OBD scan notes", value=condition.obd_notes or "", height=90, placeholder="Optional scan codes, freeze-frame notes, or observations.")
            tyre_dot_codes = st.text_input("Tyre DOT date codes", value=condition.tyre_dot_codes or "", placeholder="Optional. Record each tyre's DOT code if available.")

        with st.expander("Test drive", expanded=False):
            st.caption("Use a short drive to record what you actually felt or heard.")
            test_drive: dict[str, str] = {}
            for key, label in TEST_DRIVE_FIELDS.items():
                current = condition.test_drive.get(key, UNKNOWN)
                test_drive[key] = st.selectbox(label, YES_NO_UNKNOWN, index=YES_NO_UNKNOWN.index(current) if current in YES_NO_UNKNOWN else 2, key=f"test_drive_{car.car_id}_{key}")

        save_condition = st.form_submit_button("Save condition and run the check later", type="primary", use_container_width=True)

    if save_condition:
        saved_condition = ConditionRecord(car_id=car.car_id, repairs=repairs, services=services, accident_status=accident_status_value, repainted_panels=repainted_panels_value, airbag_deployed=airbag_deployed_value, documents=documents, physical_inspection=physical, test_drive=test_drive, obd_notes=obd_notes.strip() or None, tyre_dot_codes=tyre_dot_codes.strip() or None, seller_claims=seller_claims.strip() or None)
        db.save_condition(saved_condition)
        st.session_state.saved_condition = saved_condition
        report_id, memory_error = sync_condition_to_memory(car, saved_condition, db)
        if memory_error is None:
            st.success("Condition saved. VeriCar retained the record for future comparison.")
        else:
            st.warning("Condition saved locally. Vehicle history could not be retained right now; the local assessment still works.")

    saved_condition = db.get_condition(car.car_id)
    if saved_condition:
        st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">3 · REVIEW</div>', unsafe_allow_html=True)
        metric_cols = st.columns(4)
        metric_cols[0].markdown(f'<div class="metric-label">Repairs</div><div class="metric-value">{len(saved_condition.repairs)}</div>', unsafe_allow_html=True)
        metric_cols[1].markdown(f'<div class="metric-label">Services</div><div class="metric-value">{len(saved_condition.services)}</div>', unsafe_allow_html=True)
        metric_cols[2].markdown(f'<div class="metric-label">Flood indicators</div><div class="metric-value">{sum(1 for key in ("flood_signs",) if saved_condition.physical_inspection.get(key) == "Yes")}</div>', unsafe_allow_html=True)
        unknown_count = sum(value == UNKNOWN for values in (saved_condition.documents, saved_condition.physical_inspection, saved_condition.test_drive) for value in values.values())
        metric_cols[3].markdown(f'<div class="metric-label">Unknown checks</div><div class="metric-value">{unknown_count}</div>', unsafe_allow_html=True)
        st.caption("Unknown is not treated as No. It remains missing evidence and can lower confidence.")

        if st.button("Assess this car", type="primary", use_container_width=True):
            try:
                memory_result = recall_vehicle_memory(car, query="repairs, services, accidents, recurring issues, and contradictions")
                history_result = recall_vehicle_history(car)
                st.session_state.memory_result = memory_result
                st.session_state.history_memory_result = history_result
                history_items = list(history_result.items) if history_result.status == "AVAILABLE" else None
                result = run_assessment(car, saved_condition, db, today=date.today(), generate_explanation=True, history_items=history_items)
                st.session_state.assessment_result = result
            except Exception as exc:
                st.error("Assessment could not be completed: " + str(exc))
                st.session_state.pop("assessment_result", None)

        result = st.session_state.get("assessment_result")
        memory_result = st.session_state.get("memory_result")
        if result is not None:
            # History is deliberately rendered before the deterministic verdict.
            _render_history_check(result, memory_result)
            _render_memory_insights(result)
            _render_india_checks()

        if result is not None and result.profile_resolution.status == "MISSING":
            st.warning("No expected profile is available for this exact vehicle configuration. No verdict was generated.")

        if result is not None and result.assessment is not None:
            assessment = result.assessment
            _render_verdict(assessment)
            summary = st.columns(3)
            low, high = assessment.near_term_repair_range_inr
            summary[0].markdown(f'<div class="metric-label">Near-term repair range</div><div class="metric-value">₹{low:,}–₹{high:,}</div>', unsafe_allow_html=True)
            summary[1].markdown(f'<div class="metric-label">Negotiation reduction</div><div class="metric-value">₹{assessment.negotiation_reduction_inr:,}</div>', unsafe_allow_html=True)
            summary[2].markdown(f'<div class="metric-label">Evidence source</div><div class="metric-value">Recorded inputs</div>', unsafe_allow_html=True)

            _render_findings(assessment)
            _render_next_checks(assessment)

            if result.explanation is not None:
                with st.expander("AI explanation", expanded=False):
                    st.caption("The AI explains the evidence provided. It does not decide the verdict.")
                    explanation = result.explanation.llm
                    st.write(explanation.summary)
                    if explanation.evidence_explanations:
                        st.markdown("**Evidence explained**")
                        for item in explanation.evidence_explanations:
                            st.write(f"• {item}")
                    if explanation.contradictions:
                        st.markdown("**Contradictions mentioned by the explanation**")
                        for item in explanation.contradictions:
                            st.write(f"• {item}")
                    if explanation.ai_estimates:
                        st.markdown("**AI estimates — review independently**")
                        for item in explanation.ai_estimates:
                            st.write(f"• {item}")
            else:
                st.info("The AI explanation is unavailable. The deterministic assessment remains valid and does not depend on it.")

            try:
                report_pdf = build_assessment_pdf(car, saved_condition, result)
                st.download_button("Download inspection report", data=report_pdf, file_name=f"vericar-assessment-{car.car_id}.pdf", mime="application/pdf", use_container_width=True)
            except Exception as exc:
                st.error("Inspection report could not be generated: " + str(exc))

        with st.expander("View recalled history notes", expanded=False):
            if memory_result is None:
                st.caption("Run an assessment to check the vehicle's previous VeriCar record.")
            elif memory_result.status == "UNAVAILABLE":
                st.caption("Vehicle history is unavailable. This does not mean the vehicle has no history.")
            elif not memory_result.items:
                st.caption("No matching historical notes were returned.")
            else:
                st.caption("These notes are historical evidence, not automatic truth. They do not change the deterministic verdict.")
                for item in memory_result.items:
                    st.write(item.text)

st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
st.caption("VeriCar helps you inspect evidence. It does not replace an independent inspection, original document checks, or professional mechanical advice.")
