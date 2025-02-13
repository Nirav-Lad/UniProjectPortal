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
    path('update-student-details/', views.UpdateStudentDetailsView.as_view(), name='update_student_details'),
    path('batches/<str:batch_name>/students/', views.GetStudentsInBatchAPIView.as_view(), name='students-in-batch'),
    path('students/profile/', views.GetStudentProfileAPIView.as_view(), name='student-profile'),
    path('students/<int:enrollment_id>/', views.GetSingleStudentAPIView.as_view(), name='student-detail'),
    path('groups/available/', views.AvailableGroupsAPIView.as_view(), name='available-groups'),
    path('groups/join/', views.JoinGroupAPIView.as_view(), name='join-group'),
    path('ideas/submit/', views.IdeaSubmissionAPIView.as_view(), name='submit-idea'),
    path('groups/freeze/', views.FreezeGroupFormationAPIView.as_view(), name='freeze-groups'),
]
