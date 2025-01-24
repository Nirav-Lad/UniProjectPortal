from django.urls import path
from .views import LoginAPIView,BatchcreateView,StudentUploadView,RegisterStudent
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('create-batch/',BatchcreateView.as_view(),name='create-batch'), 
    path('upload-students/', StudentUploadView.as_view(), name='upload_students'),
    path('register_student/',RegisterStudent.as_view(),name='registerstudent'),
]
