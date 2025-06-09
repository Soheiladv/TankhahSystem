# # views.py
# from django.http import JsonResponse
# from django.shortcuts import get_object_or_404
# from django.views.generic import ListView, CreateView, UpdateView, DeleteView
# from django.urls import reverse_lazy
# from django.contrib.auth.mixins import LoginRequiredMixin
#
# from tankhah.models import Notification
#
#
# class NotificationListView(LoginRequiredMixin, ListView):
#     model = Notification
#     template_name = 'tankhah/notifications/notification_list.html'
#     context_object_name = 'notifications'
#
#     def get_queryset(self):
#         return Notification.objects.filter(user=self.request.user).order_by('-created_at')
#
#
# class NotificationCreateView(LoginRequiredMixin, CreateView):
#     model = Notification
#     fields = ['message', 'tankhah']
#     template_name = 'tankhah/notifications/notification_form.html'
#     success_url = reverse_lazy('notification_list')
#
#     def form_valid(self, form):
#         form.instance.user = self.request.user
#         return super().form_valid(form)
#
#
# class NotificationUpdateView(LoginRequiredMixin, UpdateView):
#     model = Notification
#     fields = ['message', 'tankhah', 'is_read']
#     template_name = 'tankhah/notifications/notification_form.html'
#     success_url = reverse_lazy('notification_list')
#
#
# class NotificationDeleteView(LoginRequiredMixin, DeleteView):
#     model = Notification
#     template_name = 'tankhah/notifications/notification_confirm_delete.html'
#     success_url = reverse_lazy('notification_list')
#
# #
# # def mark_notification_as_read(request, pk):
# #     notification = get_object_or_404(Notification, pk=pk, user=request.user)
# #     notification.is_read = True
# #     notification.save()
# #     return JsonResponse({'status': 'success'})