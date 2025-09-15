from django.urls import path,include
from api.urls import *

urlpatterns = [
    path("", include("api.urls.__init__")), 
]
