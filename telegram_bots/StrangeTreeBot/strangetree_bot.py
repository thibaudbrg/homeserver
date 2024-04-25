import requests
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def fetch_links_from_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    
    # Extracting all links
    all_links = [a.get('href') for a in soup.find_all('a') if a.get('href')]
    
    # Filtering links that redirect to smeetz.com
    smeetz_links = [link for link in all_links if 'smeetz.com' in link]
    
    return smeetz_links

previous_links = fetch_links_from_website(os.getenv("URL"))

def has_new_link():
    global previous_links
    current_links = fetch_links_from_website(os.getenv("URL"))
    
    new_links = set(current_links) - set(previous_links)
    previous_links = current_links
    
    return list(new_links)

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
    TOKEN = os.getenv("TOKEN")
    CHAT_ID = os.getenv("CHAT_ID")

    while True:
        try:
            new_links = has_new_link()
            if new_links:
                for link in new_links:
                    send_telegram_message(CHAT_ID, TOKEN, f"New event detected: {link}")

            time.sleep(3600/3)  # check every hour
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(60)  # Wait a minute before trying again

if __name__ == "__main__":
    main()
