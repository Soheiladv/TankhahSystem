#!/usr/bin/env python
import requests
import json
import re

def get_csrf_token(session, url):
    """Get CSRF token from a page"""
    response = session.get(url)
    csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', response.text)
    return csrf_match.group(1) if csrf_match else None

def test_api_endpoints():
    """Test all API endpoints for comprehensive budget report"""
    session = requests.Session()
    
    # Login first
    login_url = "http://127.0.0.1:8000/accounts/login/"
    csrf_token = get_csrf_token(session, login_url)
    
    if not csrf_token:
        print("❌ Could not get CSRF token")
        return
    
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
    
    # Test API endpoints
    api_tests = [
        {
            'name': 'Budget Items for Org Period',
            'url': 'http://127.0.0.1:8000/reports/api/budget-items-for-org-period/25/1/',
            'method': 'GET'
        },
        {
            'name': 'Factors for Tankhah',
            'url': 'http://127.0.0.1:8000/reports/api/factors-for-tankhah/1/',
            'method': 'GET'
        },
        {
            'name': 'Tankhahs for Allocation',
            'url': 'http://127.0.0.1:8000/reports/api/tankhahs-for-allocation/1/',
            'method': 'GET'
        },
        {
            'name': 'Organizations for Period',
            'url': 'http://127.0.0.1:8000/reports/api/organizations-for-period/25/',
            'method': 'GET'
        },
        {
            'name': 'Organization Allocations',
            'url': 'http://127.0.0.1:8000/reports/api/period/25/organization-allocations/',
            'method': 'GET'
        }
    ]
    
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/json'
    }
    
    for test in api_tests:
        print(f"\n🧪 Testing: {test['name']}")
        print(f"   URL: {test['url']}")
        
        try:
            if test['method'] == 'GET':
                response = session.get(test['url'], headers=headers)
            else:
                response = session.post(test['url'], headers=headers)
            
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    print(f"   ✅ JSON Response: {json.dumps(json_data, indent=2)[:200]}...")
                except:
                    print(f"   ⚠️  HTML Response (first 200 chars): {response.text[:200]}")
            else:
                print(f"   ❌ Error Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"   💥 Exception: {e}")

if __name__ == "__main__":
    test_api_endpoints()
