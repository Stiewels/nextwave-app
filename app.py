import streamlit as st
from google import genai
import json
from PIL import Image
import sqlite3
import os
from datetime import datetime
from st_paywall import add_auth

# --- 1. PAGE SETUP & ADVANCED CSS ---
st.set_page_config(page_title="Nextwave AI | Pro", page_icon="🌊", layout="wide")

st.markdown("""
    <style>
    /* Institutional Dark Theme */
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    
    /* Sleek Primary Buttons */
    .stButton>button[kind="primary"] { 
        background: linear-gradient(90deg, #0052FF 0%, #1E40AF 100%);
        color: white; width: 100%; border-radius: 4px; border: none; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;
    }
    .stButton>button[kind="primary"]:hover { background: #1E40AF; border: 1px solid #60A5FA; }
    
    /* Clean Sidebar */
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #1f2937; }
    
    /* Metric Card Text Formatting */
    .metric-label { font-size: 0.85rem; color: #9ca3af; text-transform: uppercase; font-weight: 600; margin-bottom: -10px; }
    .val-green { color: #10b981; font-size: 1.8rem; font-weight: 700; }
    .val-red { color: #ef4444; font-size: 1.8rem; font-weight: 700; }
    .val-blue { color: #3b82f6; font-size: 1.8rem; font-weight: 700; }
    .val-white { color: #ffffff; font-size: 1.8rem; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE SETUP ---
os.makedirs("history_images", exist_ok=True)
conn = sqlite3.connect("nextwave_history.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date_saved TEXT, image_path TEXT, trend TEXT, 
    confidence TEXT, entry_zone TEXT, stop_loss TEXT, take_profit TEXT, support TEXT, 
    resistance TEXT, notes TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, first_login_date TEXT)''')
conn.commit()

# --- 3. SECURE AUTHENTICATION & TRIAL LOGIC ---
if not st.user.is_logged_in:
    st.markdown("<h2 style='text-align: center; margin-top: 10vh;'>🌊 NEXTWAVE TECHNOLOGY</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8B949E;'>Institutional Market Analysis. Please log in to start your 7-day free trial.</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Log in with Google", type="primary"):
            st.login()
    st.stop()

add_auth(required=False, show_redirect_button=False)
user_email = st.user.email
is_admin = (user_email == st.secrets.get("ADMIN_EMAIL", ""))
is_subscribed = st.session_state.get("user_subscribed", False)

if not is_admin and not is_subscribed:
    c.execute("SELECT first_login_date FROM users WHERE email = ?", (user_email,))
    user_record = c.fetchone()
    
    if not user_record:
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("INSERT INTO users (email, first_login_date) VALUES (?, ?)", (user_email, today))
        conn.commit()
        trial_start = datetime.now()
    else:
        trial_start = datetime.strptime(user_record[0], "%Y-%m-%d")
        
    days_used = (datetime.now() - trial_start).days
    
    if days_used > 7:
        st.error("⏳ 7-Day Free Trial Expired.")
        st.markdown(f"### [🚀 Subscribe to Unlock Nextwave Premium]({st.secrets['stripe_link_test']})")
        st.stop()
    else:
        st.warning(f"🕒 Trial Active: {7 - days_used} days remaining.")

# --- 4. PROFESSIONAL SIDEBAR ---
with st.sidebar:
    st.markdown("### 🌊 NEXTWAVE PRO")
    st.caption(f"Logged in as: {user_email}")
    if is_admin:
        st.success("👑 Master Admin Active", icon="✔️")
    st.divider()
    page = st.radio("MAIN MENU", ["📊 Market Analyzer", "📓 Trade Journal"])

# --- 5. MARKET ANALYZER (DASHBOARD) ---
if page == "📊 Market Analyzer":
    st.markdown("<h2 style='color: #FFFFFF; font-weight: 600;'>Market Analyzer Pipeline</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8B949E; margin-top: -10px;'>Upload XAUUSD or Forex charts for AI-driven structural analysis.</p>", unsafe_allow_html=True)
    
    left_col, right_col = st.columns([1, 1.8], gap="large")
    
    with left_col:
        with st.container(border=True):
            st.markdown("#### 📥 Data Input")
            uploaded_file = st.file_uploader("Upload Chart (PNG/JPG)", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
            
            if uploaded_file is not None:
                image = Image.open(uploaded_file)
                st.image(image, use_container_width=True)
                analyze_btn = st.button("EXECUTE ANALYSIS SCAN", type="primary", use_container_width=True)

    with right_col:
        if uploaded_file is None:
            st.info("Awaiting chart data. Upload a screenshot to generate liquidity and structural analysis.", icon="ℹ️")
            
        elif uploaded_file is not None and analyze_btn:
            api_key = st.secrets["GEMINI_API_KEY"]
            with st.spinner("Scanning for liquidity sweeps and structural breaks..."):
                try:
                    client = genai.Client(api_key=api_key)
                    # Advanced Prompting for SMC & ATR
                    prompt = """
                    Analyze this XAUUSD/Forex chart as an institutional algorithmic trader.
                    Specifically look for Smart Money Concepts (SMC) including Fair Value Gaps (FVG), Break of Structure (BoS), and recent Liquidity Sweeps.
                    Ensure Stop Loss and Take Profit levels factor in ATR (Average True Range) volatility to avoid premature stop-outs.
                    
                    Respond ONLY with a valid JSON object matching this exact structure exactly:
                    {
                        "trend": "BULLISH/BEARISH/RANGING", "confidence": "XX%", "entry_zone": "Price - Price",
                        "stop_loss": "Price", "take_profit": "Price", "support": "Price",
                        "resistance": "Price", "notes": "One highly technical sentence explaining the setup based on SMC and liquidity."
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
                    
                    # Display Premium Results
                    st.success(f"Analysis successfully logged to database at {timestamp}", icon="✅")
                    
                    # Data Row 1
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        with st.container(border=True):
                            st.markdown("<p class='metric-label'>Market Structure</p>", unsafe_allow_html=True)
                            st.markdown(f"<p class='val-blue'>{ai_data['trend']}</p>", unsafe_allow_html=True)
                            st.caption(f"Confidence: **{ai_data['confidence']}**")
                    with c2:
                        with st.container(border=True):
                            st.markdown("<p class='metric-label'>Entry Zone</p>", unsafe_allow_html=True)
                            st.markdown(f"<p class='val-white'>{ai_data['entry_zone']}</p>", unsafe_allow_html=True)
                            st.caption("Optimal Execution Area")
                    with c3:
                        with st.container(border=True):
                            st.markdown("<p class='metric-label'>Key Resistance</p>", unsafe_allow_html=True)
                            st.markdown(f"<p class='val-white'>{ai_data['resistance']}</p>", unsafe_allow_html=True)
                            st.caption(f"Support Base: {ai_data['support']}")
                            
                    # Data Row 2 (Risk Management)
                    r1, r2 = st.columns(2)
                    with r1:
                        with st.container(border=True):
                            st.markdown("<p class='metric-label'>Target (Take Profit)</p>", unsafe_allow_html=True)
                            st.markdown(f"<p class='val-green'>{ai_data['take_profit']}</p>", unsafe_allow_html=True)
                    with r2:
                        with st.container(border=True):
                            st.markdown("<p class='metric-label'>Risk Limit (Stop Loss)</p>", unsafe_allow_html=True)
                            st.markdown(f"<p class='val-red'>{ai_data['stop_loss']}</p>", unsafe_allow_html=True)
                            
                    # Insight Card
                    with st.container(border=True):
                        st.markdown("<p class='metric-label' style='color: #60A5FA;'>🧠 Institutional Insight</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='font-size: 1.1rem; padding-top: 10px;'>{ai_data['notes']}</p>", unsafe_allow_html=True)
                        
                except Exception as e:
                    st.error(f"System Error parsing output: {e}")

# --- 6. TRADE JOURNAL (HISTORY) ---
elif page == "📓 Trade Journal":
    st.markdown("<h2 style='color: #FFFFFF; font-weight: 600;'>Trade Journal & Logs</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8B949E; margin-top: -10px;'>Historical records of all executed chart analyses.</p>", unsafe_allow_html=True)
    
    c.execute("SELECT * FROM history ORDER BY id DESC")
    records = c.fetchall()
    
    if not records:
        st.info("No historical data found. Execute a scan to populate your journal.")
    else:
        for record in records:
            with st.expander(f"SCAN {record[0]} | DATE: {record[1]} | TREND: {record[3]}"):
                j_col1, j_col2, j_col3 = st.columns([1.5, 1, 1])
                with j_col1:
                    st.image(record[2], use_container_width=True)
                with j_col2:
                    st.markdown("**Execution Plan**")
                    st.write(f"Entry: `{record[5]}`")
                    st.write(f"Stop Loss: `{record[6]}`")
                    st.write(f"Take Profit: `{record[7]}`")
                with j_col3:
                    st.markdown("**Structural Data**")
                    st.write(f"Confidence: `{record[4]}`")
                    st.write(f"Support: `{record[8]}`")
                    st.write(f"Resistance: `{record[9]}`")
                st.info(f"**Insight:** {record[10]}")
