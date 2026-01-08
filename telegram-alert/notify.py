import os, requests, sys
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown",  # optional
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Message sent successfully")
        else:
            print("Failed to send message:", response.text)
    except Exception as e:
        return {"error": str(e)}



def main():
    if len(sys.argv) < 2:
        print("Usage: python notify.py <alert_message>")
        sys.exit(1)
    alert_message = sys.argv[1]
    send_telegram(alert_message)



if __name__ == "__main__":
    main()