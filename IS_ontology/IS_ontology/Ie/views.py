from typing import Any, Dict

from django.http import JsonResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView
from ..Notes import models as nm
from .database import execute_read
from . import graph_repositories as gr
from .ai_utils import (
    get_marked_ents,
    generate_sent_form,
    filter_ents,
    get_parsed_html,
    get_ents,
    crf,
)

from nltk.tokenize import sent_tokenize


"""
views.py

Определяет представления (views) для приложения 'Ie'.

Содержит:
    - IndexView: Страница работы с сущностями, добавление новых сущностей в базу.
    - AddView: Страница добавления триплетов на основе сущностей.
    - PredicateView: Страница добавления и поиска предикатов.
    - graph: Отображение графа сущностей и триплетов.
    - build_graph_object: Построение объекта графа для отображения.
    - build_graph: API-эндпоинт для получения графа в формате JSON.

Особенности:
    Используется обработка POST-запросов для работы с данными пользователя.
    Хранение состояния для разных пользователей с помощью словарей last_for_ents и last_for_triples.
"""


last_for_triples = {}
"""
Глобальный словарь для хранения промежуточных данных триплетов.

Ключи:
    Пользователи (request.user).

Значения:
    Списки с данными о текущем состоянии обработки триплетов:
        - индекс предложения,
        - список предложений,
        - список сущностей,
        - ссылка на источник.
"""


class TemplatePostViewMixin:
    """
    Миксин для упрощения обработки POST-запросов в шаблонных представлениях.

    Особенности:
        - Переопределяет метод post().
        - Возвращает рендеринг страницы с текущим контекстом данных.
    """
    def post(self, request, *args, **kwargs):
        """
        Обрабатывает POST-запрос и возвращает страницу с обновлённым контекстом.

        Args:
            request (HttpRequest): Объект запроса.
            *args: Позиционные аргументы.
            **kwargs: Именованные аргументы.

        Returns:
            HttpResponse: Сформированный ответ для пользователя.
        """
        return super(TemplateView, self).render_to_response(
            self.get_context_data(**kwargs)
        )


