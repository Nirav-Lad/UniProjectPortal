from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('set-password/', views.SetPasswordAPIView.as_view(), name='set-password'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('batches/', views.BatchCreateView.as_view(), name='batch-create'), 
    path('students/upload/', views.StudentUploadView.as_view(), name='student-upload'),
    path('students/register/', views.RegisterSingleStudentAPIView.as_view(), name='student-register'),
]
