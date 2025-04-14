import os
import json
import time
import random
import requests
import datetime
import streamlit as st
import threading
import pandas as pd
import plotly.express as px
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from collections import Counter
import schedule
import zipfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import streamlit.components.v1 as components

# Load environment variables
load_dotenv()

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="NSE Smart Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- USER AUTHENTICATION ---
USER_CREDENTIALS_FILE = "user_credentials.json"

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "downloading" not in st.session_state:
    st.session_state["downloading"] = False
if "scheduled_time" not in st.session_state:
    st.session_state["scheduled_time"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "login"
if "theme" not in st.session_state:
    st.session_state["theme"] = "Dark"
if "download_progress" not in st.session_state:
    st.session_state["download_progress"] = 0
if "process_logs" not in st.session_state:
    st.session_state["process_logs"] = []
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "last_update" not in st.session_state:
    st.session_state["last_update"] = time.time()
if "custom_bg_color" not in st.session_state:
    st.session_state["custom_bg_color"] = "#2A2A72"
if "button_color_start" not in st.session_state:
    st.session_state["button_color_start"] = "#FF8C00"
if "button_color_end" not in st.session_state:
    st.session_state["button_color_end"] = "#00CED1"
if "login_time" not in st.session_state:
    st.session_state["login_time"] = None
if "clock_color" not in st.session_state:
    st.session_state["clock_color"] = "#FFD700"

# Load existing user credentials
def load_credentials():
    if os.path.exists(USER_CREDENTIALS_FILE):
        with open(USER_CREDENTIALS_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                for username, creds in data.items():
                    if isinstance(creds, str):
                        data[username] = {"password": creds, "email": ""}
                return data
            return {}
    return {}

USER_CREDENTIALS = load_credentials()

def save_credentials():
    with open(USER_CREDENTIALS_FILE, "w") as f:
        json.dump(USER_CREDENTIALS, f)

# --- EMAIL CONFIGURATION ---
EMAIL_SENDER = os.getenv("NSE_EMAIL_SENDER", "abinash3373@gmail.com")
EMAIL_PASSWORD = os.getenv("NSE_EMAIL_PASSWORD", "lrcbmmixohcxauax")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        log_entry(f"Email sent to {to_email}: {subject}")
    except Exception as e:
        log_entry(f"Failed to send email: {e}")

# --- CUSTOM CSS FOR STYLING AND ANIMATIONS ---
def apply_global_styles():
    button_gradient = f"linear-gradient(45deg, {st.session_state['button_color_start']}, {st.session_state['button_color_end']})"
    st.markdown(f"""
        <style>
        .stApp {{ 
            font-family: 'Roboto', sans-serif; 
            transition: background 0.5s ease, color 0.5s ease; 
            background: linear-gradient(to bottom right, {st.session_state['custom_bg_color']}, #483D8B); 
        }}
        h1 {{ 
            font-family: 'Poppins', sans-serif; 
            font-weight: bold; 
            text-align: center; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3); 
            animation: fadeIn 1s ease-in; 
        }}
        @keyframes fadeIn {{ 
            from {{ opacity: 0; transform: translateY(-20px); }} 
            to {{ opacity: 1; transform: translateY(0); }} 
        }}
        h3 {{ 
            font-family: 'Montserrat', sans-serif; 
            font-style: italic; 
            text-align: center; 
            animation: slideIn 1s ease-out; 
        }}
        @keyframes slideIn {{ 
            from {{ opacity: 0; transform: translateX(-20px); }} 
            to {{ opacity: 1; transform: translateX(0); }} 
        }}
        .stButton>button {{ 
            background: {button_gradient}; 
            color: white; 
            border: none; 
            border-radius: 25px; 
            padding: 12px 24px; 
            font-size: 18px; 
            transition: all 0.3s ease; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.2); 
        }}
        .stButton>button:hover {{ 
            transform: scale(1.1); 
            box-shadow: 0 6px 20px rgba(0,0,0,0.3); 
        }}
        .stTextInput>input {{ 
            background: rgba(255, 255, 255, 0.1); 
            border: 2px solid {st.session_state['button_color_end']}; 
            border-radius: 15px; 
            color: #FFFFFF; 
            padding: 10px; 
            transition: border-color 0.3s ease, box-shadow 0.3s ease; 
        }}
        .stTextInput>input:focus {{ 
            border-color: {st.session_state['button_color_start']}; 
            box-shadow: 0 0 10px rgba(255, 140, 0, 0.5); 
        }}
        .sidebar .sidebar-content {{ 
            background: linear-gradient(135deg, #1F2A44, #4ECDC4); 
            color: white; 
            padding: 20px; 
            border-radius: 0 0 15px 15px; 
            box-shadow: 0 4px 20px rgba(0,0,0,0.2); 
            animation: slideDown 1s ease-out; 
        }}
        @keyframes slideDown {{ 
            from {{ opacity: 0; transform: translateY(-20px); }} 
            to {{ opacity: 1; transform: translateY(0); }} 
        }}
        .stProgress > div > div {{ 
            background: {button_gradient}; 
            animation: progressAnim 2s infinite ease-in-out; 
        }}
        @keyframes progressAnim {{ 
            0% {{ background-position: 0% 50%; }} 
            50% {{ background-position: 100% 50%; }} 
            100% {{ background-position: 0% 50%; }} 
        }}
        .stPlotlyChart {{ animation: zoomIn 1s ease-in; }}
        @keyframes zoomIn {{ 
            from {{ opacity: 0; transform: scale(0.8); }} 
            to {{ opacity: 1; transform: scale(1); }} 
        }}
        .stWarning {{ background: rgba(255, 0, 0, 0.1); border: 2px solid #FF0000; border-radius: 15px; padding: 10px; color: #FF0000; }}
        .live-time {{ font-size: 18px; color: {st.session_state['clock_color']}; text-align: center; margin-top: 10px; }}
        .folder {{ background: rgba(255, 255, 255, 0.1); border-radius: 10px; padding: 10px; margin: 5px 0; }}
        </style>
    """, unsafe_allow_html=True)

def apply_theme():
    if st.session_state["theme"] == "Dark":
        st.markdown("""
            <style>
            .stApp { background: linear-gradient(to bottom right, #1E1E1E, #2C3E50); color: #FFFFFF; }
            h1 { color: #FF6B6B; }
            h3 { color: #4ECDC4; }
            .stMetric { background: rgba(46, 64, 87, 0.8); border-radius: 15px; padding: 15px; color: #FFD700; }
            .stDataFrame { background: rgba(255, 255, 255, 0.05); border-radius: 15px; }
            </style>
        """, unsafe_allow_html=True)
    elif st.session_state["theme"] == "Light":
        st.markdown("""
            <style>
            .stApp { background: linear-gradient(to bottom right, #F7F7F7, #E0E0E0); color: #333333; }
            h1 { color: #FF4500; }
            h3 { color: #4682B4; }
            .stMetric { background: rgba(255, 255, 255, 0.8); border-radius: 15px; padding: 15px; color: #32CD32; }
            .stDataFrame { background: rgba(0, 0, 0, 0.05); border-radius: 15px; }
            </style>
        """, unsafe_allow_html=True)
    elif st.session_state["theme"] == "Custom":
        st.markdown(f"""
            <style>
            .stApp {{ background: linear-gradient(to bottom right, {st.session_state['custom_bg_color']}, #483D8B); color: #FFD700; }}
            h1 {{ color: #FF00FF; }}
            h3 {{ color: #00FF7F; }}
            .stMetric {{ background: rgba(106, 90, 205, 0.8); border-radius: 15px; padding: 15px; color: #FFA500; }}
            .stDataFrame {{ background: rgba(255, 255, 255, 0.1); border-radius: 15px; }}
            </style>
        """, unsafe_allow_html=True)

# --- LOGIN AND SIGNUP PAGES ---
def signup_page():
    apply_global_styles()
    apply_theme()
    st.sidebar.header("Navigation")
    if st.sidebar.button("Go to Login", help="Switch to Login page"):
        st.session_state["page"] = "login"

    st.title("Welcome to National Stock Exchange Automatic Downloader")
    st.markdown("<h3 style='text-align: center;'>Create Your Account</h3>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            new_username = st.text_input("Username", key="signup_username")
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
            if st.button("Sign Up", help="Register a new account"):
                if not new_username or not new_password or not new_email:
                    st.warning("All fields are required.")
                elif new_username in USER_CREDENTIALS:
                    st.error("Username already exists.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    USER_CREDENTIALS[new_username] = {"password": new_password, "email": new_email}
                    save_credentials()
                    st.success("Signup successful! Please log in.")
                    st.session_state["page"] = "login"

def login_page():
    apply_global_styles()
    apply_theme()
    st.sidebar.header("Navigation")
    if st.sidebar.button("Go to Sign Up", help="Switch to Sign Up page"):
        st.session_state["page"] = "signup"

    st.title("Welcome to National Stock Exchange Automatic Downloader")
    st.markdown("<h3 style='text-align: center;'>Access Your Dashboard</h3>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", help="Log into your account"):
                if username in USER_CREDENTIALS and USER_CREDENTIALS[username]["password"] == password:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.session_state["user_email"] = USER_CREDENTIALS[username]["email"]
                    st.session_state["login_time"] = time.time()
                    st.session_state["page"] = "dashboard"
                    st.success("Login successful!")
                    email_body = f"Dear {username},\n\nYou have successfully logged into the NSE Smart Dashboard at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n\nPrevious Downloads (if any):\n"
                    file_list = []
                    for root, _, files in os.walk(DOWNLOAD_DIR):
                        for file in files:
                            file_path = os.path.join(root, file)
                            file_size = os.path.getsize(file_path) / (1024 * 1024)
                            file_extension = file.split(".")[-1].upper()
                            file_list.append(f"{file} ({file_extension}, {file_size:.2f} MB)")
                    if file_list:
                        email_body += "\n".join(file_list) + f"\n\nTotal Files: {len(file_list)}\n\nHappy downloading!\n\nBest,\nNSE Dashboard Team"
                    else:
                        email_body += "No previous downloads found.\n\nHappy downloading!\n\nBest,\nNSE Dashboard Team"
                    send_email(st.session_state["user_email"], "Login Successful", email_body)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

# --- DIRECTORY SETUP ---
DOWNLOAD_DIR = os.path.join(os.getcwd(), "Nse_Reports")
LOG_DIR = os.path.join(os.getcwd(), "nse_logs")
FEEDBACK_FILE = os.path.join(os.getcwd(), "feedback.txt")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
today_date = datetime.date.today().strftime("%Y-%m-%d")
log_file_path = os.path.join(LOG_DIR, f"download_log_{today_date}.log")

def log_entry(message, manual=False):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(log_message + "\n")
        log_file.flush()
    print(log_message + "\n", flush=True)
    if manual:
        st.session_state["process_logs"].append(log_message)

# --- FILE FORMATS ---
file_formats = {
    "CSV": "CSV_Files", "XLSX": "Excel_Files", "PDF": "PDF_Files", "TXT": "TXT_Files",
    "DAT": "DAT_Files", "DOC": "DOC_Files", "XLS": "XLS_Excel_Files", "ZIP": "ZIP_Files",
}

# --- EXTRACT ZIP FUNCTION ---
def extract_zip(file_path, target_folder):
    log_entry(f"Extracting ZIP: {file_path}")
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(target_folder)
    log_entry(f"Extracted ZIP: {file_path}")

    for root, _, files in os.walk(target_folder):
        for file in files:
            src_path = os.path.join(root, file)
            file_extension = file.split(".")[-1].upper()
            dest_folder = os.path.join(DOWNLOAD_DIR, file_formats.get(file_extension, "Other_Files"), today_date)
            os.makedirs(dest_folder, exist_ok=True)
            dest_path = os.path.join(dest_folder, file)
            os.rename(src_path, dest_path)
            log_entry(f"Moved {file} to {dest_folder}", manual=False)

    os.remove(file_path)
    log_entry(f"Deleted original ZIP file: {file_path}", manual=False)
    
    if st.session_state.get("authenticated", False):
        st.session_state["process_logs"].append(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ZIP file {file_path} deleted after extraction.")
    if st.session_state.get("user_email", "") and st.session_state["authenticated"]:
        email_body = f"Dear {st.session_state['username']},\n\nA ZIP file ({file_path}) was successfully extracted and deleted at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n\nBest,\nNSE Dashboard Team"
        send_email(st.session_state["user_email"], "ZIP Extraction and Deletion", email_body)

    if os.path.exists(target_folder):
        for root, dirs, files in os.walk(target_folder, topdown=False):
            for name in dirs:
                os.rmdir(os.path.join(root, name))

# --- DOWNLOAD FUNCTION ---
def download_reports(manual=False):
    st.session_state["downloading"] = True
    st.session_state["download_progress"] = 0
    if manual:
        st.toast("🚀 Download started!", icon="📥")
        st.session_state["process_logs"] = []
    
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.127 Safari/537.36"
        chrome_options.add_argument(f"user-agent={USER_AGENT}")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        url = "https://www.nseindia.com/all-reports"
        log_entry(f"Accessing {url}", manual)
        driver.get(url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)

        for _ in range(10):
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            time.sleep(1)

        report_links = set()
        elements = driver.find_elements(By.TAG_NAME, "a")
        for elem in elements:
            href = elem.get_attribute("href")
            if href and href.startswith("https") and any(href.lower().endswith(ext.lower()) for ext in file_formats):
                report_links.add(href)

        driver.quit()

        if not report_links:
            log_entry("No Reports Found. Exiting...", manual)
            st.session_state["downloading"] = False
            return

        log_entry(f"Report_Found {len(report_links)} Downloading...", manual)
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT, "Referer": "https://www.nseindia.com/"})
        total_files = len(report_links)
        downloaded_files = 0
        file_details = []
        download_times = []

        for file_url in report_links:
            file_name = file_url.split("/")[-1]
            file_extension = file_name.split(".")[-1].upper()
            target_folder = os.path.join(DOWNLOAD_DIR, file_formats.get(file_extension, "Other_Files"), today_date)
            os.makedirs(target_folder, exist_ok=True)
            file_path = os.path.join(target_folder, file_name)

            if os.path.exists(file_path):
                log_entry(f"Skipping_Report(already exists): {file_name}", manual)
                downloaded_files += 1
                st.session_state["download_progress"] = (downloaded_files / total_files) * 100
                continue

            log_entry(f"Downloading...: {file_name} from {file_url}", manual)
            start_download = time.time()
            for attempt in range(3):
                try:
                    response = session.get(file_url, stream=True, timeout=15)
                    if response.status_code == 200:
                        with open(file_path, "wb") as file:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    file.write(chunk)
                        log_entry(f"Downloaded: {file_name}", manual)
                        download_time = time.time() - start_download
                        download_times.append(download_time)
                        downloaded_files += 1
                        st.session_state["download_progress"] = (downloaded_files / total_files) * 100
                        file_size = os.path.getsize(file_path) / (1024 * 1024)
                        file_details.append(f"{file_name} ({file_extension}, {file_size:.2f} MB)")
                        if file_extension == "ZIP":
                            extract_zip(file_path, target_folder + "_temp")
                        break
                    else:
                        log_entry(f"Retry{attempt+1} for {file_name}", manual)
                        time.sleep(random.uniform(1, 3))
                except requests.exceptions.RequestException as e:
                    log_entry(f"Error Downloading {file_name}: {e}", manual)
                    time.sleep(random.uniform(1, 3))

        avg_download_speed = sum(download_times) / len(download_times) if download_times else 0
        log_entry(f"All Reports Successfully Downloaded: {DOWNLOAD_DIR} (Average Speed: {avg_download_speed:.2f}s/file)", manual)
        st.session_state["downloading"] = False
        st.session_state["download_progress"] = 100
        if manual:
            st.toast("🎉 Download completed!", icon="✅")

        if not manual and st.session_state["user_email"]:
            email_body = f"Dear {st.session_state['username']},\n\nYour scheduled download completed at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n\nFiles Downloaded (Full Details):\n" + "\n".join(file_details) + f"\n\nTotal Files: {len(file_details)}\n\nAverage Download Speed: {avg_download_speed:.2f}s/file\n\nBest,\nNSE Dashboard Team"
            send_email(st.session_state["user_email"], "Scheduled Download Completed", email_body)

    except Exception as e:
        log_entry(f"Download Error: {e}", manual)
        st.session_state["downloading"] = False
        st.error(f"Download failed: {e}")

# --- SCHEDULER FUNCTION ---
def run_scheduler():
    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            log_entry(f"Scheduler Error: {e}")
        time.sleep(1)

# --- LIVE UPDATE FUNCTION ---
def update_live_status():
    if time.time() - st.session_state["last_update"] > 5:
        st.session_state["last_update"] = time.time()
        st.rerun()

# --- SAVE FEEDBACK ---
def save_feedback(feedback):
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {st.session_state['username']}: {feedback}\n")
    log_entry(f"Feedback submitted by {st.session_state['username']}: {feedback}")

# --- STOCK ANALYSIS FUNCTIONS ---
def analyze_stock_csv(file_path):
    """Analyze stock data from a CSV file and return key metrics"""
    try:
        # Read CSV with error handling for malformed lines
        df = pd.read_csv(file_path, on_bad_lines='skip', engine='python')
        
        # Log available columns for debugging
        log_entry(f"Columns in {file_path}: {list(df.columns)}")
        
        # Common stock data columns (expanded list based on potential NSE formats)
        possible_price_cols = ['PRICE', 'CLOSE', 'CLOSE_PRICE', 'LTP', 'LAST_PRICE']
        possible_volume_cols = ['VOLUME', 'VOL', 'QUANTITY', 'TOTAL_TRADE_QTY']
        possible_symbol_cols = ['SYMBOL', 'STOCK', 'NAME', 'TRADING_SYMBOL']
        possible_turnover_cols = ['TURNOVER', 'VALUE', 'TOTAL_TURNOVER']
        possible_open_cols = ['OPEN', 'OPEN_PRICE']

        # Find relevant columns
        price_col = next((col for col in possible_price_cols if col in df.columns), None)
        volume_col = next((col for col in possible_volume_cols if col in df.columns), None)
        symbol_col = next((col for col in possible_symbol_cols if col in df.columns), None)
        turnover_col = next((col for col in possible_turnover_cols if col in df.columns), None)
        open_col = next((col for col in possible_open_cols if col in df.columns), None)

        metrics = {}
        has_data = False

        # Highest price stock
        if price_col and df[price_col].notna().any():
            highest_price_idx = df[price_col].idxmax()
            metrics['highest_price'] = {
                'symbol': df[symbol_col].iloc[highest_price_idx] if symbol_col and not pd.isna(df[symbol_col].iloc[highest_price_idx]) else 'N/A',
                'value': df[price_col].max()
            }
            has_data = True

        # Highest volume stock
        if volume_col and df[volume_col].notna().any():
            highest_volume_idx = df[volume_col].idxmax()
            metrics['highest_volume'] = {
                'symbol': df[symbol_col].iloc[highest_volume_idx] if symbol_col and not pd.isna(df[symbol_col].iloc[highest_volume_idx]) else 'N/A',
                'value': df[volume_col].max()
            }
            has_data = True

        # Highest turnover stock
        if turnover_col and df[turnover_col].notna().any():
            highest_turnover_idx = df[turnover_col].idxmax()
            metrics['highest_turnover'] = {
                'symbol': df[symbol_col].iloc[highest_turnover_idx] if symbol_col and not pd.isna(df[symbol_col].iloc[highest_turnover_idx]) else 'N/A',
                'value': df[turnover_col].max()
            }
            has_data = True

        # Percentage gain (if we have opening and closing prices)
        if open_col and price_col and df[open_col].notna().any() and df[price_col].notna().any():
            df['percent_gain'] = ((df[price_col] - df[open_col]) / df[open_col]) * 100
            highest_gain_idx = df['percent_gain'].idxmax()
            metrics['highest_gain'] = {
                'symbol': df[symbol_col].iloc[highest_gain_idx] if symbol_col and not pd.isna(df[symbol_col].iloc[highest_gain_idx]) else 'N/A',
                'value': df['percent_gain'].max() if not pd.isna(df['percent_gain'].max()) else 0
            }
            has_data = True

        return metrics, df if has_data else (None, None)
    
    except Exception as e:
        log_entry(f"Error analyzing CSV {file_path}: {e}")
        return None, None

def get_all_stock_metrics():
    """Collect stock metrics from all CSV files"""
    all_metrics = []
    all_dfs = []
    
    for root, _, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            if file.lower().endswith('.csv'):
                file_path = os.path.join(root, file)
                metrics, df = analyze_stock_csv(file_path)
                if metrics is not None:
                    all_metrics.append(metrics)
                if df is not None:
                    all_dfs.append(df)
    
    return all_metrics, all_dfs

# --- SMART DASHBOARD ---
def smart_dashboard():
    apply_global_styles()
    apply_theme()
    st.title(f"Welcome, {st.session_state['username']}!")
    st.markdown("<h3 style='text-align: center;'>NSE Smart Dashboard</h3>", unsafe_allow_html=True)

    # --- SIDEBAR ---
    st.sidebar.header("User Profile")
    with st.sidebar.expander(f"👤 {st.session_state['username']}", expanded=False):
        st.write(f"Email: {st.session_state['user_email']}")
        new_password = st.text_input("New Password", type="password", key="new_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
        if st.button("Change Password"):
            if new_password and new_password == confirm_password:
                USER_CREDENTIALS[st.session_state["username"]]["password"] = new_password
                save_credentials()
                st.success("Password changed successfully!")
                st.toast("✅ Password updated!", icon="🎉")
                send_email(st.session_state["user_email"], "Password Changed",
                           f"Dear {st.session_state['username']},\n\nYour password was successfully changed on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n\nBest,\nNSE Dashboard Team")
            elif not new_password:
                st.error("Please enter a new password.")
            else:
                st.error("Passwords do not match.")

    st.sidebar.header("Settings")
    theme = st.sidebar.selectbox("Choose Theme", ["Dark", "Light", "Custom"], index=["Dark", "Light", "Custom"].index(st.session_state["theme"]))
    color_option = st.sidebar.selectbox("Customize Colors", ["Background", "Button Start", "Button End", "Clock"])
    if color_option == "Background":
        custom_bg_color = st.sidebar.color_picker("Background Color", value=st.session_state["custom_bg_color"])
        if custom_bg_color != st.session_state["custom_bg_color"]:
            st.session_state["custom_bg_color"] = custom_bg_color
            st.rerun()
    elif color_option == "Button Start":
        button_color_start = st.sidebar.color_picker("Button Gradient Start", value=st.session_state["button_color_start"])
        if button_color_start != st.session_state["button_color_start"]:
            st.session_state["button_color_start"] = button_color_start
            st.rerun()
    elif color_option == "Button End":
        button_color_end = st.sidebar.color_picker("Button Gradient End", value=st.session_state["button_color_end"])
        if button_color_end != st.session_state["button_color_end"]:
            st.session_state["button_color_end"] = button_color_end
            st.rerun()
    elif color_option == "Clock":
        clock_color = st.sidebar.color_picker("Clock Text Color", value=st.session_state["clock_color"])
        if clock_color != st.session_state["clock_color"]:
            st.session_state["clock_color"] = clock_color
            st.rerun()

    if theme != st.session_state["theme"]:
        st.session_state["theme"] = theme
        st.rerun()

    # Live Time (Dynamic Update with JavaScript)
    components.html(f"""
        <div id="live-time" class="live-time">🕒 Loading...</div>
        <script>
            function updateTime() {{
                const now = new Date();
                const timeString = now.toLocaleString('en-US', {{ year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }});
                document.getElementById('live-time').innerHTML = `🕒 ${{timeString}}`;
            }}
            setInterval(updateTime, 1000);
            updateTime();
        </script>
    """, height=50)

    # About Us
    if st.sidebar.button("About Us"):
        st.sidebar.write("NSE Smart Dashboard is a tool designed to automate downloading and analyzing reports from the National Stock Exchange. Developed by Abinash.")

    # Suggestions and Feedback
    st.sidebar.subheader("Suggestions & Feedback")
    feedback = st.sidebar.text_area("Your Feedback", height=100)
    if st.sidebar.button("Submit Feedback"):
        if feedback:
            save_feedback(feedback)
            st.sidebar.success("Thank you for your feedback!")
            st.toast("📬 Feedback submitted!", icon="✅")
        else:
            st.sidebar.error("Please enter feedback before submitting.")

    # Copyright
    st.sidebar.markdown("<hr>", unsafe_allow_html=True)
    st.sidebar.markdown("<p style='text-align: center;'>© 2025 Copyright by Abinash</p>", unsafe_allow_html=True)

    if st.button("Refresh Dashboard", help="Update dashboard in real-time"):
        update_live_status()

    # --- TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Downloads", "Analytics", "History"])

    with tab1:  # Overview
        st.subheader("Dashboard Overview")

        # Animated Metrics with Tooltips
        col1, col2, col3, col4 = st.columns(4)
        total_files = sum(len(files) for _, _, files in os.walk(DOWNLOAD_DIR))
        total_size = sum(os.path.getsize(os.path.join(dirpath, filename)) / (1024 * 1024) 
                         for dirpath, _, filenames in os.walk(DOWNLOAD_DIR) 
                         for filename in filenames)
        last_download = max((os.path.getmtime(os.path.join(dirpath, filename)) 
                             for dirpath, _, filenames in os.walk(DOWNLOAD_DIR) 
                             for filename in filenames), default=0)
        last_download_str = datetime.datetime.fromtimestamp(last_download).strftime("%Y-%m-%d %H:%M:%S") if last_download else "N/A"
        unique_formats = len({f.split(".")[-1].upper() for _, _, files in os.walk(DOWNLOAD_DIR) for f in files})

        with col1:
            st.metric("Total Files", total_files, help="Total number of downloaded files")
        with col2:
            st.metric("Total Size (MB)", f"{total_size:.2f}", help="Total size of all files")
        with col3:
            st.metric("Last Download", last_download_str, help="Time of the most recent download")
        with col4:
            st.metric("Unique Formats", unique_formats, help="Number of different file types")

        # Histogram of File Sizes
        st.subheader("File Size Distribution")
        file_sizes = [os.path.getsize(os.path.join(dirpath, filename)) / (1024 * 1024) 
                      for dirpath, _, filenames in os.walk(DOWNLOAD_DIR) for filename in filenames]
        if file_sizes:
            df_sizes = pd.DataFrame(file_sizes, columns=["Size (MB)"])
            fig_hist = px.histogram(df_sizes, x="Size (MB)", nbins=20, title="File Size Histogram",
                                    template="plotly_dark" if st.session_state["theme"] == "Dark" else "plotly_white",
                                    color_discrete_sequence=["#FF8C00"])
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.write("No files available for histogram.")

        # Files Graph (by Date)
        st.subheader("Files Downloaded Over Time")
        file_data = []
        for root, _, files in os.walk(DOWNLOAD_DIR):
            date = os.path.basename(os.path.dirname(root)) if "20" in os.path.basename(os.path.dirname(root)) else today_date
            file_data.append({"Date": date, "Count": len(files)})
        if file_data:
            df_files = pd.DataFrame(file_data).groupby("Date").sum().reset_index()
            fig_files = px.bar(df_files, x="Date", y="Count", title="Files by Date",
                               template="plotly_dark" if st.session_state["theme"] == "Dark" else "plotly_white",
                               color="Count", color_continuous_scale="Viridis")
            st.plotly_chart(fig_files, use_container_width=True)
        else:
            st.write("No files downloaded yet.")

        # Real-Time User Activity
        st.subheader("Real-Time User Activity")
        if st.session_state["login_time"]:
            login_time_str = datetime.datetime.fromtimestamp(st.session_state["login_time"]).strftime("%Y-%m-%d %H:%M:%S")
            session_duration = (time.time() - st.session_state["login_time"]) / 3600  # Hours
            st.write(f"Logged in at: {login_time_str}")
            st.write(f"Session Duration: {session_duration:.2f} hours")
        else:
            st.write("No login activity recorded.")

        # File Type Folders
        st.subheader("File Type Explorer")
        folder_data = {}
        for root, _, files in os.walk(DOWNLOAD_DIR):
            folder_name = os.path.basename(os.path.dirname(root))
            if folder_name in file_formats.values():
                if folder_name not in folder_data:
                    folder_data[folder_name] = []
                for file in files:
                    file_path = os.path.join(root, file)
                    folder_data[folder_name].append({
                        "File Name": file,
                        "Size (MB)": os.path.getsize(file_path) / (1024 * 1024),
                        "Last Modified": datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                    })
        if folder_data:
            for folder, files in folder_data.items():
                with st.expander(f"📁 {folder} ({len(files)} files)"):
                    df_folder = pd.DataFrame(files)
                    st.dataframe(df_folder, use_container_width=True, hide_index=True)
        else:
            st.write("No folders available.")

        # Real-Time File Activity Log
        st.subheader("Real-Time Activity Log")
        if st.session_state["process_logs"]:
            log_text = "\n".join(st.session_state["process_logs"][-10:])
            st.code(log_text, language="text", line_numbers=True)
        else:
            st.write("No recent activity.")

    with tab2:  # Downloads
        st.subheader("Download Controls")
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("Start Download", key="start_download"):
                threading.Thread(target=download_reports, args=(True,), daemon=True).start()
        with col2:
            if st.session_state["downloading"]:
                st.markdown("""
                    <style>
                    .loader { border: 4px solid #f3f3f3; border-top: 4px solid #FF8C00; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; }
                    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                    </style>
                    <div class='loader'></div>
                """, unsafe_allow_html=True)
                st.progress(st.session_state["download_progress"])

        col_action1, col_action2 = st.columns(2)
        with col_action1:
            if st.button("Clear History", key="clear_history"):
                for root, dirs, files in os.walk(DOWNLOAD_DIR, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                st.success("Download history cleared!")

        st.subheader("Smart Scheduler")
        with st.container():
            st.markdown("<style>.scheduler { background: rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 15px; }</style>", unsafe_allow_html=True)
            with st.expander("📅 Schedule Download", expanded=False):
                schedule_date = st.date_input("Select Date", value=datetime.date.today())
                schedule_time = st.time_input("Set Time", value=datetime.time(9, 0))
                if st.button("Schedule Download Now"):
                    scheduled_datetime = datetime.datetime.combine(schedule_date, schedule_time)
                    st.session_state["scheduled_time"] = scheduled_datetime.strftime("%H:%M")
                    schedule.every().day.at(st.session_state["scheduled_time"]).do(lambda: download_reports(manual=False))
                    st.success(f"Scheduled for {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}", icon="✅")
                    st.markdown("<style>.success-anim { animation: pulse 1s infinite; } @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }</style>", unsafe_allow_html=True)
                    st.markdown("<div class='success-anim'>Scheduled!</div>", unsafe_allow_html=True)
        if st.session_state["scheduled_time"]:
            st.info(f"Next scheduled download: {st.session_state['scheduled_time']}")

        if st.session_state["downloading"]:
            if os.path.exists(log_file_path):
                with open(log_file_path, "r", encoding="utf-8") as log_file:
                    st.text_area("Live Logs", value=log_file.read(), height=150, key="log_area")
            if st.session_state["process_logs"]:
                log_text = "\n".join(st.session_state["process_logs"][-10:])
                st.code(log_text, language="text", line_numbers=True)
        else:
            st.write("No active downloads.")

    with tab3:  # Analytics
        st.subheader("Download Analytics")
        
        # File list collection
        file_list = []
        for root, _, files in os.walk(DOWNLOAD_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                file_list.append({
                    "File Name": file,
                    "Format": file.split(".")[-1].upper(),
                    "Size (MB)": os.path.getsize(file_path) / (1024 * 1024),
                    "Last Modified": datetime.datetime.fromtimestamp(os.path.getmtime(file_path)),
                    "Path": os.path.dirname(file_path)  # Add directory path for validation
                })

        # Stock Market Analysis Section
        st.subheader("Stock Market Analysis")
        all_metrics, all_dfs = get_all_stock_metrics()
        
        # Display CSV Data Preview for Debugging
        st.subheader("CSV Data Preview")
        csv_files = [f for f in file_list if f["Format"] == "CSV"]
        if csv_files:
            selected_file = st.selectbox("Select a CSV file to preview", [f["File Name"] for f in csv_files])
            # Find the correct file path by searching all directories
            file_path = next((f["Path"] for f in file_list if f["File Name"] == selected_file), None)
            if file_path:
                full_file_path = os.path.join(file_path, selected_file)
                if os.path.exists(full_file_path):
                    try:
                        df_preview = pd.read_csv(full_file_path, on_bad_lines='skip', engine='python', nrows=5)
                        st.dataframe(df_preview)
                        log_entry(f"Previewed {selected_file} successfully")
                    except Exception as e:
                        st.error(f"Error previewing {selected_file}: {e}")
                        log_entry(f"Error previewing {selected_file}: {e}")
                else:
                    st.error(f"File {selected_file} not found at {full_file_path}")
                    log_entry(f"File not found: {full_file_path}")
            else:
                st.error(f"Could not determine path for {selected_file}")
                log_entry(f"Could not determine path for {selected_file}")
        else:
            st.write("No CSV files available for preview.")

        if all_metrics:
            # Display Key Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                highest_price = max((m['highest_price']['value'] for m in all_metrics if 'highest_price' in m and m['highest_price']['value'] > 0), default=0)
                highest_price_symbol = next((m['highest_price']['symbol'] for m in all_metrics if 'highest_price' in m and m['highest_price']['value'] == highest_price), 'N/A')
                st.metric("Highest Price", f"{highest_price:.2f}" if highest_price > 0 else "N/A", f"Stock: {highest_price_symbol}")
            
            with col2:
                highest_volume = max((m['highest_volume']['value'] for m in all_metrics if 'highest_volume' in m and m['highest_volume']['value'] > 0), default=0)
                highest_volume_symbol = next((m['highest_volume']['symbol'] for m in all_metrics if 'highest_volume' in m and m['highest_volume']['value'] == highest_volume), 'N/A')
                st.metric("Highest Volume", f"{highest_volume:,.0f}" if highest_volume > 0 else "N/A", f"Stock: {highest_volume_symbol}")
            
            with col3:
                highest_turnover = max((m['highest_turnover']['value'] for m in all_metrics if 'highest_turnover' in m and m['highest_turnover']['value'] > 0), default=0)
                highest_turnover_symbol = next((m['highest_turnover']['symbol'] for m in all_metrics if 'highest_turnover' in m and m['highest_turnover']['value'] == highest_turnover), 'N/A')
                st.metric("Highest Turnover", f"{highest_turnover:,.0f}" if highest_turnover > 0 else "N/A", f"Stock: {highest_turnover_symbol}")
            
            with col4:
                highest_gain = max((m['highest_gain']['value'] for m in all_metrics if 'highest_gain' in m and m['highest_gain']['value'] > 0), default=0)
                highest_gain_symbol = next((m['highest_gain']['symbol'] for m in all_metrics if 'highest_gain' in m and m['highest_gain']['value'] == highest_gain), 'N/A')
                st.metric("Top % Gain", f"{highest_gain:.2f}%" if highest_gain > 0 else "N/A", f"Stock: {highest_gain_symbol}")

            # Visualizations
            st.subheader("Stock Market Visualizations")
            col_viz1, col_viz2 = st.columns(2)

            with col_viz1:
                # Top 10 stocks by price
                price_data = []
                for metrics in all_metrics:
                    if 'highest_price' in metrics and metrics['highest_price']['value'] > 0:
                        price_data.append({
                            'Symbol': metrics['highest_price']['symbol'],
                            'Price': metrics['highest_price']['value'],
                            'File': metrics['file']
                        })
                if price_data:
                    df_prices = pd.DataFrame(price_data).nlargest(10, 'Price')
                    fig_prices = px.bar(df_prices, x='Symbol', y='Price', 
                                      title='Top 10 Stocks by Price',
                                      template="plotly_dark" if st.session_state["theme"] == "Dark" else "plotly_white",
                                      color='Price', color_continuous_scale='Viridis')
                    st.plotly_chart(fig_prices, use_container_width=True)
                else:
                    st.write("No valid price data available.")

            with col_viz2:
                # Top 10 stocks by volume
                volume_data = []
                for metrics in all_metrics:
                    if 'highest_volume' in metrics and metrics['highest_volume']['value'] > 0:
                        volume_data.append({
                            'Symbol': metrics['highest_volume']['symbol'],
                            'Volume': metrics['highest_volume']['value'],
                            'File': metrics['file']
                        })
                if volume_data:
                    df_volumes = pd.DataFrame(volume_data).nlargest(10, 'Volume')
                    fig_volumes = px.bar(df_volumes, x='Symbol', y='Volume',
                                       title='Top 10 Stocks by Volume',
                                       template="plotly_dark" if st.session_state["theme"] == "Dark" else "plotly_white",
                                       color='Volume', color_continuous_scale='Plasma')
                    st.plotly_chart(fig_volumes, use_container_width=True)
                else:
                    st.write("No valid volume data available.")

            # Percentage Gain Distribution
            gain_data = []
            for df in all_dfs:
                if isinstance(df, pd.DataFrame) and 'percent_gain' in df.columns and df['percent_gain'].notna().any():
                    gain_data.extend(df['percent_gain'].dropna().tolist())
            if gain_data:
                fig_gain_dist = px.histogram(gain_data, x=gain_data, nbins=50,
                                           title='Distribution of Percentage Gains',
                                           template="plotly_dark" if st.session_state["theme"] == "Dark" else "plotly_white",
                                           color_discrete_sequence=['#FF8C00'])
                fig_gain_dist.update_layout(xaxis_title="Percentage Gain (%)", yaxis_title="Count")
                st.plotly_chart(fig_gain_dist, use_container_width=True)
            else:
                st.write("No valid percentage gain data available.")

        else:
            st.warning("No stock data available for analysis. Ensure CSV files contain columns like SYMBOL, PRICE, VOLUME, TURNOVER, or OPEN.")

        # General Analytics
        st.subheader("General File Analytics")
        if file_list:
            df_files = pd.DataFrame(file_list)

            # Side-by-Side Graphs
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("File Sizes Over Time")
                df_files["Date"] = df_files["Last Modified"].dt.date
                df_sizes_time = df_files.groupby("Date")["Size (MB)"].sum().reset_index()
                fig_line = px.line(df_sizes_time, x="Date", y="Size (MB)", title="Total File Size Over Time",
                                 template="plotly_dark" if st.session_state["theme"] == "Dark" else "plotly_white")
                st.plotly_chart(fig_line, use_container_width=True)

            with col2:
                st.subheader("Files by Format")
                format_counts = df_files["Format"].value_counts().reset_index()
                format_counts.columns = ["Format", "Count"]
                fig_bar = px.bar(format_counts, x="Format", y="Count", title="Files by Format",
                               template="plotly_dark" if st.session_state["theme"] == "Dark" else "plotly_white",
                               color="Format")
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.write("No data available for general analytics.")

        st.subheader("File Explorer")
        if file_list:
            df_files = pd.DataFrame(file_list)
            search_query = st.text_input("Search Files")
            if search_query:
                df_files = df_files[df_files["File Name"].str.contains(search_query, case=False)]
            st.dataframe(df_files, height=300, use_container_width=True, hide_index=True)
        else:
            st.write("No files downloaded yet.")

    with tab4:  # History
        st.subheader("Download History")
        if os.path.exists(log_file_path):
            with open(log_file_path, "r", encoding="utf-8") as log_file:
                st.text_area("History Logs", value=log_file.read(), height=400, key=f"history_{time.time()}")
        else:
            st.write("No download history available.")

# --- PAGE NAVIGATION ---
if st.session_state["page"] == "signup":
    signup_page()
elif st.session_state["page"] == "login":
    login_page()
elif st.session_state["page"] == "dashboard" and st.session_state["authenticated"]:
    smart_dashboard()
    if "scheduler_thread" not in st.session_state:
        st.session_state["scheduler_thread"] = threading.Thread(target=run_scheduler, daemon=True)
        st.session_state["scheduler_thread"].start()

# --- SIDEBAR LOGOUT ---
if st.session_state["authenticated"]:
    if st.sidebar.button("Logout", key="logout", help="Log out of your account"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.session_state["scheduled_time"] = None
        st.session_state["page"] = "login"
        st.session_state["login_time"] = None
        schedule.clear()
        st.rerun()