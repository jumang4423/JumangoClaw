import requests
import json

url = "https://cart.jlcpcb.com/shoppingCart/smtGood/selectSmtComponentList"
payload = {
    "keyword": "C39535",
    "searchSource": "search",
    "componentAttributes": []
}
headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"
}
try:
    r = requests.post(url, json=payload, headers=headers, timeout=10)
    print("Response Status:", r.status_code)
    try:
        data = r.json()
        print("Data sample:")
        print(json.dumps(data, indent=2)[:500])
    except Exception as je:
        print("Error parsing JSON:", je)
        print("Raw text:", r.text[:300])
except Exception as e:
    print("Request Error:", e)
