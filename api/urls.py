from django.urls import path
from . import views

urlpatterns = [
    path('createbatch/',views.BatchCreateList.as_view()),
]
