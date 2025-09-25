#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
    import django
    django.setup()

    from django.contrib.auth import get_user_model
    from core.models import UserPost, Post, Transition, Status, EntityType
    from tankhah.models import Factor

    username = sys.argv[1] if len(sys.argv) > 1 else 'snejate'
    factor_id = int(sys.argv[2]) if len(sys.argv) > 2 else 77

    User = get_user_model()
    user = User.objects.filter(username=username).first()
    if not user:
        print(f'❌ User {username} not found')
        return

    try:
        factor = Factor.objects.select_related('tankhah__organization', 'status').get(id=factor_id)
    except Factor.DoesNotExist:
        print(f'❌ Factor id={factor_id} not found')
        return

    org = getattr(factor.tankhah, 'organization', None)
    print(f'✅ User: {user.username} | full_name={user.get_full_name()}')
    print(f'✅ Factor: {getattr(factor, "number", factor.id)} | org={getattr(org, "name", None)} | status={getattr(factor.status, "code", None)}')

    print('\n👤 Active posts for user in ANY org:')
    ups = UserPost.objects.filter(user=user, is_active=True).select_related('post', 'post__organization')
    for up in ups:
        print(f' - Post[{up.post.id}]: {up.post.name} @ {up.post.organization.name} (level={up.post.level})')
    if not ups.exists():
        print(' - None')

    print('\n🏢 Active posts for user in factor org:')
    if org:
        ups_org = ups.filter(post__organization=org)
        for up in ups_org:
            print(f' - Post[{up.post.id}]: {up.post.name} @ {up.post.organization.name}')
        if not ups_org.exists():
            print(' - None in factor org')
    else:
        print(' - Factor has no organization')

    draft = Status.objects.filter(code='DRAFT').first()
    et = EntityType.objects.filter(code='FACTOR').first()
    if draft and et and org:
        tr = Transition.objects.filter(organization=org, entity_type=et, from_status=draft).select_related('action','to_status').first()
        if tr:
            print(f'\n🔁 Draft transition: {tr.from_status.code} -> {tr.to_status.code} ({tr.action.code})')
            allowed = list(tr.allowed_posts.values_list('id','name'))
            print('   allowed_posts:', allowed)
        else:
            print('\n🔁 No transition from DRAFT found for org')
    else:
        print('\n⚠️ Missing draft/entity_type/org to inspect transitions')


if __name__ == '__main__':
    main()


