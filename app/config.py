import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'devices.db')}"
SECRET_KEY = "change-this-to-a-random-secret-key"