class IndexView(TemplateView, TemplatePostViewMixin):
    """
    Представление главной страницы работы с сущностями.

    Отвечает за:
        - Загрузку текста статьи.
        - Разметку сущностей в тексте.
        - Добавление новых сущностей в базу данных.
        - Навигацию по предложениям статьи.

    Атрибуты:
        template_name (str): Путь к HTML-шаблону страницы.
        last_for_ents (dict): Словарь для хранения состояния обработки текста для каждого пользователя.

    Методы:
        get_context_data: Формирует контекст данных для отображения страницы.
        process_get: Обработка GET-запроса (отображение текущего состояния).
        process_post: Обработка POST-запроса (добавление сущностей, переход между предложениями).
    """
    
    template_name = "ie.html"
    last_for_ents: dict[Any, list] = {}
    """
     Словарь состояния сущностей для каждого пользователя:
        {пользователь: [индекс предложения, список предложений, список сущностей, ссылка на источник]}
    """

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Формирует контекст данных для рендеринга главной страницы.

        Включает:
            - Список доступных источников (описания статей).
            - Текущее состояние обработки предложения и сущностей.
            - Видимость кнопок "Следующее" и "Предыдущее" для навигации.

        Возвращает:
            dict: Словарь данных для передачи в шаблон.
        """

        # Получаем список всех доступных источников (url и описание)
        context = super().get_context_data(**kwargs)
        context["descriptions"] = [
            [i["n.url"], i["n.description"]]
            for i in gr.SourceRepository.get_descriptions()
        ]

        # Вызываем соответствующий обработчик в зависимости от метода запроса
        if self.request.method == "GET":
            context |= self.process_get()
        elif self.request.method == "POST":
            context |= self.process_post()

        # Контроль отображения кнопок "следующее" и "предыдущее"
        context["show_next"] = (
            context["sent_index"] < context["sent_len"]
            if "sent_index" in context.keys()
            else True
        )
        context["show_previous"] = (
            context["sent_index"] > 0 if "sent_index" in context.keys() else True
        )
        return context

    def process_get(self) -> Dict[str, Any]:
        """
        Обрабатывает GET-запрос для отображения текущего состояния работы с сущностями.

        Выполняет:
            - Загрузку текста предложения.
            - Разметку уже добавленных сущностей.
            - Фильтрацию сущностей, которые ещё не были добавлены.

        Возвращает:
            dict: Данные для отображения предложения и сущностей в шаблоне.
        """
        result = {
            "show": True,
        }
        # views.py:50

        # Проверяем, есть ли сохранённое состояние для пользователя
        if self.request.user not in self.last_for_ents.keys():
            return result

        # Извлекаем последнее состояние
        sent_index, sents, ents, description = self.last_for_ents[self.request.user]

        # Получаем источник и формируем текущее предложение
        #source = nm.Source.objects.get(description=description)
        source = gr.SourceRepository.get_by_url(description)
        sent_form = generate_sent_form(sent_index, sents, ents)

        # Отмечаем сущности, которые уже добавлены, и фильтруем их
        marked_ents = get_marked_ents(sent_index, sents, source)
        ents = filter_ents(marked_ents, sent_form[1])

        result |= {
            "sentence": sent_form[0],
            "ents": list(enumerate(ents)),
            "sent_index": sent_index,
            "sent_len": len(sents),
            "show_table": True,
            "ents_in_sent": marked_ents,
        }

        return result

    def process_post(self):
        """
        Обрабатывает POST-запрос для действий пользователя на главной странице.

        Возможные действия:
            - Загрузка текста статьи и сущностей из базы данных.
            - Добавление новых отмеченных сущностей в базу данных.
            - Переход к следующему или предыдущему предложению.

        Возвращает:
            dict: Обновлённый контекст для отображения страницы.
        """
        result = {"show": True, "show_table": True}

        # Пользователь выбрал источник из базы данных
        if "descriptions" in self.request.POST:
            result["source"] = self.request.POST.get("descriptions")

        # Получение текста и сущностей из выбранного источника
        if "get_from_base" in self.request.POST:
            source = gr.SourceRepository.get_by_url(result["source"])

            last_text = get_parsed_html(source.url)
            ents = get_ents(source.url, crf)
            sent_index = 0
            sents = sent_tokenize(last_text, language="russian")

            # Сохраняем состояние для пользователя
            self.last_for_ents[self.request.user] = [
                sent_index,
                sents,
                ents,
                source.url,
            ]

            # Формируем данные для текущего предложения
            sent_form = generate_sent_form(sent_index, sents, ents)
            marked_ents = get_marked_ents(sent_index, sents, source)
            ents = filter_ents(marked_ents, sent_form[1])

            result |= {
                "sentence": sent_form[0],
                "ents": list(enumerate(ents)),
                "sent_index": sent_index,
                "sent_len": len(sents),
                "ents_in_sent": marked_ents,
            }

        # Пользователь отметил сущности и хочет их добавить    
        elif "add_ents" in self.request.POST:
            sent_index, sents, ents, description = self.last_for_ents[self.request.user]
            sent_form = generate_sent_form(sent_index, sents, ents)

            source = gr.SourceRepository.get_by_url(description)
            marked_ents = get_marked_ents(sent_index, sents, source)
            ents = filter_ents(marked_ents, sent_form[1])

            # Проверка отмеченных сущностей
            applyed_ents = [self.request.POST.get(str(i)) for i in range(len(ents))]

            if any(applyed_ents):
                for i, ae in enumerate(applyed_ents):
                    if ae == "on":
                        gr.EntityRepository.create(
                            ents[i], source, sent_form[0], self.request.user.pk
                        )
                        # ent, created = nm.Entity.objects.get_or_create(
                        #     ent=ents[i],
                        #     source=source,
                        #     source_sentence=sent_form[0],
                        #     expert=self.request.user,
                        # )
                        # if created:
                        #     ent.save()
                        #     nm.EntScore(
                        #         ent=ent, expert=self.request.user, score=True
                        #     ).save()
                result["verdict"] = "Новые сущности внесены в базу"
            else:
                result["verdict"] = "Сущности не были отмечены"
            result |= {
                "sentence": sent_form[0],
                "ents": list(enumerate(ents)),
                "sent_index": sent_index,
                "sent_len": len(sents),
                "ents_in_sent": marked_ents,
            }
        
        # Навигация по предложениям
        elif "next" in self.request.POST or "previous" in self.request.POST:
            sent_index, sents, ents, description = self.last_for_ents[self.request.user]
            source = gr.SourceRepository.get_by_url(description)

            # Смещаем индекс в зависимости от действия
            sent_index += 1 if "next" in self.request.POST else -1
            if sent_index < 0 or sent_index >= len(sents):
                return result

            # Обновляем индекс предложения
            self.last_for_ents[self.request.user][0] = sent_index
            sent_form = generate_sent_form(sent_index, sents, ents)
            marked_ents = get_marked_ents(sent_index, sents, source)
            ents = filter_ents(marked_ents, sent_form[1])
            result |= {
                "sentence": sent_form[0],
                "ents": list(enumerate(ents)),
                "sent_index": sent_index,
                "sent_len": len(sents),
                "ents_in_sent": marked_ents,
            }

        return result


def graph(request):
    """
    Представление для отображения графа сущностей и триплетов.

    Формирует контекст страницы:
        - Генерирует объект графа через функцию build_graph_object().
        - Безопасно вставляет объект графа в HTML через mark_safe.

    Args:
        request (HttpRequest): HTTP-запрос пользователя.

    Returns:
        HttpResponse: Сформированная страница с графом.
    """
    context = {}

    # Генерируем объект графа и делаем его безопасным для вставки в HTML
    context["graph_obj"] = mark_safe(str(build_graph_object()))

    # Отрисовываем страницу "graph.html" с переданным контекстом
    return render(request, "graph.html", context)


def build_graph_object():
    """
    Построение объекта графа сущностей и триплетов.

    Выполняет запрос к базе данных:
        - Извлекает все сущности и триплеты между ними.
        - Формирует словарь с узлами (nodes) и связями (links) для визуализации графа.

    Структура графа:
        - Узлы (nodes): сущности и предикаты (триплеты).
        - Связи (links): связи между сущностями и триплетами.

    Returns:
        dict: Объект графа с узлами и связями, готовый для передачи в шаблон.
    """

    # Выполняем Cypher-запрос: получаем все сущности и триплеты между ними
    result = execute_read(
        lambda tx: tx.run(
            "MATCH (sub: Entity)-->(pred: Triple)-->(obj: Entity) return sub, pred, obj"
        ).values()
    )

    # Инициализируем структуру графа
    graph_obj = {"nodes": {}, "links": []}

    _id = 0 # Счётчик для уникальных идентификаторов предикатов

    # Проходим по всем триплетам
    for sub, pred, obj in result:

        # Добавляем сущности (sub и obj) как узлы типа "term"
        for i in [sub, obj]:
            graph_obj["nodes"][i["name"]] = {
                "id": i["name"],
                "name": i["name"],
                "expert": i["user"],
                "type": "term",
            }

        # Добавляем предикат (pred) как отдельный узел типа "rel"
        pred_id = pred.get("name") + str(_id)  # Делаем уникальный id для каждого предиката
        graph_obj["nodes"][pred_id] = {
            "id": pred_id,
            "type": "rel",
            "name": pred.get("name"),
        }

        # Создаём связи: субъект -> предикат и предикат -> объект
        graph_obj["links"].append({"source": sub["name"], "target": pred_id})
        graph_obj["links"].append({"source": pred_id, "target": obj["name"]})

        _id += 1 # Увеличиваем счётчик для следующего предиката

    # Преобразуем словарь узлов в список
    graph_obj["nodes"] = list(graph_obj["nodes"].values())

    return graph_obj


def build_graph(request):
    """
    API-представление для получения графа сущностей и триплетов в формате JSON.

    Выполняет:
        - Построение объекта графа через функцию build_graph_object().
        - Возвращает объект графа в JSON-формате для последующей обработки на фронтенде.

    Args:
        request (HttpRequest): HTTP-запрос пользователя.

    Returns:
        JsonResponse: Граф с узлами и связями в формате JSON.
    """
    # Возвращаем сгенерированный граф как JSON-ответ
    return JsonResponse(build_graph_object())


class AddView(TemplateView, TemplatePostViewMixin):
    """
    Представление страницы для добавления триплетов (субъект-предикат-объект) на основе сущностей.

    Отвечает за:
        - Загрузку статьи и существующих сущностей.
        - Формирование и добавление новых триплетов в базу данных.
        - Навигацию по предложениям статьи.

    Атрибуты:
        template_name (str): Путь к HTML-шаблону страницы добавления триплетов.
        last_for_triples (dict): Словарь для хранения состояния обработки триплетов для каждого пользователя.
        articles (dict): Словарь для хранения выбранных пользователем источников.
    """

    template_name = "add.html"

    last_for_triples: dict[Any, list] = {}
    """
    Словарь состояния работы с триплетами для каждого пользователя:
        {пользователь: [индекс предложения, список предложений, список сущностей, описание источника]}
    """

    articles: dict[Any, int] = {}
    """
    Словарь выбранных источников для каждого пользователя:
        {пользователь: id источника}
    """

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Формирует контекст данных для рендеринга страницы добавления триплетов.

        Добавляет в контекст:
            - Список описаний доступных источников (descriptions).
            - Список доступных предикатов (preds).
            - Текущее состояние обработки статьи (если пользователь отправил запрос).

        В зависимости от метода запроса:
            - GET: вызывает process_get().
            - POST: вызывает process_post().

        Returns:
            dict: Словарь данных для шаблона.
        """
        context = super().get_context_data(**kwargs)

        # Добавляем список всех источников (url + описание) и доступные предикаты
        context |= {
            "descriptions": [
                [i["n.url"], i["n.description"]]
                for i in gr.SourceRepository.get_descriptions()
            ],
            "preds": nm.Predicate.get_preds(),
        }

        # Вызываем обработку запроса в зависимости от его типа
        if self.request.method == "GET":
            context |= self.process_get()
        elif self.request.method == "POST":
            context |= self.process_post()

        return context

    def process_get(self) -> Dict[str, Any]:
        """
        Обрабатывает GET-запрос для страницы добавления триплетов.

        Выполняет:
            - Загрузку текущего предложения и сущностей для выбранной статьи.
            - Получение уже существующих триплетов по текущему предложению.

        Returns:
            dict: Данные для отображения предложения, сущностей и триплетов на странице.
        """
        result = {}

        # Проверяем, есть ли сохранённое состояние работы для пользователя
        if self.request.user not in self.last_for_triples.keys():
            return result

        # Извлекаем последнее состояние для пользователя
        last = self.last_for_triples[self.request.user]
        ents = [e[1] for e in last[2]] # Получаем список сущностей
        sent_form = generate_sent_form(last[0], last[1], ents) # Формируем предложение с сущностями
        source = gr.SourceRepository.get_by_url(last[3]) # Получаем объект источника по описанию

        # Формируем контекст для отображения
        result |= {
            "sentence": sent_form[0], # Текст предложения
            "ents": list(enumerate(sent_form[1])), # Список сущностей с индексами
            "sent_index": last[0], # Индекс текущего предложения
            "sent_len": len(last[1]), # Общее количество предложений
            "show": True,
            "triples": nm.Triple.get_by_sent(source, last[1][last[0]]), # Уже существующие триплеты по предложению
        }

        return result

    def process_post(self):
        """
        Обрабатывает POST-запрос на странице добавления триплетов.

        Возможные действия:
            - Загрузка статьи и сущностей из базы данных.
            - Добавление нового триплета в базу.
            - Переход к следующему или предыдущему предложению.

        Returns:
            dict: Обновлённый контекст данных для рендеринга страницы.
        """
        result = {}

        # Пользователь выбрал источник и хочет загрузить текст статьи
        if "get_from_base" in self.request.POST:
            description = self.request.POST.get("descriptions")
            self.articles[self.request.user] = description

            # Ниже очень непонятный код, нужно оптимизировать взаимодействие с БД

            # Загружаем объект источника по описанию
            source = gr.SourceRepository.get_by_url(description)

            last_url = source.url
            last_text = get_parsed_html(last_url)

            # Разбиваем текст на предложения
            sents = sent_tokenize(last_text, "russian")
            sent_index = 0 # Начинаем с первого предложения

            # Получаем связанные сущности для первого предложения
            ents_for_article = source.get_connected_entities(sents[sent_index])
            ents = list(enumerate(i["e"]["name"] for i in ents_for_article))

            # Сохраняем состояние для пользователя
            self.last_for_triples[self.request.user] = [
                sent_index,
                sents,
                ents,
                description,
            ]

            # Формируем данные для отображения
            sent_form = generate_sent_form(sent_index, sents, ents_for_article)

            result |= {
                "source": self.articles[self.request.user],
                "sentence": sent_form[0],
                "ents": list(enumerate(sent_form[1])),
                "triples": nm.Triple.get_by_sent(source, sent_form[0]),
                "sent_index": sent_index,
                "sent_len": len(sents),
                "show": True,
            }
        
        # Пользователь отправил форму для добавления триплета
        elif "add_triple" in self.request.POST:
            sent_index, sents, ents, description = self.last_for_triples[
                self.request.user
            ]

            # Извлекаем выбранные субъект, объект и предикат
            # preds = nm.Predicate.get_preds()
            sub = self.request.POST.get("sub")
            obj = self.request.POST.get("obj")
            pred = self.request.POST.get("pred")

            # Формируем текущее предложение и сущности
            sent_form = generate_sent_form(sent_index, sents, [e[1] for e in ents])
            sent = sent_form[0]
            ents = list(enumerate(sent_form[1]))

            # Создаём триплет в базе данных
            source = gr.SourceRepository.get_by_url(description)
            gr.TripleRepository.create_triple(
                sub, source, obj, pred, sent, self.request.user.pk
            )

            created = True # Предположим успешное создание (пока без проверки)

            # triple_score = nm.TripleScore(
            #     triple=triple, expert=self.request.user, score=True
            # )

            # Формируем ответ о результате добавления
            if created:
                # triple.save()
                # triple_score.save()
                result["verdict_triple"] = "Триплет успешно добавлен"
            else:
                result["verdict_triple"] = "Триплет уже есть в базе"

            result |= {
                "source": self.articles[self.request.user],
                "show": True,
                "sentence": sent,
                "ents": ents,
                "triples": nm.Triple.get_by_sent(source, sents[sent_index]),
                "sent_index": sent_index,
                "sent_len": len(sents),
            }

        # Пользователь нажал "следующее" или "предыдущее" предложение
        elif "next" in self.request.POST or "previous" in self.request.POST:
            sent_index, sents, ents, description = self.last_for_triples[
                self.request.user
            ]

            # Смещаем индекс предложения
            sent_index += 1 if "next" in self.request.POST else -1

            # Проверка на выход за границы списка предложений
            if sent_index < 0 or sent_index >= len(sents):
                return result

            # Загружаем сущности для нового предложения
            source = gr.SourceRepository.get_by_url(description)
            ents_for_article = source.get_connected_entities(sents[sent_index])
            ents = list(enumerate(i["e"]["name"] for i in ents_for_article))

            # Обновляем состояние пользователя
            self.last_for_triples[self.request.user][0] = sent_index
            self.last_for_triples[self.request.user][2] = ents

            # Формируем данные для отображения
            sent_form = generate_sent_form(sent_index, sents, [e[1] for e in ents])
            result |= {
                "source": self.articles[self.request.user],
                "show": True,
                "sentence": sent_form[0],
                "ents": ents,
                "sent_index": sent_index,
                "sent_len": len(sents),
                "triples": nm.Triple.get_by_sent(source, sents[sent_index]),
            }

        return result


