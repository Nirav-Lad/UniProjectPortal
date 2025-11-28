from django.urls import path
from api.views import stage3_views

urlpatterns = [
    path('create_log/',stage3_views.MeetingLogCreateView.as_view(),name='create_meeting_log'),
    path('get_logs/',stage3_views.MeetingLogListView.as_view(),name='get_meeting_logs'),
    path('approve_log/',stage3_views.MeetingLogApproveView.as_view(),name='approve_meeting_log'),
    path('groups_list/',stage3_views.GroupListView.as_view(),name='get_groups_list_under_a_guide'),
]
