import streamlit as st
from google import genai
import json
from PIL import Image
import sqlite3
import os
from datetime import datetime
from st_paywall import add_auth

# --- 1. PAGE SETUP & CSS ---
st.set_page_config(page_title="Nextwave Chart AI", page_icon="🌊", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button[kind="primary"] { background-color: #0052FF; color: white; width: 100%; border-radius: 6px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE SETUP ---
os.makedirs("history_images", exist_ok=True)
conn = sqlite3.connect("nextwave_history.db", check_same_thread=False)
c = conn.cursor()

# Trade History Table
c.execute('''CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date_saved TEXT, image_path TEXT, trend TEXT, 
    confidence TEXT, entry_zone TEXT, stop_loss TEXT, take_profit TEXT, support TEXT, 
    resistance TEXT, notes TEXT)''')

# Trial Users Table
c.execute('''CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY, first_login_date TEXT)''')
conn.commit()

# --- 3. AUTHENTICATION & TRIAL LOGIC ---
# Handles Google Login but allows custom trial logic below
add_auth(required=False, show_redirect_button=False)

user_email = st.session_state.get("email")

if not user_email:
    st.info("👋 Welcome to Nextwave Technology! Please log in via the sidebar to start your 7-day free trial.")
    st.stop()

# Verify Status
is_admin = (user_email == st.secrets.get("ADMIN_EMAIL", ""))
is_subscribed = st.session_state.get("user_subscribed", False)

if not is_admin and not is_subscribed:
    c.execute("SELECT first_login_date FROM users WHERE email = ?", (user_email,))
    user_record = c.fetchone()
    
    if not user_record: # First time logging in!
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("INSERT INTO users (email, first_login_date) VALUES (?, ?)", (user_email, today))
        conn.commit()
        trial_start = datetime.now()
    else:
        trial_start = datetime.strptime(user_record[0], "%Y-%m-%d")
        
    days_used = (datetime.now() - trial_start).days
    
    if days_used > 7:
        st.error(f"⏳ Your 7-day free trial has expired, {user_email}.")
        st.markdown(f"### [🚀 Click Here to Subscribe & Unlock Premium]({st.secrets['stripe_link_test']})")
        st.stop()
    else:
        st.warning(f"🕒 Free Trial Active: {7 - days_used} days remaining. Upgrade to Premium for uninterrupted access.")
elif is_admin:
    st.success("👑 Master Admin Account Recognized. Paywall Bypassed.")

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.header("Settings")
    st.divider()
    page = st.radio("Navigation", ["📊 Dashboard", "🕒 History"])

# --- 5. DASHBOARD PAGE ---
if page == "📊 Dashboard":
    st.markdown("## 🌊 NEXTWAVE TECHNOLOGY")
    st.markdown("### AI Chart Analysis for XAUUSD & Major Forex Pairs")

    uploaded_file = st.file_uploader("Upload Chart Screenshot (PNG/JPG)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        left_col, right_col = st.columns([1.2, 2])
        
        with left_col:
            st.image(image, caption="Chart ready for analysis", use_container_width=True)
            analyze_btn = st.button("LAUNCH NEXTWAVE AI", type="primary")
            
        with right_col:
            if analyze_btn:
                api_key = st.secrets["GEMINI_API_KEY"]
                with st.spinner("Calculating key levels and volatility..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        prompt = """
                        Analyze this gold (XAUUSD) trading chart. 
                        You must respond ONLY with a valid JSON object. Do not include markdown formatting or extra text.
                        Ensure your stop loss and take profit suggestions account for ATR (Average True Range) volatility.
                        
                        Use this exact JSON structure:
                        {
                            "trend": "BULLISH", "confidence": "85%", "entry_zone": "4605.50 - 4610.00",
                            "stop_loss": "4590.00", "take_profit": "4640.00", "support": "4600.00",
                            "resistance": "4625.00", "notes": "One concise sentence of trading advice."
                        }
                        """
                        response = client.models.generate_content(model="models/gemini-3.6-flash", contents=[prompt, image])
                        ai_data = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                        
                        # Save Data
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        safe_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                        image_path = f"history_images/chart_{safe_time}.png"
                        image.save(image_path)
                        
                        c.execute('''INSERT INTO history 
                            (date_saved, image_path, trend, confidence, entry_zone, stop_loss, take_profit, support, resistance, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                            (timestamp, image_path, ai_data['trend'], ai_data['confidence'], 
                              ai_data['entry_zone'], ai_data['stop_loss'], ai_data['take_profit'], 
                              ai_data['support'], ai_data['resistance'], ai_data['notes']))
                        conn.commit()
                        
                        # Display Cards
                        st.success("Analysis Complete & Saved to History!")
                        card1, card2, card3 = st.columns(3)
                        with card1:
                            st.markdown("#### 🧭 Trend & Entry")
                            st.write(f"**Trend:** {ai_data['trend']}")
                            st.write(f"**Confidence:** {ai_data['confidence']}")
                            st.write(f"**Entry Zone:** {ai_data['entry_zone']}")
                        with card2:
                            st.markdown("#### 🛡️ Risk Management")
                            st.write(f"**Stop Loss:** {ai_data['stop_loss']}")
                            st.write(f"**Support:** {ai_data['support']}")
                        with card3:
                            st.markdown("#### 🎯 Targets")
                            st.write(f"**Take Profit:** {ai_data['take_profit']}")
                            st.write(f"**Resistance:** {ai_data['resistance']}")
                        st.info(f"**AI Insight:** {ai_data['notes']}")
                    except Exception as e:
                        st.error(f"Error parsing AI response: {e}")

# --- 6. HISTORY PAGE ---
elif page == "🕒 History":
    st.markdown("## 🕒 Trade Analysis History")
    c.execute("SELECT * FROM history ORDER BY id DESC")
    for record in c.fetchall():
        with st.expander(f"{record[1]} - Trend: {record[3]} (Confidence: {record[4]})"):
            hist_col1, hist_col2 = st.columns([1, 2])
            with hist_col1:
                st.image(record[2], use_container_width=True)
            with hist_col2:
                st.write(f"**Entry:** {record[5]}")
                st.write(f"**Stop Loss:** {record[6]}")
                st.write(f"**Take Profit:** {record[7]}")
                st.write(f"**Notes:** {record[10]}")
