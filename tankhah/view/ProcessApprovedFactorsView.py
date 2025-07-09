from django.shortcuts import get_object_or_404
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from tankhah.models import Tankhah
from core.PermissionBase import PermissionBaseView
import logging

logger = logging.getLogger(' ProcessApprovedFactorsView ')

class ProcessApprovedFactorsView(PermissionBaseView, View):
    permission_codenames = ['tankhah.can_process_factors']

    def post(self, request, pk):
        tankhah = get_object_or_404(Tankhah, pk=pk)
        try:
            processed_count = tankhah.process_approved_factors(user=request.user)
            messages.success(request, f"{processed_count} فاکتور با موفقیت پردازش و دستور پرداخت‌های مربوطه صادر شد.")
        except Exception as e:
            logger.error(f"Error processing factors for Tankhah {pk}: {e}", exc_info=True)
            messages.error(request, f"خطا در پردازش فاکتورها: {e}")
        return redirect('tankhah_detail', pk=tankhah.pk)