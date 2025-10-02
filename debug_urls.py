#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('D:\\Design & Source Code\\Source Coding\\BudgetsSystem')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')

# Setup Django
django.setup()

from django.urls import reverse
from django.conf import settings

print("=== URL Configuration Debug ===")

# Test URL reversals
url_tests = [
    'api_budget_items_for_org_period',
    'api_factors_for_tankhah', 
    'api_tankhahs_for_allocation',
    'api_organizations_for_period',
    'api_organization_allocations_for_period'
]

for url_name in url_tests:
    try:
        if url_name == 'api_budget_items_for_org_period':
            url = reverse(url_name, kwargs={'period_pk': 25, 'org_pk': 1})
        elif url_name == 'api_factors_for_tankhah':
            url = reverse(url_name, kwargs={'tankhah_pk': 1})
        elif url_name == 'api_tankhahs_for_allocation':
            url = reverse(url_name, kwargs={'alloc_pk': 1})
        elif url_name == 'api_organizations_for_period':
            url = reverse(url_name, kwargs={'period_pk': 25})
        elif url_name == 'api_organization_allocations_for_period':
            url = reverse(url_name, kwargs={'period_pk': 25})
        
        print(f"✅ {url_name}: {url}")
    except Exception as e:
        print(f"❌ {url_name}: {e}")

print("\n=== URL Patterns ===")
from reports.urls import urlpatterns
for pattern in urlpatterns:
    print(f"Pattern: {pattern}")
