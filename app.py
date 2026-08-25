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
if not st.user.is_logged_in:
    st.info("👋 Welcome to Nextwave Technology! Please log in to start your 7-day free trial.")
    if st.button("Log in with Google", type="primary"):
        st.login()
    st.stop()

add_auth(required=False, show_redirect_button=False)

user_email = st.user.email

# Verify Status
is_admin = (user_email == st.secrets.get("ADMIN_EMAIL", ""))
is_subscribed = st.session_state.get("user_subscribed", False)

if not is_admin and not is_subscribed:
    c.execute("SELECT first_login_date FROM users WHERE email = ?", (user_email,))
    user_record = c.fetchone()
    
    if not user_record: # First time logging in
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
    # Professional Header
    st.markdown("""
        <div style='text-align: left; margin-bottom: 20px;'>
            <h1 style='color: #FFFFFF; font-size: 32px; font-weight: 600; letter-spacing: 1px;'>
                NEXTWAVE TECHNOLOGY
            </h1>
            <p style='color: #8B949E; font-size: 16px;'>Institutional-Grade AI Analysis for XAUUSD & Major Forex Pairs</p>
        </div>
    """, unsafe_allow_html=True)
    st.divider()

    left_col, right_col = st.columns([1, 1.8], gap="large")
    
    # Structured Input Card (Left Column)
    with left_col:
        with st.container(border=True):
            st.markdown("### 📁 File Upload Center")
            st.caption("Supported formats: PNG, JPG (Max 200MB)")
            
            uploaded_file = st.file_uploader("", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
            
            if uploaded_file is not None:
                image = Image.open(uploaded_file)
                st.image(image, use_container_width=True)
                
                # Styled Button
                analyze_btn = st.button("LAUNCH PROFESSIONAL ANALYSIS", type="primary", use_container_width=True)

    # Premium Results Area (Right Column)
    with right_col:
        if uploaded_file is not None and analyze_btn:
            api_key = st.secrets["GEMINI_API_KEY"]
            with st.spinner("Analyzing market structure and volatility..."):
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
                    
                    # Card-Based Data Visualization
                    st.success("Analysis Complete & Saved to Secure Database", icon="✅")
                    
                    # Top Metric Cards
                    card1, card2, card3 = st.columns(3)
                    
                    with card1:
                        with st.container(border=True):
                            st.markdown("<h4 style='color: #0052FF;'>📈 Trend & Entry</h4>", unsafe_allow_html=True)
                            st.metric(label="Market Trend", value=ai_data['trend'])
                            st.metric(label="AI Confidence", value=ai_data['confidence'])
                            st.write(f"**Entry Zone:** {ai_data['entry_zone']}")
                            
                    with card2:
                        with st.container(border=True):
                            st.markdown("<h4 style='color: #0052FF;'>🛡️ Risk Limits</h4>", unsafe_allow_html=True)
                            st.metric(label="Stop Loss", value=ai_data['stop_loss'])
                            st.metric(label="Support Lvl", value=ai_data['support'])
                            
                    with card3:
                        with st.container(border=True):
                            st.markdown("<h4 style='color: #0052FF;'>🎯 Targets</h4>", unsafe_allow_html=True)
                            st.metric(label="Take Profit", value=ai_data['take_profit'])
                            st.metric(label="Resistance Lvl", value=ai_data['resistance'])
                            
                    # AI Insights Bottom Card
                    with st.container(border=True):
                        st.markdown("<h4 style='color: #0052FF;'>🧠 AI Insights Report</h4>", unsafe_allow_html=True)
                        st.info(ai_data['notes'], icon="💡")
                        
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
