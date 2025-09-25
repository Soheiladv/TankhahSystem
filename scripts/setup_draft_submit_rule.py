#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
    import django
    django.setup()

    from django.db import transaction
    from django.contrib.auth import get_user_model
    from core.models import Transition, Status, Action, EntityType, Organization, Post, UserPost
    from tankhah.models import Factor

    User = get_user_model()

    factor_id = int(sys.argv[1]) if len(sys.argv) > 1 else 77

    try:
        factor = Factor.objects.select_related('tankhah__organization', 'created_by', 'status').get(id=factor_id)
    except Factor.DoesNotExist:
        print(f'❌ Factor id={factor_id} not found')
        sys.exit(1)

    if not getattr(factor, 'tankhah', None) or not getattr(factor.tankhah, 'organization', None):
        print('❌ Factor has no organization via tankhah')
        sys.exit(1)

    org = factor.tankhah.organization
    creator = factor.created_by
    print(f'✅ Factor: {factor.number} | org={org.name} | status={getattr(factor.status, "code", None)} | creator={getattr(creator, "username", None)}')

    # Resolve statuses
    draft = Status.objects.filter(code='DRAFT', is_active=True).first()
    pending = Status.objects.filter(code__in=['PENDING_APPROVAL', 'SUBMITTED', 'IN_REVIEW'], is_active=True).order_by('id').first()
    if not draft:
        print('❌ DRAFT status not found')
        sys.exit(1)
    if not pending:
        print('❌ Next status (PENDING_APPROVAL/SUBMITTED/IN_REVIEW) not found')
        sys.exit(1)

    # Entity type
    et = EntityType.objects.filter(code='FACTOR').first()
    if not et:
        print('❌ EntityType FACTOR not found')
        sys.exit(1)

    # Action (create or reuse)
    action = Action.objects.filter(code__in=['SUBMIT', 'SEND', 'REGISTER']).order_by('id').first()
    if not action:
        action = Action.objects.create(name='ارسال', code='SUBMIT', is_active=True)
        print(f'ℹ️ Created Action: {action.name} ({action.code})')
    else:
        print(f'ℹ️ Using Action: {action.name} ({action.code})')

    # Find or create transition
    with transaction.atomic():
        # Respect unique_together: (organization, entity_type, from_status, action)
        tr = Transition.objects.filter(
            organization=org,
            entity_type=et,
            from_status=draft,
            action=action,
            is_active=True,
        ).select_related('to_status').first()
        created = False
        if not tr:
            tr = Transition.objects.create(
                from_status=draft,
                to_status=pending,
                action=action,
                entity_type=et,
                organization=org,
                is_active=True,
            )
            created = True
            print(f'✅ Created Transition ID={tr.id} {draft.code} -> {pending.code} ({action.code}) @ {org.name}')
        else:
            if not tr.is_active:
                tr.is_active = True
                tr.save(update_fields=['is_active'])
            print(f'ℹ️ Using existing Transition ID={tr.id} {draft.code} -> {tr.to_status.code} ({action.code}) @ {org.name}')

        # Assign creator posts as allowed_posts
        if creator:
            creator_posts = UserPost.objects.filter(user=creator, is_active=True, post__organization=org).select_related('post')
            post_ids = list(creator_posts.values_list('post_id', flat=True))
            if not post_ids:
                print(f'⚠️ Creator user has no active Post in org: {org.name}. No posts added.')
            else:
                before = set(tr.allowed_posts.values_list('id', flat=True))
                tr.allowed_posts.add(*post_ids)
                after = set(tr.allowed_posts.values_list('id', flat=True))
                added = after - before
                print(f'✅ Allowed posts updated. Added {len(added)} post(s): {list(added)}')
        else:
            print('⚠️ Factor has no creator; skipped allowed_posts assignment')

    print('🎯 Done')


if __name__ == '__main__':
    main()


