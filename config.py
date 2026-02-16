import logging
import os
from dotenv import load_dotenv

load_dotenv()

TG_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
PROXY_URL = os.getenv('PROXY_URL')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'retain.db')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
