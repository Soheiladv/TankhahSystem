#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
    import django
    django.setup()

    from django.test import Client
    from django.contrib.auth import get_user_model
    from django.urls import reverse
    from django.conf import settings
    from tankhah.models import Factor
    from core.models import Status

    User = get_user_model()
    # تضمین پذیرش testserver
    if 'testserver' not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append('testserver')
    client = Client(HTTP_HOST='testserver')

    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        print('❌ No superuser found')
        sys.exit(1)

    client.force_login(admin)
    print(f'✅ Logged in as admin: {admin.username}')

    # 1) GET control page
    url_control = reverse('admin_workflow_control', args=['factor', 78])
    resp = client.get(url_control)
    print('GET', url_control, '->', resp.status_code)
    try:
        html = resp.content.decode('utf-8', errors='ignore')
    except Exception:
        html = ''
    print(' - Contains form id="changeStatusForm"? ', 'id="changeStatusForm"' in html)

    # 2) POST change status to a different status
    try:
        factor = Factor.objects.get(id=78)
    except Factor.DoesNotExist:
        print('❌ Factor id=78 not found')
        return

    cur = getattr(factor, 'status', None)
    new = Status.objects.exclude(id=getattr(cur, 'id', None)).filter(is_active=True).first()
    if new is None:
        print('❌ No alternative active status to change to')
    else:
        url_change = reverse('admin_change_status', args=['factor', 78])
        resp2 = client.post(url_change, { 'new_status_id': new.id, 'comment': 'via TestClient' })
        print('POST', url_change, '->', resp2.status_code)
        try:
            print(' - JSON:', resp2.json())
        except Exception as ex:
            print(' - Not JSON:', ex, resp2.content[:200])

    # 3) POST reset workflow
    url_reset = reverse('admin_reset_workflow', args=['factor', 78])
    resp3 = client.post(url_reset, { 'clear_logs': 'false' })
    print('POST', url_reset, '->', resp3.status_code)
    try:
        print(' - JSON:', resp3.json())
    except Exception as ex:
        print(' - Not JSON:', ex, resp3.content[:200])

    # 4) GET fallback change via querystring
    url_fallback = url_control + f"?new_status_id=1&comment=via+GET+fallback"
    resp4 = client.get(url_fallback)
    print('GET (fallback)', url_fallback, '->', resp4.status_code)


if __name__ == '__main__':
    main()


