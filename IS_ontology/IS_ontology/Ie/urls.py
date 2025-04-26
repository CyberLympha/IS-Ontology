from django.urls import path

from . import views

print("Мой Ie/urls.py загружен") #отладка

app_name = 'Ie'

from django.http import HttpResponse

def test_add_view(request):
    return HttpResponse("✅ Работает AddView") #отладка

urlpatterns = [
    path('', views.IndexView.as_view(), name='ie'),
    path('graph', views.graph, name='graph'),
    # path('add', views.AddView.as_view(), name='add'),
    path('add', test_add_view), #отладка
    path('predicates', views.PredicateView.as_view(), name='predicates'),
    path('build_graph', views.build_graph)
]
