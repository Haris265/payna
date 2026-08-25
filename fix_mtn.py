import requests
import uuid

# --- SETTINGS ---
SUB_KEY = "4489deae7f934a2db0146e48b0a6767e"  # Apki Collection Primary Key
NGROK_DOMAIN = "9e4c-103-121-41-213.ngrok-free.app"
NEW_UUID = str(uuid.uuid4()) # Naya User ID

BASE_URL = "https://sandbox.momodeveloper.mtn.com/v1_0"

# 1. Create API User
headers_user = {
    "X-Reference-Id": NEW_UUID,
    "Ocp-Apim-Subscription-Key": SUB_KEY,
    "Content-Type": "application/json"
}
payload_user = {"providerCallbackHost": NGROK_DOMAIN}

res_user = requests.post(f"{BASE_URL}/apiuser", json=payload_user, headers=headers_user)

if res_user.status_code == 201:
    print(f"✅ NEW API USER ID: {NEW_UUID}")
    
    # 2. Create API Key
    res_key = requests.post(f"{BASE_URL}/apiuser/{NEW_UUID}/apikey", headers={"Ocp-Apim-Subscription-Key": SUB_KEY})
    if res_key.status_code == 201:
        print(f"✅ NEW API KEY: {res_key.json().get('apiKey')}")
        print("\nAb ye dono cheezein apni .env file mein update kar lein.")
    else:
        print(f"❌ Key Error: {res_key.text}")
else:
    print(f"❌ User Error: {res_user.text}")