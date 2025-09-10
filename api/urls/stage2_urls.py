from django.urls import path
from . import views

urlpatterns = [
    # Stage 2
    # [Admin]--
    path('guide/register/single/',views.RegisterSingleGuideAPIView.as_view(),name='register-guide-single'),
    # path('guide/suggestions/',views.GuideSuggestionAPIView.as_view(),name='guide-suggestions-for-admin'),
    # [Guide]--
    path('guide/firstlogin/',views.GuideFirstLoginAPIView.as_view(),name='guide-firstlogin'),
    path('guide/priorities/',views.GuidePriorityAPIView.as_view(),name='guide-priorities'),
    # [Student]--   
]