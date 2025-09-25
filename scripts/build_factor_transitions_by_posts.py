#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
    import django
    django.setup()

    from django.db import transaction
    from core.models import Transition, Status, Action, EntityType, Organization, Post

    org_scope = None
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        org_scope = int(sys.argv[1])
        print(f'⚙️ Building for organization_id={org_scope}')

    et = EntityType.objects.filter(code='FACTOR').first()
    if not et:
        print('❌ EntityType FACTOR not found')
        return

    # statuses
    draft = Status.objects.filter(code='DRAFT', is_active=True).first()
    inter = Status.objects.filter(code__in=['PENDING_APPROVAL','APPROVED_INTERMEDIATE','IN_REVIEW'], is_active=True).order_by('id').first()
    final = Status.objects.filter(code='APPROVED_FINAL', is_active=True).first()
    rejected = Status.objects.filter(code='REJECTED', is_active=True).first()
    if not (draft and inter and final):
        print('❌ Required statuses (DRAFT, intermediate, APPROVED_FINAL) not found')
        return

    # actions
    submit = Action.objects.filter(code__in=['SUBMIT','SEND']).order_by('id').first() or Action.objects.create(name='ارسال', code='SUBMIT', is_active=True)
    approve = Action.objects.filter(code__in=['APPROVE']).first() or Action.objects.create(name='تأیید', code='APPROVE', is_active=True)
    final_approve = Action.objects.filter(code__in=['FINAL_APPROVE']).first() or Action.objects.create(name='تأیید نهایی', code='FINAL_APPROVE', is_active=True)

    # organizations
    orgs = Organization.objects.filter(is_active=True)
    if org_scope:
        orgs = orgs.filter(id=org_scope)

    created_count = 0

    with transaction.atomic():
        for org in orgs:
            # Branch vs HQ
            if org.is_core:
                # HQ flow: all HQ posts can approve up to final approver (post.can_final_approve_factor)
                hq_posts = Post.objects.filter(organization=org, is_active=True).order_by('level')
                # Ensure DRAFT->inter submit allowed by all HQ posts (optional) but typically submit is branch action
                # We skip submit at HQ
                # Intermediate approvals up chain (non-final approves)
                for p in hq_posts.filter(can_final_approve_factor=False):
                    tr, created = Transition.objects.get_or_create(
                        organization=org, entity_type=et, from_status=inter, action=approve,
                        defaults={'to_status': inter, 'is_active': True}
                    )
                    # keep to_status as inter to model repeated approvals; UI will display action; status remains until final
                    tr.allowed_posts.add(p.id)
                    if created:
                        created_count += 1
                # Final approvers
                for p in hq_posts.filter(can_final_approve_factor=True):
                    tr, created = Transition.objects.get_or_create(
                        organization=org, entity_type=et, from_status=inter, action=final_approve,
                        defaults={'to_status': final, 'is_active': True}
                    )
                    tr.allowed_posts.add(p.id)
                    if created:
                        created_count += 1
            else:
                # Branch flow: all branch posts approve up to first core (HQ) post. Model as DRAFT->inter (submit) and inter approvals by branch posts.
                branch_posts = Post.objects.filter(organization=org, is_active=True).order_by('level')
                # Submit from DRAFT by any branch post
                tr, created = Transition.objects.get_or_create(
                    organization=org, entity_type=et, from_status=draft, action=submit,
                    defaults={'to_status': inter, 'is_active': True}
                )
                if created:
                    created_count += 1
                tr.allowed_posts.add(*branch_posts.values_list('id', flat=True))

                # Intermediate branch approvals keep status at inter until escalated to HQ (not modeled explicitly here)
                for p in branch_posts:
                    tr2, created2 = Transition.objects.get_or_create(
                        organization=org, entity_type=et, from_status=inter, action=approve,
                        defaults={'to_status': inter, 'is_active': True}
                    )
                    tr2.allowed_posts.add(p.id)
                    if created2:
                        created_count += 1

        print(f'✅ Build complete. New transitions created: {created_count}')


if __name__ == '__main__':
    main()


