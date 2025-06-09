from django.views import View
from django.http import JsonResponse
from tankhah.models import Tankhah
from core.PermissionBase import PermissionBaseView

import logging
logger = logging.getLogger('FactorUnlockView')

class ProcessApprovedFactorsView(PermissionBaseView, View):
    permission_required = 'tankhah.factor_approve'

    def post(self, request, tankhah_id):
        try:
            tankhah = Tankhah.objects.get(id=tankhah_id)

            count = tankhah.process_approved_factors(request.user)
            return JsonResponse({
                'success': True,
                'message': f'{count} فاکتور تأییدشده پردازش شدند.'
            })
        except Tankhah.DoesNotExist:
            return JsonResponse({'error': 'تنخواه یافت نشد.'}, status=404)
        except Exception as e:
            logger.error(f"Error processing factors for tankhah {tankhah_id}: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)