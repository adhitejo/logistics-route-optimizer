import streamlit as st

# Data Rasio BBM (km/liter)
RASIO_BBM = {
    "Blindvan": 12.0, "Granmax Box": 11.0,
    "CDE": 7.5, "CDE L": 7.25, "CDE Pendingin": 6.5, "CDE L Pendingin": 6.25,
    "CDD": 7.0, "CDD L": 6.5, "CDD Pendingin": 6.0, "CDD L Pendingin": 5.5,
    "Fuso": 4.0, "Tronton Wingbox": 3.0
}

# Pemetaan Golongan Tol
GOLONGAN_TOL = {
    "Blindvan": "Golongan I", "Granmax Box": "Golongan I",
    "CDE": "Golongan I", "CDE L": "Golongan I", "CDE Pendingin": "Golongan I", "CDE L Pendingin": "Golongan I",
    "CDD": "Golongan II", "CDD L": "Golongan II", "CDD Pendingin": "Golongan II", "CDD L Pendingin": "Golongan II",
    "Fuso": "Golongan III", "Tronton Wingbox": "Golongan III"
}

HARGA_SOLAR = 6800

st.title("🚚 Route & Cost Optimizer Logistik")

# Input Parameter
col1, col2 = st.columns(2)
with col1:
    armada = st.selectbox("Pilih Jenis Armada", list(RASIO_BBM.keys()))
    biaya_supir = st.number_input("Biaya Supir per Hari (Rp)", value=200000, step=25000)
    jam_berangkat = st.time_input("Waktu Keberangkatan")

with col2:
    jarak_km = st.number_input("Estimasi Jarak (km)", value=150.0)
    biaya_tol = st.number_input(f"Estimasi Tarif Tol ({GOLONGAN_TOL[armada]}) (Rp)", value=120000)
    pilih_tol = st.radio("Opsi Rute", ["Via Tol", "Non-Tol"])

# Kalkulasi
rasio = RASIO_BBM[armada]
kebutuhan_bbm = jarak_km / rasio
biaya_bbm = kebutuhan_bbm * HARGA_SOLAR
tol_final = biaya_tol if pilih_tol == "Via Tol" else 0
total_biaya = biaya_bbm + tol_final + biaya_supir

# Output
st.subheader("📊 Hasil Optimasi & Estimasi Biaya")
st.write(f"**Golongan Tol:** {GOLONGAN_TOL[armada]}")
st.write(f"**Konsumsi BBM:** {kebutuhan_bbm:.2f} Liter (Rp {biaya_bbm:,.0f})")
st.write(f"**Total Biaya Operasional:** Rp {total_biaya:,.0f}")
