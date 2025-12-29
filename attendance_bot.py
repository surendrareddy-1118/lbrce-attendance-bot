from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import os
import time
import requests
import json
from datetime import datetime
from github import Github

USERNAME = os.getenv("ERP_USERNAME")
PASSWORD = os.getenv("ERP_PASSWORD")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GITHUB_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")  # Auto-detects repo name

STORED_ATTENDANCE_FILE = "stored_attendance.json"

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    # Use pre-installed Chrome + ChromeDriver from GitHub Actions
    service = Service("/usr/bin/chromedriver")  # Path from browser-actions/setup-chrome
    return webdriver.Chrome(service=service, options=chrome_options)

# [Keep all your existing functions unchanged: parse_attendance_table, get_attendance_icon, etc.]
# ... (paste the rest of your functions here exactly as they are)

def main():
    print("🚀 LBRCE ATTENDANCE BOT STARTED")
    driver = setup_driver()
    
    try:
        print("🔐 Logging in...")
        driver.get("https://erp.lbrce.ac.in/Login/")
        time.sleep(3)
        
        driver.find_element(By.NAME, "txtusername").send_keys(USERNAME)
        driver.find_element(By.NAME, "txtpassword").send_keys(PASSWORD)
        driver.find_element(By.CSS_SELECTOR, 'button.btn.blue.pull-right[onclick*="login()"]').click()
        time.sleep(6)
        
        print("📂 Fetching attendance...")
        driver.get("https://erp.lbrce.ac.in/Discipline/StudentHistory.aspx")
        time.sleep(5)
        driver.find_element(By.NAME, "ctl00$ContentPlaceHolder1$btnAtt").click()
        time.sleep(6)
        
        html = driver.page_source
        current_attendance, overall_percentage = parse_attendance_table(html)
        print(f"✅ Found {len(current_attendance)} subjects | Overall: {overall_percentage}")
        
        stored_attendance = load_from_github()
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        message = f"📊 *ATTENDANCE REPORT*\n🕐 {now}\n👤 Roll: `{USERNAME}`\n📈 Overall: *{overall_percentage}*\n{'='*50}\n\n"
        message += "📋 *SUBJECT-WISE:*\n\n"
        
        for subject in current_attendance:
            icon = get_attendance_icon(subject['percentage'])
            message += f"{icon} *{subject['subject']}*\n  `{subject['present']}/{subject['held']}` | {subject['percentage']}\n\n"
        
        message += f"{'='*50}\n\n"
        
        if stored_attendance:
            absences = compare_attendance(current_attendance, stored_attendance)
            if absences:
                message += "🚨 *ABSENCES DETECTED:*\n\n"
                for absence in absences:
                    emoji = "🔴" if absence['type'] == 'corrected_absent' else "⚠️"
                    message += f"{emoji} *{absence['subject']}*\n"
                    message += f"   Before: `{absence['before_present']}/{absence['before_held']}`\n"
                    message += f"   Now: `{absence['now_present']}/{absence['now_held']}`\n"
                    message += f"   *MISSED: {absence['classes_missed']} class(es)*\n\n"
            else:
                message += "✅ *NO ABSENCES* - All good!\n"
        else:
            message += "ℹ️ *FIRST RUN* - Data saved for tomorrow\n"
        
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
            'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'
        }).raise_for_status()
        print("📱 Telegram sent!")
        
        save_to_github(current_attendance, overall_percentage)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        error_msg = f"❌ *Bot Error*\n`{str(e)[:1000]}`"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
            'chat_id': CHAT_ID, 'text': error_msg, 'parse_mode': 'Markdown'
        })
    finally:
        driver.quit()
        print("🎉 COMPLETED!")

if __name__ == "__main__":
    main()
