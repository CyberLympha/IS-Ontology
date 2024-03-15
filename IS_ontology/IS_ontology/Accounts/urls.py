"""Accounts URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.contrib.auth import views as auth_views

from IS_ontology.Notes.views import view_NotesList
from IS_ontology.Accounts.views import view_Register

urlpatterns = [
    path(r'login/',                auth_views.LoginView.as_view(),              name='login'),
    path(r'logout/',               auth_views.LogoutView.as_view(),             name='logout'),
    path(r'password_change/',      auth_views.PasswordChangeView.as_view(),     name='password_change'),
    path(r'password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path(r'password_change/',      auth_views.PasswordChangeView.as_view(),     name='password_change'),
    path(r'register/',             view_Register,                               name='register'),
    path('',                       view_NotesList,                              name='notes_list'),
]



