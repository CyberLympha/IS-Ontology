"""BlogNote URL Configuration

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
from .views import (
    index,
    main,
    fz,
    pp,
    fstek,
    companies,
    members,
    terms,
    triplets,
    triplet_table,
    rep_2021_jul,
    rep_2021_aug,
    terms_to_vote,
    terms_table,
    triples_to_vote,
    eng_rate,
    exp_rate,
)

app_name = "IS_ontology"

urlpatterns = [
    path("", index, name="index"),
    path("main", main, name="main"),
    path("fz", fz, name="fz"),
    path("pp", pp, name="pp"),
    path("fstek", fstek, name="fstek"),
    path("terms", terms, name="terms"),
    path("terms/table", terms_table),
    path("rep_2021_jul", rep_2021_jul, name="rep_2021_jul"),
    path("rep_2021_aug", rep_2021_aug, name="rep_2021_aug"),
    path("triplets", triplets, name="triplets"),
    path("triplets/table", triplet_table),
    path("companies", companies, name="companies"),
    path("members", members, name="members"),
    path("exp_rate", exp_rate, name="expert_rating"),
    path("eng_rate", eng_rate, name="engineer_rating"),
    path("terms_to_vote", terms_to_vote, name="terms_to_vote"),
    path("triples_to_vote", triples_to_vote, name="triples_to_vote"),
    #     path(r'<int:year>/<int:month>/<int:day>/<slug:code>', view_NoteDetails, name='note_details'),
    #     path('InputNote',                                     view_InputNote,   name='input_note'),
    #     path('NotesList',                                     view_NotesList,   name='notes_list'),
    #     path('api', NoteAPIView.as_view()),
    #     path('api/<int:year>/<int:month>/<int:day>/<slug:code>', NoteAPIView.as_view()),
    path("information_extraction", include("IS_ontology.Ie.urls")),
    path("classifier", include("IS_ontology.Clf.urls")),
]
