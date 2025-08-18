import requests
import json

# First, setup posts
try:
    response = requests.post("http://localhost:8000/api/setup-posts")
    print("Setup posts response:", response.json())
except Exception as e:
    print("Setup posts error:", e)

# Test chat text (your example)
chat_text = """🚐 SOG: SGT Lastre

💻 CQ: SGT Park

🚧 ECP1: SPC Henderson

🚧 ECP2: SPC Cox

🚧 ECP3: PV2 Anderson

🛺 VCP: SGT Warren

🚧 ROVER: PFC Smith

Stand by: PV2 Johnson"""

data = {
    "chat_text": chat_text,
    "duty_date": "2024-01-15"
}

# Test import
try:
    response = requests.post("http://localhost:8000/api/import-chat", json=data)
    print("Import response status:", response.status_code)
    print("Import response:", response.json())
except Exception as e:
    print("Import error:", e)

# Check dashboard stats
try:
    response = requests.get("http://localhost:8000/api/dashboard")
    print("Dashboard response:", response.json())
except Exception as e:
    print("Dashboard error:", e)
