from __future__ import annotations

from datetime import date

import streamlit as st

from core.database import Database
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
    st.info("Next stage: repairs, services, inspection evidence, documents, and seller claims will be attached to this vehicle record.")

st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
st.caption("VeriCar is an evidence system. Unknown information remains unknown; later assessments will distinguish missing data from reported facts.")
