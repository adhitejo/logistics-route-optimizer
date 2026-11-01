import streamlit as st
import requests
import folium
import math
import pandas as pd
from datetime import datetime, timedelta
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection

# ------------------------------------------
# CONFIG & DATABASE CONNECTION
# ------------------------------------------
st.set_page_config(page_title="Logistic Enterprise System", layout="wide")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Helper function to safely read Google Sheets
def load_data(sheet_url):
    try:
        return conn.read(spreadsheet=sheet_url, ttl=0)
    except Exception:
        return pd.DataFrame()

# URLs Google Sheets Database
URL_VEHICLES = "https://docs.google.com/spreadsheets/d/12DUIfV9cD-qh507CdWQAlN62wnF5jVvn5eD5-9kJcek/edit"
URL_DRIVERS = "https://docs.google.com/spreadsheets/d/1aD4TnY5FBZ5zJ3GmZ7QMw8vGCkc3GNyeeNKXNobkr48/edit"
URL_ORDERS = "https://docs.google.com/spreadsheets/d/18vRdScdK_b5TEfSBxgyDu0LlwsKZN22GG5af8QMhB_M/edit"
URL_SETTLEMENTS = "https://docs.google.com/spreadsheets/d/1aWtn2ehrQ99eKqeHof2tVQkxAPj00JuSqUZRTaoBFac/edit"

# Load Initial Dataframe
df_vehicles = load_data(URL_VEHICLES)
df_drivers = load_data(URL_DRIVERS)
df_orders = load_data(URL_ORDERS)
df_settlements = load_data(URL_SETTLEMENTS)

# Master Fuel Ratio & Pricing
RASIO_BBM_ID = {
    "Blindvan": 12.0, "Granmax Box": 11.0,
    "CDE": 7.5, "CDE L": 7.25, "CDE Pendingin": 6.5, "CDE L Pendingin": 6.25,
    "CDD": 7.0, "CDD L": 6.5, "CDD Pendingin": 6.0, "CDD L Pendingin": 5.5,
    "Fuso": 4.0, "Tronton Wingbox": 3.0
}
HARGA_SOLAR_IDR = 6800

# Helper Functions (Geocoding & Route Engine)
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
    R = 6371.0
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def solve_nearest_neighbor(coords_list):
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
    coord_str = ";".join([f"{lon},{lat}" for lat, lon in ordered_coords])
    url = f"http://router.project-osrm.org/route/v1/driving/{coord_str}?overview=full&geometries=geojson"
    try:
        res = requests.get(url).json()
        if res.get("routes"):
            route = res["routes"][0]
            return route["distance"] / 1000.0, route["duration"] / 60.0, route["geometry"]
    except Exception:
        pass
    return 0, 0, None

# ------------------------------------------
# MAIN INTERFACE & TABS
# ------------------------------------------
st.title("🚛 Logistic Enterprise Control Tower")

tab1, tab2, tab3, tab4 = st.tabs([
    "Route & Cost Optimizer", 
    "Order Management System (OMS)", 
    "Transport Management System (TMS)", 
    "Master Data Management"
])

