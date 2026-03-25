from django.urls import path
from api.views import stage5_views

urlpatterns = [
    path("submissions/",stage5_views.SubmissionWindowAPIView.as_view(),name="submissions"),
    path("submissions/<int:id>/toggle",stage5_views.SubmissionWindowToggleAPIView.as_view(),name="submissions toggle"),
]