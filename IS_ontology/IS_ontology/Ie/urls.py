"""
urls.py

Определяет маршруты URL для приложения 'Ie'.

Маршруты:
    - '' (views.IndexView) — главная страница для работы с сущностями.
    - 'graph' (views.graph) — отображение графа сущностей и триплетов.
    - 'add' (views.AddView) — добавление новых триплетов.
    - 'predicates' (views.PredicateView) — добавление и поиск предикатов.
    - 'build_graph' (views.build_graph) — API для построения графа в формате JSON.

Примечание:
    Все маршруты имеют пространство имён 'Ie' (app_name='Ie') для использования в шаблонах.
"""


from django.urls import path

from . import views


app_name = 'Ie'

urlpatterns = [
    path('', views.IndexView.as_view(), name='ie'), # Главная страница: работа с сущностями
    path('graph', views.graph, name='graph'), # Отображение графа сущностей
    path('add', views.AddView.as_view(), name='add'), # Страница добавления триплетов
    path('predicates', views.PredicateView.as_view(), name='predicates'), # Работа с предикатами
    path('build_graph', views.build_graph) # API-эндпоинт для получения графа в JSON
]
