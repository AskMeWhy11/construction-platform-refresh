from django.urls import path

from . import views

app_name = "calc"

urlpatterns = [
    path("", views.index, name="index"),
    path("history/", views.history, name="history"),
    path("api/classes/<int:purpose_id>/", views.classes_for_purpose, name="classes_for_purpose"),
    path("api/classes/<int:purpose_id>/", views.classes_for_purpose, name="classes_for_purpose"),
    path("api/purpose-meta/<int:purpose_id>/", views.purpose_meta, name="purpose_meta"),
]