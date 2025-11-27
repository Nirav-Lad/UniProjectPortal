from django.urls import path
from api.views import stage1_views

urlpatterns = [
    # General
    path('login/', stage1_views.LoginAPIView.as_view(), name='login'),
    path('token/refresh/', stage1_views.CustomTokenRefreshView.as_view(), name='token-refresh'),
    path('logout/',stage1_views.LogoutAPIView.as_view(),name='logout'),
    path('user/register/',stage1_views.RegisterUserAPIView.as_view(),name='user-registration'),

    # Stage 1
    # [Admin]--
    path('batches/', stage1_views.BatchCreateView.as_view(), name='batch-create'),
    path("batches/<str:batch_name>/", stage1_views.BatchDetailAPI.as_view(), name="batch-detail"),
    path('students/upload/', stage1_views.StudentUploadView.as_view(), name='student-upload'),
    path('students/register/', stage1_views.RegisterSingleStudentAPIView.as_view(), name='student-register'),
    path("admin-view/groups/", stage1_views.AdminGroupOverviewAPIView.as_view(), name="admin-group-overview"),
    path('groups/freeze/', stage1_views.FreezeGroupFormationAPIView.as_view(), name='freeze-groups'),
    path('batches/<str:batch_name>/students/', stage1_views.GetStudentsInBatchAPIView.as_view(), name='students-in-batch'),
    path('students/<int:enrollment_id>/', stage1_views.GetSingleStudentAPIView.as_view(), name='student-detail'),
    path('students/list/',stage1_views.AdminStudentListView.as_view(),name='list-students'),
    # [Student]--
    path('setup-student/', stage1_views.SetupStudentAPIView.as_view(), name='setup-student'),
    path('get-enrollids/', stage1_views.BatchEnrollmentIDsAPIView.as_view(), name='enrollmentids-students'),
    path('register-group/',stage1_views.RegisterGroupAPIView.as_view(),name='register-group'),
    path('ideas/submit/', stage1_views.IdeaSubmissionAPIView.as_view(), name='submit-idea'),
    path('ideas/check/',stage1_views.CheckIdeaSubmissionAPIView.as_view(),name='check-ideasubmission'),
    path('ideas/update/',stage1_views.UpdateIdeaAPIView.as_view(),name='update-idea'),
    path('ideas/reset/',stage1_views.IdeaResetAPIView.as_view(),name='reset-idea'),
    path('students/profile/', stage1_views.GetStudentProfileAPIView.as_view(), name='student-profile'),
    path("groups/my-group/", stage1_views.StudentGroupDetailsAPIView.as_view(), name="student-group-details"),
]