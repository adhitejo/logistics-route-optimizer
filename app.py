import streamlit as st
import requests
import folium
import math
from streamlit_folium import st_folium
from datetime import datetime, timedelta

# Config Halaman
st.set_page_config(page_title="Logistic - Route & Cost Optimizer", layout="wide")

# Master Data Indonesia
RASIO_BBM_ID = {
    "Blindvan": 12.0, "Granmax Box": 11.0,
    "CDE": 7.5, "CDE L": 7.25, "CDE Pendingin": 6.5, "CDE L Pendingin": 6.25,
    "CDD": 7.0, "CDD L": 6.5, "CDD Pendingin": 6.0, "CDD L Pendingin": 5.5,
    "Fuso": 4.0, "Tronton Wingbox": 3.0
}

HARGA_SOLAR_IDR = 6800

def get_coordinates(location_name):
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={location_name}&limit=1"
    headers = {"User-Agent": "LogisticApp/1.0"}
    try:
        res = requests.get(url, headers=headers).json()
        if res:
            return float(res[0]["lat"]), float(res[0]["lon"]), res[0]["display_name"]
    except Exception:
        pass
    return None, None, None

def haversine_distance(coord1, coord2):
    """Menhitung jarak garis lurus (Haversine) antara dua koordinat lat/lon"""
    R = 6371.0 # Radius bumi (km)
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def solve_nearest_neighbor(coords_list):
    """Algoritma Nearest Neighbor untuk mengurutkan destinasi paling logis dari Origin"""
    unvisited = list(range(1, len(coords_list)))
    current_idx = 0
    route_order = [0]
    
    while unvisited:
        nearest_idx = min(unvisited, key=lambda i: haversine_distance(coords_list[current_idx], coords_list[i]))
        route_order.append(nearest_idx)
        unvisited.remove(nearest_idx)
        current_idx = nearest_idx
        
    return route_order

def get_osrm_sequential_route(ordered_coords):
    """Menghitung rute sekuensial berdasarkan urutan teroptimasi"""
    coord_str = ";".join([f"{lon},{lat}" for lat, lon in ordered_coords])
    url = f"http://router.project-osrm.org/route/v1/driving/{coord_str}?overview=full&geometries=geojson"
    try:
        res = requests.get(url).json()
        if res.get("routes"):
            route = res["routes"][0]
            distance_km = route["distance"] / 1000.0
            duration_min = route["duration"] / 60.0
            geometry = route["geometry"]
            return distance_km, duration_min, geometry
    except Exception:
        pass
    return 0, 0, None

# Session state initialization
if "calculation_result" not in st.session_state:
    st.session_state.calculation_result = None

st.title("🚛 Logistic")

tab1, tab2, tab3 = st.tabs(["Route & Cost Optimizer", "Order Management System (OMS)", "Transport Management System (TMS)"])

