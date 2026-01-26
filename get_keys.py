# get_keys.py (Isay run karke ID aur Key nikalein)
import requests
import uuid

SUBSCRIPTION_KEY = "4489deae7f934a2db0146e48b0a6767e"
BASE_URL = "https://sandbox.momodeveloper.mtn.com"
CALLBACK_HOST = "75f06aca2b7f.ngrok-free.app"

def create_permanent_user():
    user_uuid = str(uuid.uuid4())
    print("Wait...")
    
    # 1. User Create
    url_user = f"{BASE_URL}/v1_0/apiuser"
    headers = {
        "X-Reference-Id": user_uuid,
        "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
        "Content-Type": "application/json"
    }
    requests.post(url_user, json={"providerCallbackHost": CALLBACK_HOST}, headers=headers)

    # 2. Key Create
    url_key = f"{BASE_URL}/v1_0/apiuser/{user_uuid}/apikey"
    req = requests.post(url_key, headers=headers)
    
    if req.status_code == 201:
        api_key = req.json()['apiKey']
        print("\n✅ INHE COPY KAR K SETTINGS.PY ME DALEN:")
        print(f'MTN_API_USER_ID = "{user_uuid}"')
        print(f'MTN_API_KEY = "{api_key}"')
    else:
        print("Error:", req.text)

create_permanent_user()