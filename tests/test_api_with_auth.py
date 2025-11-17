#!/usr/bin/env python
import requests
import json

# Create a session to maintain login state
session = requests.Session()

# First, login to get authentication
login_url = "http://127.0.0.1:8000/accounts/login/"
login_data = {
    'username': 'admin',  # or your test username
    'password': 'admin',  # or your test password
}

# Get the login page first to get CSRF token
login_page = session.get(login_url)
csrf_token = None
for line in login_page.text.split('\n'):
    if 'csrfmiddlewaretoken' in line:
        csrf_token = line.split('value="')[1].split('"')[0]
        break

if csrf_token:
    login_data['csrfmiddlewaretoken'] = csrf_token
    login_data['next'] = '/'
    
    # Login
    login_response = session.post(login_url, data=login_data)
    print(f"Login Status: {login_response.status_code}")
    
    # Now test the API
    api_url = "http://127.0.0.1:8000/reports/api/budget-items-for-org-period/25/1/"
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/json'
    }
    
    try:
        response = session.get(api_url, headers=headers)
        print(f"API Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                print(f"JSON Response: {json.dumps(json_data, indent=2)[:500]}...")
            except:
                print(f"Response is not JSON. First 200 chars: {response.text[:200]}")
        else:
            print(f"Error Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"Request failed: {e}")
else:
    print("Could not find CSRF token")