with tab1:
    st.subheader("Route & Cost Optimization")
    
    region = st.radio("Operating Region", ["Indonesia", "Outside Indonesia"], horizontal=True)
    currency = "IDR" if region == "Indonesia" else "USD"
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📍 Location & Drops")
        origin_input = st.text_input("Origin (Start Point)", value="Surabaya")
        
        num_dest = st.number_input("Number of Destination Points (Max 3 for Free Plan)", min_value=1, max_value=5, value=3)
        
        if num_dest > 3:
            st.warning("⚠️ Free plan limits up to 3 destinations. Upgrade to Pro for unlimited multi-drop routing!")
            num_dest = 3
            
        destinations = []
        default_dests = ["Karawang", "Bandung", "Sukabumi"]
        for i in range(int(num_dest)):
            default_val = default_dests[i] if i < len(default_dests) else f"Destination {i+1}"
            dest = st.text_input(f"Destination Point {i+1}", value=default_val)
            destinations.append(dest)
            
    with col2:
        st.markdown("### 🚚 Vehicle & Cost Configuration")
        
        if region == "Indonesia":
            vehicle_type = st.selectbox("Vehicle Type", list(RASIO_BBM_ID.keys()))
            fuel_ratio = RASIO_BBM_ID[vehicle_type]
            fuel_price = HARGA_SOLAR_IDR
            st.caption(f"Default Fuel Ratio: {fuel_ratio} km/L | Price: Rp {fuel_price}/L")
        else:
            vehicle_type = st.text_input("Custom Vehicle Type", value="Heavy Duty Truck")
            fuel_price = st.number_input("Fuel Price (per Liter / Gallon)", value=3.50, step=0.1)
            fuel_ratio = st.number_input("Fuel Efficiency Ratio (Distance per Unit Fuel)", value=6.0, step=0.5)
            
        driver_cost = st.number_input(f"Driver Daily Allowance ({currency})", value=200000 if region == "Indonesia" else 150, step=10)
        departure_time = st.time_input("Departure Time", value=datetime.now().time())
        
        # Opsi Toll & Fee Input
        route_option = st.radio("Route Option", ["Via Toll", "Non-Toll"], horizontal=True)
        toll_cost_input = st.number_input(f"Toll Fee Estimation ({currency})", value=150000 if region == "Indonesia" else 20, step=5)
        toll_cost = toll_cost_input if route_option == "Via Toll" else 0

    if st.button("Calculate & Optimize Route", type="primary"):
        all_locations = [origin_input] + destinations
        coords_list = []
        names_list = []
        valid = True
        
        for loc in all_locations:
            lat, lon, name = get_coordinates(loc)
            if lat and lon:
                coords_list.append((lat, lon))
                names_list.append(name)
            else:
                st.error(f"Could not locate address: '{loc}'. Please try a more specific address.")
                valid = False
                break
                
        if valid and len(coords_list) >= 2:
            # Hitung urutan terdekat yang efisien
            order_indices = solve_nearest_neighbor(coords_list)
            
            ordered_coords = [coords_list[i] for i in order_indices]
            ordered_names = [names_list[i] for i in order_indices]
            
            # Hitung jarak rute berurutan
            dist_km, dur_min, geom = get_osrm_sequential_route(ordered_coords)
            
            fuel_needed = dist_km / fuel_ratio if fuel_ratio > 0 else 0
            fuel_cost_total = fuel_needed * fuel_price
            total_cost = fuel_cost_total + toll_cost + driver_cost
            
            now = datetime.now()
            dt_dep = datetime.combine(now.date(), departure_time)
            dt_arr = dt_dep + timedelta(minutes=dur_min)
            
            st.session_state.calculation_result = {
                "ordered_coords": ordered_coords,
                "ordered_names": ordered_names,
                "dist_km": dist_km,
                "dur_min": dur_min,
                "geom": geom,
                "vehicle_type": vehicle_type,
                "fuel_needed": fuel_needed,
                "fuel_cost_total": fuel_cost_total,
                "route_option": route_option,
                "toll_cost": toll_cost,
                "driver_cost": driver_cost,
                "total_cost": total_cost,
                "eta": dt_arr.strftime('%I:%M %p'),
                "currency": currency
            }

    # Display Results
    if st.session_state.calculation_result is not None:
        res = st.session_state.calculation_result
        st.markdown("---")
        
        c_head, c_close = st.columns([5, 1])
        with c_head:
            st.subheader("📊 Optimization & Cost Breakdown")
        with c_close:
            if st.button("Close"):
                st.session_state.calculation_result = None
                st.rerun()

        if st.session_state.calculation_result is not None:
            curr = res["currency"]
            
            # Tampilkan Urutan Rute Hasil Optimasi
            st.success("✅ **Optimized Visiting Sequence:** " + " ➔ ".join([f"{idx+1}. {name.split(',')[0]}" for idx, name in enumerate(res["ordered_names"])]))
            
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.write(f"**Total Distance:** {res['dist_km']:.2f} km")
                st.write(f"**Estimated Travel Time:** {int(res['dur_min'] // 60)} hrs {int(res['dur_min'] % 60)} mins")
                st.write(f"**Estimated Arrival Time (ETA):** {res['eta']}")
                st.write(f"**Vehicle Type:** {res['vehicle_type']}")
                st.write(f"**Selected Route:** {res['route_option']}")
                
            with col_res2:
                st.write(f"**Estimated Fuel Usage:** {res['fuel_needed']:.2f} Units ({curr} {res['fuel_cost_total']:,.2f})")
                st.write(f"**Toll Fee ({res['route_option']}):** {curr} {res['toll_cost']:,.2f}")
                st.write(f"**Driver Allowance:** {curr} {res['driver_cost']:,.2f}")
                st.markdown(f"### **Total Operational Cost: {curr} {res['total_cost']:,.2f}**")
            
            # Map Rendering
            avg_lat = sum(p[0] for p in res["ordered_coords"]) / len(res["ordered_coords"])
            avg_lon = sum(p[1] for p in res["ordered_coords"]) / len(res["ordered_coords"])
            
            m = folium.Map(location=[avg_lat, avg_lon], zoom_start=7)
            
            # Menampilkan Marker Berurut Nomor (1, 2, 3...)
            for idx, (coord, name) in enumerate(zip(res["ordered_coords"], res["ordered_names"]), start=1):
                color = "green" if idx == 1 else "red"
                label_type = "Origin" if idx == 1 else f"Stop {idx-1}"
                
                folium.Marker(
                    coord, 
                    popup=f"<b>#{idx} {label_type}</b><br>{name}",
                    tooltip=f"#{idx} - {label_type}",
                    icon=folium.Icon(color=color, icon="info-sign")
                ).add_to(m)
                
            if res["geom"]:
                polyline_coords = [[pt[1], pt[0]] for pt in res["geom"]["coordinates"]]
                folium.PolyLine(polyline_coords, color="blue", weight=5, opacity=0.8).add_to(m)
                
            st_folium(m, width=700, height=400, key="numbered_multi_drop_map")

with tab2:
    st.subheader("📦 Order Management System (OMS)")
    st.info("Feature Coming Soon: Manage incoming delivery orders, SKU tracking, and customer dispatch requests.")

with tab3:
    st.subheader("🚛 Transport Management System (TMS)")
    st.info("Feature Coming Soon: Live fleet tracking, driver assignments, maintenance schedules, and POD management.")
    
