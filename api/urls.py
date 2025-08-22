from django.urls import path
from . import views

urlpatterns = [
    # General
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('token/refresh/', views.CustomTokenRefreshView.as_view(), name='token-refresh'),
    path('logout/',views.LogoutAPIView.as_view(),name='logout'),
    path('user/register/',views.RegisterUserAPIView.as_view(),name='user-registration'),

    # Stage 1
    # [Admin]--
    path('batches/', views.BatchCreateView.as_view(), name='batch-create'),
    path('students/upload/', views.StudentUploadView.as_view(), name='student-upload'),
    path('students/register/', views.RegisterSingleStudentAPIView.as_view(), name='student-register'),
    path("admin-view/groups/", views.AdminGroupOverviewAPIView.as_view(), name="admin-group-overview"),
    path('groups/freeze/', views.FreezeGroupFormationAPIView.as_view(), name='freeze-groups'),
    path('batches/<str:batch_name>/students/', views.GetStudentsInBatchAPIView.as_view(), name='students-in-batch'),
    path('students/<int:enrollment_id>/', views.GetSingleStudentAPIView.as_view(), name='student-detail'),
    path('students/list/',views.AdminStudentListView.as_view(),name='list-students'),
    # [Student]--
    path('setup-student/', views.SetupStudentAPIView.as_view(), name='setup-student'),
    path('get-enrollids/', views.BatchEnrollmentIDsAPIView.as_view(), name='enrollmentids-students'),
    path('register-group/',views.RegisterGroupAPIView.as_view(),name='register-group'),
    path('ideas/submit/', views.IdeaSubmissionAPIView.as_view(), name='submit-idea'),
    path('ideas/check/',views.CheckIdeaSubmissionAPIView.as_view(),name='check-ideasubmission'),
    path('ideas/update/',views.UpdateIdeaAPIView.as_view(),name='update-idea'),
    path('ideas/reset/',views.IdeaResetAPIView.as_view(),name='reset-idea'),
    path('students/profile/', views.GetStudentProfileAPIView.as_view(), name='student-profile'),
    path("groups/my-group/", views.StudentGroupDetailsAPIView.as_view(), name="student-group-details"),
    
    # Stage 2
    # [Admin]--
    path('guide/register/single/',views.RegisterSingleGuideAPIView.as_view(),name='register-guide-single'),
    # [Guide]--
    path('guide/firstlogin/',views.GuideFirstLoginAPIView.as_view(),name='guide-firstlogin'),
    path('guide/priorities/',views.GuidePriorityAPIView.as_view(),name='guide-priorities'),
    # [Student]--

    # Stage 3
    ]
