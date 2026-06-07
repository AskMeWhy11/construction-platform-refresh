from django.urls import path

from . import views

app_name = "calc"

urlpatterns = [
    path("", views.index, name="index"),
    path("history/", views.history, name="history"),
    path("api/classes/<int:purpose_id>/", views.classes_for_purpose, name="classes_for_purpose"),
]