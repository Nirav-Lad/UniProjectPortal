from django.urls import path
from api.views import stage2_views

urlpatterns = [
    # Stage 2
    # [Admin]--
    path('guide/register/single/',stage2_views.RegisterSingleGuideAPIView.as_view(),name='register-guide-single'),
    # path('guide/suggestions/',views.GuideSuggestionAPIView.as_view(),name='guide-suggestions-for-admin'),
    # [Guide]--
    path('guide/firstlogin/',stage2_views.GuideFirstLoginAPIView.as_view(),name='guide-firstlogin'),
    path('guide/priorities/',stage2_views.GuidePriorityAPIView.as_view(),name='guide-priorities'),
    # [Student]--   
]