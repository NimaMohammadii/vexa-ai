import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
CARD_NUMBER = os.getenv("CARD_NUMBER", "****-****-****-****")

# آی‌دی عددی خودت (از Secret میاد)
try:
    BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
except Exception:
    BOT_OWNER_ID = 0

DEBUG = True