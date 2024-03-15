from django.urls import path

from . import views


app_name = 'Ie'

urlpatterns = [
    path('', views.IndexView.as_view(), name='ie'),
    path('graph', views.graph, name='graph'),
    path('add', views.AddView.as_view(), name='add'),
    path('predicates', views.PredicateView.as_view(), name='predicates'),
    path('build_graph', views.build_graph)
]