# ------------------------------------------
# TAB 1: ROUTE & COST OPTIMIZER
# ------------------------------------------
with tab1:
    st.subheader("Route & Cost Optimization")
    region = st.radio("Operating Region", ["Indonesia", "Outside Indonesia"], horizontal=True)
    currency = "IDR" if region == "Indonesia" else "USD"
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📍 Location & Drops")
        origin_input = st.text_input("Origin (Start Point)", value="Surabaya")
        num_dest = st.number_input("Number of Destination Points", min_value=1, max_value=3, value=2)
        
        destinations = []
        default_dests = ["Karawang", "Bandung", "Sukabumi"]
        for i in range(int(num_dest)):
            default_val = default_dests[i] if i < len(default_dests) else f"Destination {i+1}"
            destinations.append(st.text_input(f"Destination Point {i+1}", value=default_val))
            
    with col2:
        st.markdown("### 🚚 Vehicle & Cost Configuration")
        vehicle_type = st.selectbox("Vehicle Type", list(RASIO_BBM_ID.keys()))
        fuel_ratio = RASIO_BBM_ID[vehicle_type]
        fuel_price = HARGA_SOLAR_IDR
        
        driver_cost_per_day = st.number_input(f"Driver Allowance per Day ({currency})", value=200000, step=10000)
        departure_time = st.time_input("Departure Time", value=datetime.now().time())
        route_option = st.radio("Route Option", ["Via Toll", "Non-Toll"], horizontal=True)
        toll_cost_input = st.number_input(f"Toll Fee Estimation ({currency})", value=150000, step=5000)
        toll_cost = toll_cost_input if route_option == "Via Toll" else 0

    if st.button("Calculate & Optimize Route", type="primary"):
        all_locations = [origin_input] + destinations
        coords_list, names_list, valid = [], [], True
        
        for loc in all_locations:
            lat, lon, name = get_coordinates(loc)
            if lat and lon:
                coords_list.append((lat, lon))
                names_list.append(name)
            else:
                st.error(f"Could not locate address: '{loc}'.")
                valid = False
                break
                
        if valid and len(coords_list) >= 2:
            order_indices = solve_nearest_neighbor(coords_list)
            ordered_coords = [coords_list[i] for i in order_indices]
            ordered_names = [names_list[i] for i in order_indices]
            dist_km, dur_min, geom = get_osrm_sequential_route(ordered_coords)
            
            days_needed = math.ceil(dur_min / (12 * 60)) if dur_min > 0 else 1
            total_driver_cost = days_needed * driver_cost_per_day
            fuel_needed = dist_km / fuel_ratio
            fuel_cost_total = fuel_needed * fuel_price
            total_cost = fuel_cost_total + toll_cost + total_driver_cost
            
            st.session_state.current_calc = {
                "route_name": f"{origin_input} ➔ { ' ➔ '.join(destinations) }",
                "ordered_names": ordered_names,
                "ordered_coords": ordered_coords,
                "dist_km": dist_km,
                "dur_min": dur_min,
                "geom": geom,
                "vehicle_type": vehicle_type,
                "fuel_needed": fuel_needed,
                "fuel_cost": fuel_cost_total,
                "route_option": route_option,
                "toll_cost": toll_cost,
                "driver_cost": total_driver_cost,
                "days_needed": days_needed,
                "total_cost": total_cost,
                "currency": currency
            }

    if "current_calc" in st.session_state:
        calc = st.session_state.current_calc
        st.markdown("---")
        st.success(f"✅ **Optimized Route:** {' ➔ '.join([name.split(',')[0] for name in calc['ordered_names']])}")
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.write(f"**Total Distance:** {calc['dist_km']:.2f} km")
            st.write(f"**Travel Time:** {int(calc['dur_min'] // 60)} hrs {int(calc['dur_min'] % 60)} mins")
            st.write(f"**Vehicle Type:** {calc['vehicle_type']}")
            st.write(f"**Selected Route:** {calc['route_option']}")
        with col_r2:
            st.write(f"**Fuel Cost:** Rp {calc['fuel_cost']:,.0f}")
            st.write(f"**Toll Fee:** Rp {calc['toll_cost']:,.0f}")
            st.write(f"**Driver Allowance ({calc['days_needed']} Day):** Rp {calc['driver_cost']:,.0f}")
            st.markdown(f"### **Total Cost: Rp {calc['total_cost']:,.0f}**")
            
        # Map Rendering
        avg_lat = sum(p[0] for p in calc["ordered_coords"]) / len(calc["ordered_coords"])
        avg_lon = sum(p[1] for p in calc["ordered_coords"]) / len(calc["ordered_coords"])
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=7)
        for idx, (coord, name) in enumerate(zip(calc["ordered_coords"], calc["ordered_names"]), start=1):
            color = "green" if idx == 1 else "red"
            folium.Marker(coord, popup=f"#{idx} {name}", icon=folium.Icon(color=color)).add_to(m)
        if calc["geom"]:
            folium.PolyLine([[pt[1], pt[0]] for pt in calc["geom"]["coordinates"]], color="blue", weight=5).add_to(m)
        st_folium(m, width=700, height=350, key="opt_map")

        if st.button("💾 Save Route to OMS Draft"):
            new_order = pd.DataFrame([{
                "Order_ID": f"ORD-{datetime.now().strftime('%m%d%H%M')}",
                "Route_Name": calc["route_name"],
                "Customer_Name": "TBD",
                "Cargo_Weight_Kg": 0,
                "Vehicle_Type": calc["vehicle_type"],
                "Assigned_Driver": "Unassigned",
                "Assigned_Nopol": "Unassigned",
                "Cash_Advance": calc["total_cost"],
                "Status": "DRAFT",
                "Created_At": datetime.now().strftime('%Y-%m-%d %H:%M')
            }])
            updated_orders = pd.concat([df_orders, new_order], ignore_index=True)
            conn.update(spreadsheet=URL_ORDERS, data=updated_orders)
            st.success("Route saved to Google Sheets OMS! Go to 'Order Management System' tab.")

