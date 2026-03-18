from django.urls import path
from api.views import stage5_views

urlpatterns = [
#    SUBMISSION:
#     POST   /submissions/
#     GET    /submissions/
#     POST   /submissions/{id}/toggle/
#     DELETE /submissions/{id}/

#     DOCUMENT:
#     POST   /documents/
#     GET    /documents/
#     GET    /documents/history/
#     POST   /documents/{id}/review/
#     GET    /documents/{id}/download/

#     HARDCOPY:
#     POST   /hardcopy/request/
#     POST   /hardcopy/submit/
#     POST   /hardcopy/verify/

    path('/submissions')
]
