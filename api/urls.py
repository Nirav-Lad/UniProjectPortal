from django.urls import path
from .views import LoginAPIView,BatchcreateView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('create-batch/',BatchcreateView.as_view(),name='create-batch'), 
]
