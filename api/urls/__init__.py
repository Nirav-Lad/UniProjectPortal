# api/urls/__init__.py
from django.urls import path, include

urlpatterns = [
    path("", include("api.urls.stage1_urls")),
    path("", include("api.urls.stage2_urls")),
    path("", include("api.urls.stage3_urls")),
    path("", include("api.urls.stage4_urls")),
    path("", include("api.urls.stage5_urls")),
]
