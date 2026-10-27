import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta

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

def get_coordinates(location_name):
    """Mencari koordinat (lat, lon) dari nama lokasi menggunakan Nominatim OSMR API"""
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={location_name}&limit=1"
    headers = {"User-Agent": "LogisticsRouteApp/1.0"}
    res = requests.get(url, headers=headers).json()
    if res:
        return float(res[0]["lat"]), float(res[0]["lon"]), res[0]["display_name"]
    return None, None, None

def get_osrm_route(origin_coords, dest_coords):
    """Menghitung rute, jarak, dan durasi pakai OSRM API"""
    lon1, lat1 = origin_coords[1], origin_coords[0]
    lon2, lat2 = dest_coords[1], dest_coords[0]
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    res = requests.get(url).json()
    if res.get("routes"):
        route = res["routes"][0]
        distance_km = route["distance"] / 1000.0  # Meter ke KM
        duration_min = route["duration"] / 60.0    # Detik ke Menit
        geometry = route["geometry"]
        return distance_km, duration_min, geometry
    return 0, 0, None

st.title("🚚 Route & Cost Optimizer Logistic")

# Section 1: Input Rute & Armada
col1, col2 = st.columns(2)
with col1:
    origin_input = st.text_input("Lokasi Asal (Origin)", value="Surabaya")
    dest_input = st.text_input("Lokasi Tujuan (Destination)", value="Malang")
    armada = st.selectbox("Pilih Jenis Armada", list(RASIO_BBM.keys()))

with col2:
    biaya_supir = st.number_input("Biaya Supir per Hari (Rp)", value=200000, step=25000)
    jam_berangkat = st.time_input("Waktu Keberangkatan", value=datetime.now().time())
    biaya_tol = st.number_input(f"Estimasi Tarif Tol ({GOLONGAN_TOL[armada]}) (Rp)", value=50000)
    pilih_tol = st.radio("Opsi Rute", ["Via Tol", "Non-Tol"])

# Process Routing & Cost
if st.button("Hitung Rute & Biaya"):
    lat1, lon1, name1 = get_coordinates(origin_input)
    lat2, lon2, name2 = get_coordinates(dest_input)
    
    if lat1 and lat2:
        dist_km, dur_min, geom = get_osrm_route((lat1, lon1), (lat2, lon2))
        
        # Hitung Biaya
        rasio = RASIO_BBM[armada]
        kebutuhan_bbm = dist_km / rasio
        biaya_bbm = kebutuhan_bbm * HARGA_SOLAR
        tol_final = biaya_tol if pilih_tol == "Via Tol" else 0
        total_biaya = biaya_bbm + tol_final + biaya_supir
        
        # Hitung SLA / ETA Waktu
        now = datetime.now()
        dt_berangkat = datetime.combine(now.date(), jam_berangkat)
        dt_tiba = dt_berangkat + timedelta(minutes=dur_min)
        
        st.subheader("📊 Hasil Optimasi Rute & Biaya")
        st.write(f"**Jarak Tempuh:** {dist_km:.2f} km")
        st.write(f"**Estimasi Waktu Tempuh:** {int(dur_min // 60)} Jam {int(dur_min % 60)} Menit")
        st.write(f"**Estimasi Waktu Tiba (ETA):** {dt_tiba.strftime('%H:%M WIB')}")
        st.write(f"**Golongan Tol:** {GOLONGAN_TOL[armada]}")
        st.write(f"**Konsumsi BBM:** {kebutuhan_bbm:.2f} Liter (Rp {biaya_bbm:,.0f})")
        st.write(f"**Total Biaya Operasional:** Rp {total_biaya:,.0f}")
        
        # Tampilkan Peta Leaflet
        m = folium.Map(location=[(lat1 + lat2)/2, (lon1 + lon2)/2], zoom_start=9)
        folium.Marker([lat1, lon1], popup=f"Origin: {name1}", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker([lat2, lon2], popup=f"Destination: {name2}", icon=folium.Icon(color="red")).add_to(m)
        
        if geom:
            coords = [[pt[1], pt[0]] for pt in geom["coordinates"]]
            folium.PolyLine(coords, color="blue", weight=5, opacity=0.8).add_to(m)
            
        st_folium(m, width=350, height=300)
    else:
        st.error("Lokasi tidak ditemukan. Coba ketik lokasi yang lebih spesifik (misal: 'Surabaya, Jawa Timur').")
