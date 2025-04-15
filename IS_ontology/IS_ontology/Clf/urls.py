from django.contrib import admin 
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path, include
from rest_framework.schemas import get_schema_view

api_patterns = [
    path("api/", include("IS_ontology.api.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls), 
    path("accounts/", include("IS_ontology.Accounts.urls")),
    api_patterns[0],
    ...
]
