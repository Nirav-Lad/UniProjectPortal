from django.urls import path
from api.views import stage2_views

urlpatterns = [
    # Stage 2
    # [Admin]--
    path('guide/register/single/',stage2_views.RegisterSingleGuideAPIView.as_view(),name='register-guide-single'),
    path("batches/<str:batch_name>/get-priorities/", stage2_views.AdminBatchWiseGuidePriorityAPIView.as_view()),
    path("guide-assignment/", stage2_views.AdminAssignFinalGuideAPIView.as_view()),

    # [Guide]--
    path('guide/firstlogin/',stage2_views.GuideFirstLoginAPIView.as_view(),name='guide-firstlogin'),
    path('guide/priorities/',stage2_views.GuidePriorityAPIView.as_view(),name='guide-priorities'),
    path("guide/my-groups/", stage2_views.GuideDashboardAPIView.as_view()),
    path("guide/finalize-idea/", stage2_views.GuideFinalizeIdeaAPIView.as_view()),

    # [Student]--   
    path("student/project-details/",stage2_views.StudentGroupDashboardAPIView.as_view()),
]