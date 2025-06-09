from django.views import View
from django.http import JsonResponse

from core.PermissionBase import PermissionBaseView
from tankhah.models import Factor

import logging
logger = logging.getLogger('FactorUnlockView')


class FactorUnlockView(PermissionBaseView, View):
    permission_required = 'tankhah.factor_unlock'

    def post(self, request, factor_id):
        try:
            factor = Factor.objects.get(id=factor_id)

            factor.unlock(request.user)
            return JsonResponse({'success': True, 'message': f'فاکتور {factor.number} باز شد.'})
        except Factor.DoesNotExist:
            return JsonResponse({'error': 'فاکتور یافت نشد.'}, status=404)
        except Exception as e:
            logger.error(f"Error unlocking factor {factor_id}: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)