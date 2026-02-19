import requests
from django.conf import settings

class OrangePaymentService:
    @staticmethod
    def get_access_token():
        headers = {
            "Authorization": settings.ORANGE_AUTHORIZATION_HEADER,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}

        response = requests.post(settings.ORANGE_AUTH_URL, headers=headers, data=data)
        
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print("Token Error:", response.json()) 
            return None

    @staticmethod
    def create_payment_url(order_id, amount, return_url, cancel_url, notif_url):
        token = OrangePaymentService.get_access_token()
        if not token:
            return {"error": "Token generate nahi ho saka. Apne Authorization Header check karein."}

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        payload = {
            "merchant_key": settings.ORANGE_MERCHANT_KEY,
            "currency": "OUV", 
            "order_id": str(order_id),
            "amount": amount,
            "return_url": return_url, 
            "cancel_url": cancel_url,
            "notif_url": notif_url,  
            "lang": "en",
            "reference": "My_App"
        }

        response = requests.post(settings.ORANGE_PAYMENT_URL, headers=headers, json=payload)
        return response.json()
    
    # ---- NAYA: B2C Payment (App to User Phone) ----
    @staticmethod
    def send_b2c_payment(order_id, amount, phone_number):
        token = OrangePaymentService.get_access_token()
        if not token:
            return {"error": "Token generate nahi ho saka."}

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # B2C api me msisdn (phone number) jata hai
        payload = {
            "merchant_key": settings.ORANGE_MERCHANT_KEY,
            "currency": "OUV", 
            "order_id": str(order_id),
            "amount": amount,
            "msisdn": phone_number, # <--- User ka phone number yahan jayega
            "reference": "App_Payout"
        }

        # Dihan dein: B2C ke liye URL alag hai (settings.ORANGE_B2C_URL)
        response = requests.post(settings.ORANGE_B2C_URL, headers=headers, json=payload)
        return response.json()