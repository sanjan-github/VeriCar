from __future__ import annotations

from datetime import date, datetime, timezone
import asyncio

import streamlit as st

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
from core.memory_sync import sync_condition_to_memory
from core.memory_report import build_vehicle_memory_report
from core.memory_recall import recall_vehicle_memory
from core.assessment_pipeline import run_assessment
from memory.hindsight import HindsightMemory
from core.models import Car, UNKNOWN, clean_optional_text, new_car_id


st.set_page_config(page_title="VeriCar — Vehicle History", page_icon="V", layout="wide")

db = Database()

st.markdown(
    """
    <style>
    .block-container { max-width: 1180px; padding-top: 2.5rem; }
    .vericar-brand { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em; }
    .eyebrow { font-size: .72rem; font-weight: 700; letter-spacing: .14em; color: #667085; margin-bottom: .35rem; }
    .lede { color: #667085; font-size: 1.02rem; }
    .section-rule { border-top: 1px solid #e4e7ec; margin: 1.5rem 0; }
    .source-note { color: #667085; font-size: .82rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="vericar-brand">V &nbsp; VeriCar</div>', unsafe_allow_html=True)
st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">VEHICLE SETUP</div>', unsafe_allow_html=True)
st.title("Build the vehicle record before assessing its history")
st.markdown(
    "Enter the known vehicle details. Unknown values are valid and remain explicitly unknown; "
    "they will lower confidence later rather than being guessed."
)

st.markdown('<div class="eyebrow">DEMO MODE</div>', unsafe_allow_html=True)
st.caption(
    "Synthetic demo data only. Loading a scenario replaces the current in-memory vehicle selection "
    "and condition record so the real assessment pipeline can be exercised without manual entry."
)
demo_scenarios = build_demo_scenarios()
demo_names = {scenario.name: scenario for scenario in demo_scenarios}
selected_demo_name = st.selectbox(
    "Demo scenario",
    ["Select a scenario"] + list(demo_names),
    key="demo_scenario_name",
)
if st.button("Load demo scenario", use_container_width=True):
    if selected_demo_name == "Select a scenario":
        st.warning("Select a demo scenario first.")
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

st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)

if "car_id" not in st.session_state:
    st.session_state.car_id = new_car_id()

existing = st.session_state.get("editing_car")
fuel_options = [UNKNOWN, "Petrol", "Diesel", "CNG", "Hybrid", "Electric"]
transmission_options = [UNKNOWN, "Manual", "Automatic", "AMT", "CVT", "DCT"]

with st.form("car_setup"):
    st.subheader("Identity")
    identity = st.columns(3)
    with identity[0]:
        brand = st.text_input("Brand *", value=existing["brand"] if existing else "")
    with identity[1]:
        model = st.text_input("Model *", value=existing["model"] if existing else "")
    with identity[2]:
        current_year = date.today().year
        manufacture_year = st.number_input(
            "Manufacture year *", min_value=1950, max_value=current_year,
            value=int(existing["manufacture_year"]) if existing else current_year, step=1,
        )

    details = st.columns(3)
    with details[0]:
        variant = st.text_input("Variant", value=(existing["variant"] or "") if existing else "")
        fuel_type = st.selectbox(
            "Fuel type", fuel_options,
            index=fuel_options.index(existing["fuel_type"]) if existing and existing["fuel_type"] in fuel_options else 0,
        )
    with details[1]:
        transmission = st.selectbox(
            "Transmission", transmission_options,
            index=transmission_options.index(existing["transmission"]) if existing and existing["transmission"] in transmission_options else 0,
        )
        month_options = [None, *range(1, 13)]
        manufacture_month = st.selectbox(
            "Manufacture month", month_options,
            format_func=lambda value: UNKNOWN if value is None else date(2000, value, 1).strftime("%B"),
            index=int(existing["manufacture_month"]) if existing and existing["manufacture_month"] else 0,
        )
    with details[2]:
        vin = st.text_input("VIN / chassis number", value=(existing["vin"] or "") if existing else "")
        registration_state = st.text_input("Registration state", value=(existing["registration_state"] or "") if existing else "")

    dates = st.columns(2)
    with dates[0]:
        registration_date = st.date_input(
            "Registration date",
            value=date.fromisoformat(existing["registration_date"]) if existing and existing["registration_date"] else None,
        )
    with dates[1]:
        purchase_date = st.date_input(
            "Purchase date",
            value=date.fromisoformat(existing["purchase_date"]) if existing and existing["purchase_date"] else None,
        )

    usage = st.columns(3)
    with usage[0]:
        previous_owners = st.number_input(
            "Previous owners", min_value=0, max_value=20,
            value=int(existing["previous_owners"]) if existing and existing["previous_owners"] is not None else 0,
        )
    with usage[1]:
        odometer_km = st.number_input(
            "Current odometer (km)", min_value=0, max_value=2_000_000,
            value=int(existing["odometer_km"]) if existing and existing["odometer_km"] is not None else 0, step=100,
        )
    with usage[2]:
        asking_price_inr = st.number_input(
            "Asking price (INR)", min_value=0, max_value=100_000_000,
            value=int(existing["asking_price_inr"]) if existing and existing["asking_price_inr"] is not None else 0, step=10_000,
        )

    st.caption("Unknown values are valid. Blank text and zero numeric values are treated as not provided in this first stage.")
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
        st.success(f"Vehicle saved as {car.car_id}.")

if "saved_car" in st.session_state:
    car: Car = st.session_state.saved_car
    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">VEHICLE RECORD</div>', unsafe_allow_html=True)
    st.subheader(f"{car.brand} {car.model} · {car.manufacture_year}")
    summary = st.columns(4)
    summary[0].metric("Vehicle ID", car.car_id)
    summary[1].metric("Memory key", car.memory_key)
    summary[2].metric("Odometer", f"{car.odometer_km:,} km" if car.odometer_km is not None else UNKNOWN)
    summary[3].metric("Asking price", f"₹{car.asking_price_inr:,}" if car.asking_price_inr is not None else UNKNOWN)

    condition = db.get_condition(car.car_id) or ConditionRecord.empty(car.car_id)
    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">CONDITION INPUT</div>', unsafe_allow_html=True)
    st.header("What is known about this vehicle's condition?")
    st.markdown(
        "Record observed history rather than conclusions. Every checklist item supports **Yes**, **No**, "
        "or **Unknown**; Unknown is preserved as missing evidence."
    )

    with st.form("condition_input"):
        st.subheader("Repairs")
        repair_count = st.number_input(
            "Number of repairs", min_value=0, max_value=30,
            value=len(condition.repairs), step=1,
        )
        repairs: list[Repair] = []
        for index in range(int(repair_count)):
            prior = condition.repairs[index] if index < len(condition.repairs) else None
            st.markdown(f"**Repair {index + 1}**")
            cols = st.columns(3)
            with cols[0]:
                repair_date = st.date_input(
                    "Date", value=prior.observed_at if prior else date.today(),
                    key=f"repair_date_{car.car_id}_{index}",
                )
            with cols[1]:
                repair_odo = st.number_input(
                    "Odometer (km)", min_value=0, max_value=2_000_000,
                    value=prior.odometer_km or 0 if prior else 0, step=100,
                    key=f"repair_odo_{car.car_id}_{index}",
                )
            with cols[2]:
                category = st.selectbox(
                    "Category", REPAIR_CATEGORIES,
                    index=REPAIR_CATEGORIES.index(prior.category) if prior and prior.category in REPAIR_CATEGORIES else 0,
                    key=f"repair_category_{car.car_id}_{index}",
                )
            description = st.text_input(
                "Description", value=prior.description if prior else "",
                key=f"repair_description_{car.car_id}_{index}",
            )
            cols = st.columns(2)
            with cols[0]:
                cost = st.number_input(
                    "Cost (INR)", min_value=0, max_value=10_000_000,
                    value=prior.cost_inr or 0 if prior else 0, step=1_000,
                    key=f"repair_cost_{car.car_id}_{index}",
                )
            with cols[1]:
                garage = st.selectbox(
                    "Garage type", GARAGE_TYPES,
                    index=GARAGE_TYPES.index(prior.garage_type) if prior and prior.garage_type in GARAGE_TYPES else 0,
                    key=f"repair_garage_{car.car_id}_{index}",
                )
            repairs.append(
                Repair(
                    observed_at=repair_date,
                    odometer_km=repair_odo or None,
                    category=category,
                    description=description.strip(),
                    cost_inr=cost or None,
                    garage_type=garage,
                )
            )
            st.markdown("---")

        st.subheader("Service history")
        service_count = st.number_input(
            "Number of recorded services", min_value=0, max_value=40,
            value=len(condition.services), step=1,
        )
        services: list[Service] = []
        for index in range(int(service_count)):
            prior = condition.services[index] if index < len(condition.services) else None
            cols = st.columns(3)
            with cols[0]:
                service_date = st.date_input(
                    "Service date", value=prior.observed_at if prior else date.today(),
                    key=f"service_date_{car.car_id}_{index}",
                )
            with cols[1]:
                service_odo = st.number_input(
                    "Odometer (km)", min_value=0, max_value=2_000_000,
                    value=prior.odometer_km or 0 if prior else 0, step=100,
                    key=f"service_odo_{car.car_id}_{index}",
                )
            with cols[2]:
                service_description = st.text_input(
                    "What was done?", value=prior.description if prior else "",
                    key=f"service_description_{car.car_id}_{index}",
                )
            gap_notes = st.text_input(
                "Service gap / interval notes",
                value=prior.gap_notes or "" if prior else "",
                key=f"service_gap_{car.car_id}_{index}",
                help="Optional note such as '18 months since previous service' or 'records missing'.",
            )
            services.append(
                Service(
                    observed_at=service_date,
                    odometer_km=service_odo or None,
                    description=service_description.strip(),
                    gap_notes=gap_notes.strip() or None,
                )
            )
            st.markdown("---")

        st.subheader("Accident and body history")
        cols = st.columns(3)
        with cols[0]:
            accident_status = st.selectbox(
                "Accident history", YES_NO_UNKNOWN,
                index=YES_NO_UNKNOWN.index(condition.accident_status) if condition.accident_status in YES_NO_UNKNOWN else 2,
            )
        with cols[1]:
            repainted_panels = st.selectbox(
                "Repainted panels", YES_NO_UNKNOWN,
                index=YES_NO_UNKNOWN.index(condition.repainted_panels) if condition.repainted_panels in YES_NO_UNKNOWN else 2,
            )
        with cols[2]:
            airbag_deployed = st.selectbox(
                "Airbag deployed", YES_NO_UNKNOWN,
                index=YES_NO_UNKNOWN.index(condition.airbag_deployed) if condition.airbag_deployed in YES_NO_UNKNOWN else 2,
            )

        st.subheader("Documents")
        documents: dict[str, str] = {}
        doc_items = list(DOCUMENT_FIELDS.items())
        for start in range(0, len(doc_items), 2):
            cols = st.columns(2)
            for column, (key, label) in zip(cols, doc_items[start:start + 2]):
                with column:
                    current = condition.documents.get(key, UNKNOWN)
                    documents[key] = st.selectbox(
                        label, YES_NO_UNKNOWN,
                        index=YES_NO_UNKNOWN.index(current) if current in YES_NO_UNKNOWN else 2,
                        key=f"document_{car.car_id}_{key}",
                    )

        st.subheader("Physical inspection")
        physical: dict[str, str] = {}
        physical_items = list(PHYSICAL_FIELDS.items())
        for start in range(0, len(physical_items), 2):
            cols = st.columns(2)
            for column, (key, label) in zip(cols, physical_items[start:start + 2]):
                with column:
                    current = condition.physical_inspection.get(key, UNKNOWN)
                    physical[key] = st.selectbox(
                        label, YES_NO_UNKNOWN,
                        index=YES_NO_UNKNOWN.index(current) if current in YES_NO_UNKNOWN else 2,
                        key=f"physical_{car.car_id}_{key}",
                    )

        st.subheader("Test drive")
        test_drive: dict[str, str] = {}
        for key, label in TEST_DRIVE_FIELDS.items():
            current = condition.test_drive.get(key, UNKNOWN)
            test_drive[key] = st.selectbox(
                label, YES_NO_UNKNOWN,
                index=YES_NO_UNKNOWN.index(current) if current in YES_NO_UNKNOWN else 2,
                key=f"test_drive_{car.car_id}_{key}",
            )

        st.subheader("Additional evidence")
        obd_notes = st.text_area(
            "OBD scan notes", value=condition.obd_notes or "", height=100,
            placeholder="Optional scan codes, freeze-frame notes, or observations.",
        )
        tyre_dot_codes = st.text_input(
            "Tyre DOT date codes", value=condition.tyre_dot_codes or "",
            placeholder="Optional. Record each tyre's DOT code if available.",
        )
        seller_claims = st.text_area(
            "Seller claims", value=condition.seller_claims or "", height=100,
            placeholder='Examples: "Never accidented" or "Full service history".',
        )

        save_condition = st.form_submit_button(
            "Save condition history", type="primary", use_container_width=True
        )

    if save_condition:
        saved_condition = ConditionRecord(
            car_id=car.car_id,
            repairs=repairs,
            services=services,
            accident_status=accident_status,
            repainted_panels=repainted_panels,
            airbag_deployed=airbag_deployed,
            documents=documents,
            physical_inspection=physical,
            test_drive=test_drive,
            obd_notes=obd_notes.strip() or None,
            tyre_dot_codes=tyre_dot_codes.strip() or None,
            seller_claims=seller_claims.strip() or None,
        )
        db.save_condition(saved_condition)
        st.session_state.saved_condition = saved_condition
        report_id, memory_error = sync_condition_to_memory(car, saved_condition, db)
        if memory_error is None:
            st.success("Condition history saved and retained in vehicle memory.")
        else:
            st.warning("Condition history saved locally; report " + report_id + " remains unsynced because Hindsight is unavailable.")

    saved_condition = db.get_condition(car.car_id)
    if saved_condition:
        st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">RECORDED CONDITION</div>', unsafe_allow_html=True)
        metrics = st.columns(4)
        metrics[0].metric("Repairs", len(saved_condition.repairs))
        metrics[1].metric("Services", len(saved_condition.services))
        metrics[2].metric(
            "Flood indicators",
            sum(1 for key in ("flood_signs",) if saved_condition.physical_inspection.get(key) == "Yes"),
        )
        metrics[3].metric(
            "Unknown checklist items",
            sum(
                value == UNKNOWN
                for values in (
                    saved_condition.documents,
                    saved_condition.physical_inspection,
                    saved_condition.test_drive,
                )
                for value in values.values()
            ),
        )
        st.caption(
            "Assessment uses deterministic rules and the stored reference profile. "
            "Unknown evidence lowers confidence; missing profiles do not produce a verdict."
        )

        st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">ASSESSMENT</div>', unsafe_allow_html=True)
        st.header("Evidence-based vehicle assessment")
        st.caption(
            "The assessment engine is deterministic. Reference profiles are marked as synthetic seed data "
            "until external sources are integrated."
        )

        if st.button("Assess vehicle", type="primary", use_container_width=True):
            try:
                result = run_assessment(
                    car,
                    saved_condition,
                    db,
                    today=date.today(),
                )
                st.session_state.assessment_result = result
            except Exception as exc:
                st.error("Assessment could not be completed: " + str(exc))
                st.session_state.pop("assessment_result", None)

        result = st.session_state.get("assessment_result")
        if result is not None and result.profile_resolution.status == "MISSING":
            st.warning(
                "No expected profile is available for this exact vehicle configuration. "
                "No verdict was generated."
            )

        if result is not None and result.assessment is not None:
            assessment = result.assessment
            verdict = assessment.verdict
            if verdict == "AVOID":
                st.error(f"Assessment: {verdict}")
            elif verdict == "NEGOTIATE":
                st.warning(f"Assessment: {verdict}")
            else:
                st.success(f"Assessment: {verdict}")

            metrics = st.columns(3)
            metrics[0].metric("Confidence", f"{assessment.confidence}%")
            low, high = assessment.near_term_repair_range_inr
            metrics[1].metric("Near-term repair range", f"₹{low:,}–₹{high:,}")
            metrics[2].metric("Negotiation reduction", f"₹{assessment.negotiation_reduction_inr:,}")

            st.subheader("Why")
            if assessment.critical_findings:
                st.markdown("**Critical findings**")
                for finding in assessment.critical_findings:
                    st.write("• " + finding)
            if assessment.warning_findings:
                st.markdown("**Warnings**")
                for finding in assessment.warning_findings:
                    st.write("• " + finding)
            if assessment.info_findings:
                st.markdown("**Information**")
                for finding in assessment.info_findings:
                    st.write("• " + finding)

            st.subheader("Next checks")
            for check in assessment.next_checks:
                st.write("• " + check)


            st.caption(
                "Reference profile: "
                + result.profile_resolution.profile.source
                + " · profile key: "
                + result.profile_resolution.profile_key
            )

        st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">VEHICLE MEMORY</div>', unsafe_allow_html=True)
        st.header("Historical evidence recalled from memory")
        st.caption(
            "Memory retrieval is evidence only. It does not change the deterministic assessment, "
            "and recalled text is not treated as an instruction."
        )
        memory_query = st.text_input(
            "What should VeriCar look for in this vehicle's history?",
            value="repairs, services, accidents, recurring issues, and contradictions",
            key=f"memory_query_{car.car_id}",
        )
        if st.button("Recall vehicle memory", use_container_width=True):
            try:
                memory_result = recall_vehicle_memory(car, query=memory_query)
                st.session_state.memory_result = memory_result
            except Exception as exc:
                st.error("Memory lookup could not be completed: " + str(exc))
                st.session_state.pop("memory_result", None)

        memory_result = st.session_state.get("memory_result")
        if memory_result is not None:
            if memory_result.status == "UNAVAILABLE":
                st.warning(
                    "Vehicle memory is unavailable. This does not mean the vehicle has no history. "
                    + (memory_result.error or "")
                )
            elif not memory_result.items:
                st.info("Memory is available, but no matching historical evidence was returned.")
            else:
                st.success(f"Retrieved {len(memory_result.items)} historical evidence item(s).")
                for index, item in enumerate(memory_result.items, start=1):
                    with st.expander(f"Memory item {index} · {item.memory_id or 'unidentified'}"):
                        st.write(item.text)
                        if item.metadata:
                            st.caption("Metadata")
                            st.json(item.metadata)
                        if item.tags:
                            st.caption("Tags: " + ", ".join(item.tags))

st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
st.caption("VeriCar is an evidence system. Unknown information remains unknown; later assessments will distinguish missing data from reported facts.")