# ------------------------------------------
# TAB 2: ORDER MANAGEMENT SYSTEM (OMS)
# ------------------------------------------
with tab2:
    st.subheader("📦 Order Management System (OMS)")
    st.write("Manage orders & dispatch assignments to drivers")
    
    st.markdown("### 📋 Active Orders Database")
    st.dataframe(df_orders, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 🚀 Dispatch Assignment")
    
    draft_orders = df_orders[df_orders["Status"] == "DRAFT"] if not df_orders.empty else pd.DataFrame()
    
    if draft_orders.empty:
        st.info("No DRAFT orders available. Create a route in Tab 1 first.")
    else:
        selected_ord_id = st.selectbox("Select Order Draft", draft_orders["Order_ID"].tolist())
        selected_row = draft_orders[draft_orders["Order_ID"] == selected_ord_id].iloc[0]
        
        c_oms1, c_oms2 = st.columns(2)
        with c_oms1:
            cust_input = st.text_input("Customer Name", value="PT. Fast Logistics")
            cargo_input = st.number_input("Cargo Weight (Kg)", value=2000)
            
        with c_oms2:
            avail_veh = df_vehicles[(df_vehicles["Type"] == selected_row["Vehicle_Type"]) & (df_vehicles["Status"] == "Available")]["Nopol"].tolist() if not df_vehicles.empty else []
            avail_drv = df_drivers[df_drivers["Status"] == "Available"]["Name"].tolist() if not df_drivers.empty else []
            
            nopol_select = st.selectbox(f"Select Vehicle ({selected_row['Vehicle_Type']})", avail_veh if avail_veh else ["No Vehicle Available"])
            drv_select = st.selectbox("Select Driver", avail_drv if avail_drv else ["No Driver Available"])
            cash_adv_input = st.number_input("Total Cash Advance / Uang Jalan (Rp)", value=float(selected_row["Cash_Advance"]))

        if st.button("🚀 Dispatch Order & Notify Driver", type="primary"):
            if nopol_select != "No Vehicle Available" and drv_select != "No Driver Available":
                df_orders.loc[df_orders["Order_ID"] == selected_ord_id, ["Customer_Name", "Cargo_Weight_Kg", "Assigned_Driver", "Assigned_Nopol", "Cash_Advance", "Status"]] = [
                    cust_input, cargo_input, drv_select, nopol_select, cash_adv_input, "DISPATCHED"
                ]
                conn.update(spreadsheet=URL_ORDERS, data=df_orders)
                
                drv_phone = df_drivers[df_drivers["Name"] == drv_select]["Phone"].iloc[0] if not df_drivers.empty else ""
                wa_msg = f"Halo {drv_select}, tugas pengiriman baru {selected_ord_id} untuk {cust_input}.\nUnit: {nopol_select}\nRute: {selected_row['Route_Name']}\nUang Jalan: Rp {cash_adv_input:,.0f}"
                wa_link = f"https://wa.me/{drv_phone}?text={requests.utils.quote(wa_msg)}"
                
                st.success(f"Order {selected_ord_id} Dispatched!")
                st.markdown(f"📱 **[Click Here to Send WhatsApp Task to Driver]({wa_link})**")
            else:
                st.error("Select valid Driver and Vehicle before dispatching!")

# ------------------------------------------
# TAB 3: TRANSPORT MANAGEMENT SYSTEM (TMS)
# ------------------------------------------
with tab3:
    st.subheader("🚛 Transport Management System (TMS) & Control Tower")
    
    st.markdown("### 📊 Fleet Status Monitoring")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    tot_veh = len(df_vehicles) if not df_vehicles.empty else 0
    in_transit = len(df_vehicles[df_vehicles["Status"] == "In-Transit"]) if not df_vehicles.empty else 0
    in_maint = len(df_vehicles[df_vehicles["Status"] == "Maintenance"]) if not df_vehicles.empty else 0
    idle_veh = len(df_vehicles[df_vehicles["Status"] == "Available"]) if not df_vehicles.empty else 0
    
    kpi1.metric("Total Fleet", tot_veh)
    kpi2.metric("In-Transit / Delivering", in_transit)
    kpi3.metric("Idle / Ready at Pool", idle_veh)
    kpi4.metric("Maintenance", in_maint)
    
    st.markdown("---")
    st.markdown("### 🛣️ Trip Settlement & POD Return")
    
    dispatched_orders = df_orders[df_orders["Status"] == "DISPATCHED"] if not df_orders.empty else pd.DataFrame()
    
    if dispatched_orders.empty:
        st.info("No active trips in transit.")
    else:
        for idx, row in dispatched_orders.iterrows():
            with st.expander(f"🔴 Order {row['Order_ID']} - {row['Customer_Name']} ({row['Assigned_Nopol']})"):
                st.write(f"**Route:** {row['Route_Name']} | **Driver:** {row['Assigned_Driver']}")
                st.write(f"**Uang Jalan Initial:** Rp {row['Cash_Advance']:,.0f}")
                
                c_s1, c_s2 = st.columns(2)
                with c_s1:
                    act_spent = st.number_input("Actual Trip Expense (BBM + Tol + Parkir) (Rp)", value=float(row["Cash_Advance"]), key=f"spent_{row['Order_ID']}")
                    pod_status = st.selectbox("Proof of Delivery (POD) Status", ["Signed & Complete", "Partial Delivery", "Damaged/Rejected"], key=f"pod_{row['Order_ID']}")
                with c_s2:
                    balance = row["Cash_Advance"] - act_spent
                    if balance >= 0:
                        st.info(f"💰 Driver Refunds to Office: Rp {balance:,.0f}")
                    else:
                        st.warning(f"⚠️ Office Reimburse to Driver: Rp {abs(balance):,.0f}")
                        
                if st.button(f"✅ Complete & Settle {row['Order_ID']}", key=f"btn_{row['Order_ID']}"):
                    new_settle = pd.DataFrame([{
                        "Order_ID": row['Order_ID'],
                        "Customer_Name": row['Customer_Name'],
                        "Driver_Name": row['Assigned_Driver'],
                        "Nopol": row['Assigned_Nopol'],
                        "Cash_Advance": row['Cash_Advance'],
                        "Actual_Spent": act_spent,
                        "Balance": balance,
                        "POD_Status": pod_status,
                        "Settled_At": datetime.now().strftime('%Y-%m-%d %H:%M')
                    }])
                    updated_settlements = pd.concat([df_settlements, new_settle], ignore_index=True)
                    conn.update(spreadsheet=URL_SETTLEMENTS, data=updated_settlements)
                    
                    df_orders.loc[df_orders["Order_ID"] == row['Order_ID'], "Status"] = "COMPLETED"
                    conn.update(spreadsheet=URL_ORDERS, data=df_orders)
                    
                    st.success(f"Trip {row['Order_ID']} Settled and Saved!")
                    st.rerun()

    if not df_settlements.empty:
        st.markdown("---")
        st.markdown("### 📑 Settled Trip History")
        st.dataframe(df_settlements, use_container_width=True)

# ------------------------------------------
# TAB 4: MASTER DATA MANAGEMENT
# ------------------------------------------
with tab4:
    st.subheader("⚙️ Master Data Management")
    m_tab1, m_tab2 = st.tabs(["Master Vehicles", "Master Drivers"])
    
    with m_tab1:
        st.markdown("### 🚚 Master Vehicles List")
        st.dataframe(df_vehicles, use_container_width=True)
        
    with m_tab2:
        st.markdown("### 👨‍✈️ Master Drivers List")
        st.dataframe(df_drivers, use_container_width=True)
