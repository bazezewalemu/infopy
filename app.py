import streamlit as st
import pandas as pd
import os
import requests
import json
import plotly.express as px
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import time
import base64
from io import BytesIO

# --- 1. SETTINGS & SECURITY CONFIG ---
DB_FILE = "technical_inspection_data.xlsx"
RECYCLE_FILE = "recycle_bin_data.xlsx"
USER_FILE = "system_users.xlsx"
GSHEET_URL = "https://script.google.com/macros/s/AKfycbyfDC0kS8eVSZ2sMvoL-PxBVLQNToEBpn3LckqDIPQ8HddezDdd86eZenHXPbJFpUk3/exec"

st.set_page_config(page_title="Technical Inspection ERP Pro", layout="wide", initial_sidebar_state="expanded")

# Persistence Logic
if 'auth' not in st.session_state: st.session_state.auth = False
if 'user_data' not in st.session_state: st.session_state.user_data = None
if 'lang' not in st.session_state: st.session_state.lang = "አማርኛ"

# --- 2. ADVANCED THEME & UI ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), 
        url('https://images.unsplash.com/photo-1504384308090-c894fdcc538d?q=80&w=2000');
        background-size: cover; background-attachment: fixed; color: #e0e0e0;
    }
    .main-header { font-size: 2.5rem; color: #00d4ff; text-align: center; font-weight: bold; text-shadow: 2px 2px 4px #000; }
    div.stButton > button { width: 100%; border-radius: 20px; height: 3em; background: linear-gradient(45deg, #007bff, #00d4ff); color: white; border: none; transition: 0.3s; }
    div.stButton > button:hover { transform: scale(1.05); box-shadow: 0 10px 20px rgba(0,212,255,0.4); }
    .status-card { background: rgba(255, 255, 255, 0.05); padding: 25px; border-radius: 15px; border: 1px solid rgba(0,212,255,0.2); text-align: center; }
    .receipt-box { border: 2px solid #00d4ff; padding: 30px; background: white; color: black; font-family: 'Arial'; border-radius: 10px; }
    .footer { position: fixed; bottom: 10; width: 100%; text-align: center; font-size: 12px; color: #888; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CORE LOGIC FUNCTIONS ---

def load_data(path, columns=None):
    if os.path.exists(path):
        return pd.read_excel(path)
    return pd.DataFrame(columns=columns) if columns else pd.DataFrame()

def save_data(df, path):
    df.to_excel(path, index=False)

def check_duplicate(df, plate, date, receipt):
    mask = (df['ሰሌዳ'] == plate) & (df['ቀን'].astype(str) == str(date)) & (df['ደረሰኝ'] == receipt)
    return mask.any()

def sync_logic(row_data, mode="push"):
    try:
        if mode == "push":
            response = requests.post(GSHEET_URL, data=json.dumps(row_data), timeout=2)
            return response.status_code == 200
        return requests.get(GSHEET_URL, timeout=5).json()
    except: return False

# --- 4. AUTHENTICATION & REGISTRATION ---
if not st.session_state.auth:
    tab1, tab2 = st.tabs(["🔑 መግቢያ (Login)", "📝 አዲስ ተጠቃሚ (Register)"])
    
    with tab1:
        with st.form("login_form"):
            u = st.text_input("የተጠቃሚ ስም / Email")
            p = st.text_input("ይለፍ ቃል", type="password")
            if st.form_submit_button("ግባ"):
                users = load_data(USER_FILE)
                if not users.empty:
                    user_match = users[(users['email'] == u) & (users['password'] == p)]
                    if not user_match.empty:
                        if user_match.iloc[0]['status'] == 'Approved':
                            st.session_state.auth = True
                            st.session_state.user_data = user_match.iloc[0]
                            st.rerun()
                        else: st.warning("አካውንትዎ ገና አልተፈቀደም (Pending Approval).")
                    else: st.error("የተሳሳተ መረጃ!")
                else: st.error("ምንም ተጠቃሚ የለም። መጀመሪያ ይመዝገቡ።")

    with tab2:
        st.info("ውል፡ ይህን ፕሮጀክት መቀየር፣ መበርበር ወይም ለሌላ ማጋለጥ በህግ ያስጠይቃል።")
        with st.form("reg_form"):
            full_name = st.text_input("ሙሉ ስም")
            email = st.text_input("Email / ስልክ")
            new_p = st.text_input("አዲስ ፓስዎርድ", type="password")
            agree = st.checkbox("በውሉ ተስማምቻለሁ")
            if st.form_submit_button("ተመዝገብ"):
                if agree and full_name and email:
                    users = load_data(USER_FILE, ["name", "email", "password", "role", "status"])
                    new_user = {"name": full_name, "email": email, "password": new_p, "role": "user", "status": "Pending"}
                    users = pd.concat([users, pd.DataFrame([new_user])], ignore_index=True)
                    save_data(users, USER_FILE)
                    st.success("ምዝገባ ተጠናቋል። አድሚኑ ሲፈቅድልዎት ይላክልዎታል።")
                else: st.error("እባክዎ መረጃ ያሟሉና በውሉ ይስማሙ።")
    st.stop()

# --- 5. APP CONTENT ---
role = st.session_state.user_data['role']
df = load_data(DB_FILE, ["ተ.ቁ", "ሰሌዳ", "ዓይነት", "ቀን", "ቦታ", "ምርመራ", "ብር", "ደረሰኝ", "ሁኔታ", "መርማሪ"])
recycle_df = load_data(RECYCLE_FILE)

# Sidebar
st.sidebar.markdown(f"### 👤 {st.session_state.user_data['name']}")
menu = st.sidebar.selectbox("Main Menu", ["📊 Dashboard", "📝 Registration", "📂 Records", "🖨️ Receipt", "⚙️ Admin Panel"])

# Lock unauthorized access
if menu in ["📊 Dashboard", "🖨️ Receipt", "⚙️ Admin Panel"] and role != 'admin':
    st.error("ይህ ገጽ ለአድሚን ብቻ የተፈቀደ ነው!")
    st.stop()

# --- 6. REGISTRATION PAGE ---
if menu == "📝 Registration":
    st.markdown("<h1 class='main-header'>📝 የተሽከርካሪ ምርመራ ምዝገባ</h1>", unsafe_allow_html=True)
    with st.form("reg_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        v_plate = c1.text_input("የሰሌዳ ቁጥር")
        v_type = c1.selectbox("የተሽከርካሪ ዓይነት", ["ደረቅ", "ፈሳሽ", "ከፍተኛ", "ባጃጅ", "ሞተር", "ልዩ"])
        v_date = c2.date_input("ቀን", datetime.now())
        v_birr = c2.number_input("የምርመራ ክፍያ", min_value=0.0)
        v_rec = c1.text_input("የደረሰኝ ቁጥር")
        v_stat = c2.selectbox("የምርመራ ውጤት", ["ችግር የለበትም", "ችግር ያለበት"])
        v_rep = st.text_area("ዝርዝር ምርመራ (Findings)")
        
        if st.form_submit_button("መረጃውን መዝግብ"):
            if check_duplicate(df, v_plate, v_date, v_rec):
                st.error("⚠️ ማስጠንቀቂያ፡ ይህ መረጃ ቀድሞ ተመዝግቧል (Duplicate Data)!")
            else:
                new_id = len(df) + 1
                new_data = {
                    "ተ.ቁ": new_id, "ሰሌዳ": v_plate, "ዓይነት": v_type, "ቀን": str(v_date), 
                    "ምርመራ": v_stat, "ዝርዝር": v_rep, "ብር": v_birr, "ደረሰኝ": v_rec, 
                    "መርማሪ": st.session_state.user_data['name']
                }
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                save_data(df, DB_FILE)
                st.toast("✅ መረጃው ኦፍላይን ተመዝግቧል!")
                # Background sync
                if sync_logic(new_data): st.toast("☁️ ወደ ክላውድ ተልኳል!")

# --- 7. RECORDS & SEARCH (የተስተካከለ) ---
elif menu == "📂 Records":
    st.markdown("<h1 class='main-header'>📂 የመረጃ ማህደር</h1>", unsafe_allow_html=True)
    
    if not df.empty:
        # ዳታውን ወደ string መቀየር (ስህተት እንዳይመጣ)
        df['ሰሌዳ'] = df['ሰሌዳ'].astype(str)
        df['ደረሰኝ'] = df['ደረሰኝ'].astype(str)
        
        search_q = st.text_input("🔍 ሰሌዳ ወይም ደረሰኝ በመጥቀስ ይፈልጉ...")
        
        if search_q:
            f_df = df[df['ሰሌዳ'].str.contains(search_q, na=False) | 
                      df['ደረሰኝ'].str.contains(search_q, na=False)]
        else:
            f_df = df.copy()

        # እዚህ ጋር ነው ስህተቱ የነበረው - መስመሮቹ እኩል መሆን አለባቸው
        col1, col2 = st.columns(2)
        col1.metric("የተገኘው ብዛት", len(f_df))
        
        f_df['ብር'] = pd.to_numeric(f_df['ብር'], errors='coerce').fillna(0)
        col2.metric("የገቢ ድምር", f"{f_df['ብር'].sum():,.2f} ETB")

        st.dataframe(f_df, use_container_width=True, hide_index=True)
        
        # ለአድሚን ብቻ የሚታይ የጅምላ ማጥፊያ
        if not f_df.empty and st.session_state.user_data['role'] == 'admin':
            if st.button("🗑️ የተመረጡትን በጅምላ አጥፋ (Bulk Delete)"):
                recycle_df = pd.concat([recycle_df, f_df], ignore_index=True)
                df = df.drop(f_df.index)
                save_data(df, DB_FILE)
                save_data(recycle_df, RECYCLE_FILE)
                st.success("መረጃዎቹ ወደ ሪሳይክል ቢን ተዛውረዋል።")
                st.rerun()
    else:
        st.info("ምንም መረጃ የለም።")

       # --- 8. RECEIPT PRINTING ---
elif menu == "🖨️ Receipt":
    st.markdown("<h1 class='main-header'>🖨️ የደረሰኝ ማተሚያ</h1>", unsafe_allow_html=True)
    
    if not df.empty:
        plate_list = df['ሰሌዳ'].unique()
        target = st.selectbox("ተሽከርካሪ ይምረጡ", plate_list)
        res = df[df['ሰሌዳ'] == target]
        
        if not res.empty:
            r = res.iloc[-1]
            st.markdown(f"""
            <div class="receipt-box">
                <h2 style="text-align:center;">የቴክኒክ ምርመራ ማረጋገጫ ደረሰኝ</h2>
                <hr>
                <p><b>ተ.ቁ:</b> {r['ተ.ቁ']} &nbsp;&nbsp; <b>ቀን:</b> {r['ቀን']}</p>
                <p><b>የሰሌዳ ቁጥር:</b> {r['ሰሌዳ']} &nbsp;&nbsp; <b>ዓይነት:</b> {r['ዓይነት']}</p>
                <p><b>የክፍያ መጠን:</b> {r['ብር']} ETB &nbsp;&nbsp; <b>ደረሰኝ:</b> {r['ደረሰኝ']}</p>
                <p><b>የምርመራ ውጤት:</b> <span style="color:red;">{r['ምርመራ']}</span></p>
                <br><br>
                <div style="display:flex; justify-content:space-between;">
                    <div>___________________<br>የመርማሪ ስም: {r.get('መርማሪ', 'ያልተጠቀሰ')}</div>
                    <div>___________________<br>ፊርማ (Signature)</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("ወደ ኤክሴል አውርድና አትም"):
                r.to_frame().T.to_excel("Receipt_Print.xlsx", index=False)
                st.success("ለመታተም ዝግጁ ነው! Receipt_Print.xlsx ፋይሉን ይክፈቱ።")
        else:
            st.warning("ለተመረጠው የሰሌዳ ቁጥር መረጃ አልተገኘም።")
    else:
        st.info("መጀመሪያ መረጃ መመዝገብ አለብዎት።")

# --- 9. ADMIN PANEL (ይህ መስመር አሁን በትክክል ይሰለፋል) ---
elif menu == "⚙️ Admin Panel":
    st.markdown("<h1 class='main-header'>⚙️ የአስተዳደር ክፍል</h1>", unsafe_allow_html=True)
    
    if st.session_state.user_data['role'] != 'admin':
        st.error("ይህ ገጽ ለአድሚን ብቻ የተፈቀደ ነው!")
    else:
        t1, t2, t3, t4 = st.tabs(["☁️ Cloud Sync", "📧 Auto PDF Report", "👥 User Approval", "♻️ Recycle Bin"])
        
        with t1:
            st.subheader("የክላውድ መረጃ ማመሳሰል")
            if st.button("🔄 መረጃዎችን አመሳስል (Sync Now)"):
                with st.spinner("ከክላውድ ጋር እየተገናኘ ነው..."):
                    cloud_data = sync_logic(None, "pull")
                    if cloud_data:
                        new_df = pd.DataFrame(cloud_data)
                        df = pd.concat([df, new_df]).drop_duplicates(subset=['ሰሌዳ','ቀን','ደረሰኝ'], keep='last')
                        save_data(df, DB_FILE)
                        st.success("✅ መረጃው በሰከንድ ውስጥ ተመሳስሏል!")
                    else:
                        st.warning("ክላውድ ላይ መረጃ አልተገኘም ወይም ኢንተርኔት የለም።")

        with t2:
            st.subheader("የሪፖርት መላኪያ (PDF to Email)")
            target_mail = st.text_input("ሪፖርቱ የሚላክበት ኢሜይል", "workualemu@gmail.com")
            if st.button("📧 ሪፖርት አዘጋጅና ላክ"):
                if df.empty:
                    st.error("ምንም መረጃ የለም!")
                else:
                    st.info("ሪፖርት እየተዘጋጀ ነው...")
                    # እዚህ ጋር የቀድሞውን የ PDF እና Email ሎጂክ ይጠቀሙ

        with t3:
            st.subheader("ተጠቃሚዎችን ፍቀድ")
            u_df = load_data(USER_FILE)
            if not u_df.empty:
                st.dataframe(u_df[u_df['status'] == 'Pending'])
                pending_users = u_df[u_df['status'] == 'Pending']['email'].unique()
                if len(pending_users) > 0:
                    to_appr = st.selectbox("የሚፈቀድለት ኢሜይል", pending_users)
                    if st.button("Confirm Approval"):
                        u_df.loc[u_df['email'] == to_appr, 'status'] = 'Approved'
                        save_data(u_df, USER_FILE)
                        st.success("ተጠቃሚው ተፈቅዶለታል!")
                        st.rerun()
                else:
                    st.write("ምንም የሚጠብቅ ተጠቃሚ የለም።")

        with t4:
            st.subheader("♻️ ሪሳይክል ቢን")
            st.dataframe(recycle_df)
            if st.button("ሁሉንም መረጃዎች መልስ (Restore)"):
                df = pd.concat([df, recycle_df]).drop_duplicates()
                save_data(df, DB_FILE)
                if os.path.exists(RECYCLE_FILE): os.remove(RECYCLE_FILE)
                st.success("መረጃዎች ተመልሰዋል!")
                st.rerun()

# --- 10. FOOTER ---
st.markdown(f"""
    <div style="text-align: center; color: grey; font-size: 12px; padding-top: 50px;">
        © በአብክመ ወ/ጠ/ሰ/ሁ/ ዞን ኢ/ስ/ሂ የቲክኒክ ምርመራ መረጃ ቋት | አዘጋጅ፡ ወርቁ አለሙ ወርቅነህ <br>
        ይህ ሲስተም በህግ የተጠበቀ ነው። ያለ አድሚን ፈቃድ መበርበር በህግ ያስቀጣል።
    </div>
""", unsafe_allow_html=True) 
        
        
        