class PredicateView(TemplateView, TemplatePostViewMixin):
    """
    Представление страницы для работы с предикатами.

    Отвечает за:
        - Добавление новых предикатов в базу данных.
        - Поиск существующих предикатов по их названию.

    Атрибуты:
        template_name (str): Путь к HTML-шаблону страницы работы с предикатами.
    """

    template_name = "predicates.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Формирует контекст данных для страницы работы с предикатами.

        В случае POST-запроса:
            - Обрабатывает действие пользователя через метод process_post().

        Returns:
            dict: Словарь данных для передачи в шаблон.
        """
        context = super().get_context_data(**kwargs)

        # Если был отправлен POST-запрос, обрабатываем его
        if self.request.method == "POST":
            context |= self.process_post()
        return context

    def process_post(self):
        """
        Обрабатывает POST-запрос на странице работы с предикатами.

        Возможные действия:
            - Добавление нового предиката в базу данных.
            - Поиск существующего предиката и получение его описания.

        Returns:
            dict: Словарь с результатами выполнения действия для передачи в шаблон.
        """
        result = {}

        # Получаем название предиката из формы
        pred = self.request.POST.get("pred")

        # Проверка: если предикат не указан
        if pred == "":
            result["verdict_pred"] = "Отсутствует наименование предиката"

        # Пользователь выбрал добавление нового предиката
        if "add_pred" in self.request.POST:
            description = self.request.POST.get("pred_description")

            # Проверка: если описание не указано
            if description == "":
                result["verdict_pred"] = "Отсутствует описание предиката"
            else:
                # Пытаемся создать новый предикат (или находим существующий)
                _, created = nm.Predicate.objects.get_or_create(
                    pred=pred,
                    defaults={"description": description, "expert": self.request.user},
                )

                # Формируем сообщение об успехе или наличии предиката
                result["verdict_pred"] = (
                    "Предикат успешно добавлен"
                    if created
                    else "Предикат уже есть в базе"
                )

        # Пользователь выбрал поиск существующего предиката
        elif "find_pred" in self.request.POST:
            try:
                # Ищем предикат и возвращаем его описание
                result["pred_descriptions"] = "Описание предиката : " + str(
                    nm.Predicate.objects.get(pred=pred).description
                )
            except nm.Predicate.DoesNotExist:
                # Если предикат не найден
                result["verdict_pred"] = "Предикат не найден"

            # В любом случае возвращаем список всех предикатов
            result["preds"] = nm.Predicate.get_preds()

        return result


# ------------------------------------------------------------------------------
# Замечания и предложения по улучшению кода (Technical Debt)

"""
1. Повторение кода в методах process_post (в разных классах):
   - Блоки навигации ("next", "previous") и загрузки данных из базы очень похожи.
   - Можно вынести общую логику в отдельные вспомогательные методы или утилиты.

