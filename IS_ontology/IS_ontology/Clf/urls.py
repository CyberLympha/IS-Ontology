from django.urls import path

from . import views


app_name = 'Clf'


urlpatterns = [
    path('', views.index, name='clf'),
]
