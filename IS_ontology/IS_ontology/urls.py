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
    path('api_docs/', get_schema_view("IS_ontology", patterns=api_patterns)),
    path("clf/", include("IS_ontology.Clf.urls", namespace="Clf")),
    path("components/", include("components.urls")),
    path("ie/", include("IS_ontology.Ie.urls", namespace="Ie")),
    path("", include("IS_ontology.Notes.urls", namespace="Notes")),
    path("__debug__/", include("debug_toolbar.urls")),
]

if settings.DEBUG:
    urlpatterns+= static('/static')
