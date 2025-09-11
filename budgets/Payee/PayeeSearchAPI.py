from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from budgets.models import Payee
class PayeeSearchAPI(APIView):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        payees = Payee.objects.filter(
            Q(name__icontains=query) |
            Q(family__icontains=query) |
            Q(legal_name__icontains=query) |
            Q(national_id__icontains=query)
        ).values('id', 'name', 'family', 'legal_name', 'national_id', 'entity_type')[:10]
        return Response(list(payees), status=status.HTTP_200_OK)