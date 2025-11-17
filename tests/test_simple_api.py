#!/usr/bin/env python
import requests
import json

def test_simple_api():
    """Test a simple API endpoint to see what's happening"""
    session = requests.Session()
    
    # Login first
    login_url = "http://127.0.0.1:8000/accounts/login/"
    response = session.get(login_url)
    
    # Extract CSRF token
    import re
    csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', response.text)
    if not csrf_match:
        print("❌ Could not get CSRF token")
        return
    
    csrf_token = csrf_match.group(1)
    
    login_data = {
        'username': 'admin',
        'password': 'admin',
        'csrfmiddlewaretoken': csrf_token,
        'next': '/'
    }
    
    login_response = session.post(login_url, data=login_data)
    print(f"🔐 Login Status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print("❌ Login failed")
        return
    
    # Test the API with detailed debugging
    api_url = "http://127.0.0.1:8000/reports/api/budget-items-for-org-period/25/1/"
    
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    print(f"\n🧪 Testing API: {api_url}")
    print(f"   Headers: {headers}")
    
    try:
        response = session.get(api_url, headers=headers)
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        
        if response.status_code == 200:
            if 'application/json' in response.headers.get('Content-Type', ''):
                try:
                    json_data = response.json()
                    print(f"   ✅ JSON Response: {json.dumps(json_data, indent=2)[:500]}...")
                except Exception as e:
                    print(f"   ❌ JSON Parse Error: {e}")
                    print(f"   Raw Response: {response.text[:500]}")
            else:
                print(f"   ⚠️  HTML Response (first 500 chars):")
                print(response.text[:500])
        else:
            print(f"   ❌ Error Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"   💥 Exception: {e}")

if __name__ == "__main__":
    test_simple_api()
