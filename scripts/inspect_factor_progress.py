#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
    import django
    django.setup()

    from django.contrib.auth import get_user_model
    from django.db.models import Prefetch
    from core.models import Transition, Status, EntityType, UserPost
    from tankhah.models import Factor

    fid = int(sys.argv[1]) if len(sys.argv) > 1 else 79
    User = get_user_model()

    try:
        factor = Factor.objects.select_related('tankhah__organization','status','created_by').get(id=fid)
    except Factor.DoesNotExist:
        print(f'❌ Factor {fid} not found')
        return

    org = getattr(factor.tankhah, 'organization', None)
    print(f'✅ Factor[{factor.id}] {getattr(factor, "number", "-")} | org={getattr(org, "name", None)} | status={getattr(factor.status, "code", None)}')
    print(f'   creator={getattr(factor.created_by, "username", None)}')

    if not org or not factor.status:
        print('❌ Missing org or status')
        return

    et = EntityType.objects.filter(code='FACTOR').first()
    if not et:
        print('❌ EntityType FACTOR not found')
        return

    # Transitions from current status for this org
    transitions = Transition.objects.filter(
        organization=org,
        entity_type=et,
        from_status=factor.status,
        is_active=True
    ).select_related('action','to_status').prefetch_related('allowed_posts').order_by('action__name')

    print(f'🔁 Possible transitions from {factor.status.code}: {transitions.count()}')
    for t in transitions:
        posts = list(t.allowed_posts.values_list('id','name'))
        print(f' - {t.action.code} -> {t.to_status.code} | posts={posts}')

    # Creator eligibility
    creator = factor.created_by
    if creator:
        ups = UserPost.objects.filter(user=creator, is_active=True, post__organization=org).select_related('post')
        creator_posts = set(ups.values_list('post_id', flat=True))
        print(f'👤 Creator active posts in org: {list(creator_posts)}')
        for t in transitions:
            allowed = set(t.allowed_posts.values_list('id', flat=True))
            eligible = bool(creator_posts & allowed)
            print(f'   eligible for {t.action.code}? {eligible}')
    else:
        print('👤 No creator set')

    # Any active users in allowed posts
    for t in transitions:
        allowed_posts = list(t.allowed_posts.values_list('id', flat=True))
        up_count = UserPost.objects.filter(post_id__in=allowed_posts, is_active=True).count()
        print(f'   users in allowed posts for {t.action.code}: {up_count}')


if __name__ == '__main__':
    main()


