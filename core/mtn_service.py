# services.py
import requests
import uuid
import base64
import time
from django.conf import settings

class MTNService:
    
    @staticmethod
    def generate_access_token():
        try:
            user_uuid = settings.MTN_API_USER_ID
            api_key = settings.MTN_API_KEY
            
            if not user_uuid or not api_key:
                print("Error: MTN_API_USER_ID or MTN_API_KEY missing in settings.")
                return None

            url_token = f"{settings.MTN_BASE_URL}/collection/token/"
            
            creds = f"{user_uuid}:{api_key}"
            encoded_creds = base64.b64encode(creds.encode()).decode()

            headers_token = {
                "Authorization": f"Basic {encoded_creds}",
                "Ocp-Apim-Subscription-Key": settings.MTN_SUBSCRIPTION_KEY
            }

            req_token = requests.post(url_token, headers=headers_token)
            
            if req_token.status_code == 200:
                return req_token.json().get('access_token')
            else:
                print(f"MTN Token Error: {req_token.text}")
                return None

        except Exception as e:
            print(f"Service Exception: {e}")
            return None

    @staticmethod
    def request_to_pay(token, amount, phone_number, transaction_ref_id):
        """
        Returns: (success: bool, message: str)
        """
        url = f"{settings.MTN_BASE_URL}/collection/v1_0/requesttopay"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": transaction_ref_id,
            "X-Target-Environment": settings.MTN_ENVIRONMENT,
            "Ocp-Apim-Subscription-Key": settings.MTN_SUBSCRIPTION_KEY,
            "Content-Type": "application/json",
            "X-Callback-Url": f"https://{settings.MTN_CALLBACK_HOST}/api/payment/callback/"
        }

        body = {
            "amount": str(amount),
            "currency": "EUR", 
            "externalId": f"tr_{int(time.time())}",
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone_number
            },
            "payerMessage": "Payment via App",
            "payeeNote": "Merchant Payment"
        }

        try:
            response = requests.post(url, json=body, headers=headers)
            
            # 202 Means ACCEPTED (Pending Confirmation)
            if response.status_code == 202:
                return True, "Payment Initiated Successfully"
            
            # Error Handling
            print(f"MTN Request Failed: {response.status_code} - {response.text}")
            return False, response.text

        except Exception as e:
            return False, str(e)

    @staticmethod
    def check_status(token, transaction_ref_id):
        """
        Status Check with FULL DEBUGGING
        """
        url = f"{settings.MTN_BASE_URL}/collection/v1_0/requesttopay/{transaction_ref_id}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Target-Environment": settings.MTN_ENVIRONMENT,
            "Ocp-Apim-Subscription-Key": settings.MTN_SUBSCRIPTION_KEY
        }
        
        print(f"\n--- DEBUGGING MTN CHECK STATUS ---")
        print(f"URL: {url}")
        print(f"Ref ID: {transaction_ref_id}")
        print(f"Token: {token[:10]}... (Hidden)")

        try:
            response = requests.get(url, headers=headers)
            
            print(f"MTN Status Code: {response.status_code}")
            print(f"MTN Response Body: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            
            # Agar 200 nahi aaya, to None return karne se pehle print ho chuka hai
            return None

        except Exception as e:
            print(f"PYTHON ERROR in check_status: {e}")
            return None