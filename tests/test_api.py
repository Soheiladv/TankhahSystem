#!/usr/bin/env python
import requests
import json

# Test the API endpoint that's failing
url = "http://127.0.0.1:8000/reports/api/budget-items-for-org-period/25/1/"

headers = {
    'X-Requested-With': 'XMLHttpRequest',
    'Content-Type': 'application/json'
}

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Content: {response.text[:500]}...")
    
    if response.status_code == 500:
        print("\n=== 500 Error Details ===")
        try:
            error_data = response.json()
            print(f"JSON Error: {error_data}")
        except:
            print("Response is not JSON")
            
except Exception as e:
    print(f"Request failed: {e}")
