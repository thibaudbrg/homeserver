from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def check_ticket_availability_with_selenium(url):
    # Setup WebDriver
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # Uncomment if you do not want the browser window to open
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.get(url)
    
    # Adjust the wait time as necessary for your webpage
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "ike-layout"))
    )
    
    # After the page has loaded, search for the indicator
    try:
        complet_indicator = driver.find_element(By.CSS_SELECTOR, "div.button.tertiary.btn-sm.ike-full.large.margin-left-10.hydrated")
        if complet_indicator:
            print("Tickets are sold out.")
            return False
    except:
        print("Tickets might be available.")
    
    driver.quit()
    return True

# Send messages via Telegram bot
def send_telegram_message(chat_id, token, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Failed to send Telegram message due to: {e}")

def main():
    TOKEN = os.getenv("TOKEN")  # bot_token from .env
    CHAT_ID = os.getenv("CHAT_ID")
    TICKET_URL = os.getenv("TICKET_URL")

    send_telegram_message(CHAT_ID, TOKEN, "ArtiphysBot is starting.")
    
    try:
        while True:
            available = check_ticket_availability_with_selenium(TICKET_URL)
            if available:
                send_telegram_message(CHAT_ID, TOKEN, "Tickets are now available for Artiphys Festival!")
                break  # Stop the bot after sending the message
            else:
                print("Tickets are still not available. Checking again in 5 minutes.")
                send_telegram_message(CHAT_ID, TOKEN, "Checked Artiphys tickets: Still not available.")
            time.sleep(300)  # check every 5 minutes
    except Exception as e:
        send_telegram_message(CHAT_ID, TOKEN, f"ArtiphysBot encountered an error: {e}")
    finally:
        send_telegram_message(CHAT_ID, TOKEN, "ArtiphysBot is exiting.")

if __name__ == "__main__":
    main()