2. Состояние пользователя (last_for_ents, last_for_triples):
   - Состояние хранится в глобальных переменных прямо в коде views.py.
   - Лучше перенести управление состоянием в отдельный сервисный класс или использовать сессию Django.

3. Прямые обращения к POST-данным:
   - Нет проверки наличия обязательных полей в POST (например, request.POST.get("descriptions")).
   - Следует добавить более строгую валидацию данных формы.

4. Ошибки и исключения:
   - Мало обработки исключений (например, ошибки при запросах к базе данных или при работе с внешними источниками).
   - Желательно добавить обработку ошибок try-except для более надёжной работы.

5. Работа с базой данных:
   - Некоторые запросы к БД выглядят тяжеловесно (например, многократные вызовы SourceRepository.get_by_url).
   - Можно оптимизировать, кэшируя объекты на уровне сессии запроса.

6. Улучшение структуры кода:
   - Функции process_get и process_post перегружены логикой и разветвлениями.
   - Лучше разделить их на более мелкие функции с одним назначением.

7. Безопасность вставки данных:
   - Использование mark_safe требует осторожности.
   - Нужно убедиться, что входящие данные действительно безопасны или дополнительно очищены.

8. Повторение логики:
   - Логика формирования предложений и обработки сущностей повторяется в нескольких местах (IndexView и AddView).
   - Можно выделить отдельный модуль или сервис для обработки текста и сущностей.

"""
# ------------------------------------------------------------------------------
