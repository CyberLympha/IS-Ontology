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
from django.utils.functional import SimpleLazyObject
from django.contrib.auth import get_user_model


last_for_triples = {}


class TemplatePostViewMixin:
    """
    Mixin-класс для обработки POST-запросов в Django-представлениях, основанных на TemplateView.

    Назначение:
    - Позволяет переопределить поведение стандартного метода `post` у `TemplateView`,
      перенаправляя его на использование `get_context_data()` и дальнейший рендер шаблона.
    - Упрощает структуру представлений, где логика GET и POST запросов обрабатывается через один шаблон.

    Применение:
    - Подключается к классу-представлению (например, через множественное наследование),
      чтобы поддерживать логику отображения страницы после обработки формы (POST).
    """

    def post(self, request, *args, **kwargs):
        """
        Обрабатывает POST-запрос и возвращает HTML-ответ, используя контекст из `get_context_data`.

        Работает как обертка над `get_context_data`, автоматически вызывая его при получении POST-запроса
        и рендеря шаблон на основе полученного контекста.

        Аргументы:
            request (HttpRequest): Объект запроса.
            *args, **kwargs: Дополнительные аргументы, передаваемые во вьюху.

        Возвращает:
            HttpResponse: Сформированный HTML-ответ на основе шаблона и данных контекста.
        """
        return super(TemplateView, self).render_to_response(
            self.get_context_data(**kwargs)
        )


class IndexView(TemplateView, TemplatePostViewMixin):
    """
    Представление (View) для страницы извлечения сущностей (IE) в Django-приложении.

    Назначение:
    - Позволяет пользователю:
        - выбрать статью из базы данных;
        - извлечь предложения из текста;
        - разметить и сохранить сущности;
        - навигировать между предложениями статьи.

    Шаблон:
        - Использует HTML-шаблон `ie.html`.

    Атрибуты класса:
        - template_name (str): путь к шаблону.
        - last_for_ents (dict[Any, list]): словарь сессий, сохраняющий состояние извлечения
          сущностей для каждого пользователя по его `user.pk`.

    Основные методы:
        - get_context_data: собирает и возвращает контекст для рендера страницы.
        - process_get: обрабатывает GET-запросы (отображение предыдущих данных).
        - process_post: обрабатывает POST-запросы (получение текста статьи, добавление сущностей и навигация).
    """

    template_name = "ie.html"
    last_for_ents: dict[Any, list] = {}

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Формирует и возвращает контекст для шаблона IE (извлечение сущностей).

        Контекст включает:
        - Список доступных описаний статей из базы данных (используется в выпадающем списке).
        - Данные текущего состояния сессии пользователя: текущая фраза, сущности, статус отображения.
        - Индикаторы наличия следующего/предыдущего предложения.

        Внутри:
        - Определяется, была ли обработка GET или POST запроса.
        - В зависимости от типа запроса вызываются соответствующие методы: `process_get()` или `process_post()`.

        Возвращает:
            dict: Контекст, содержащий данные для шаблона.
        """
        context = super().get_context_data(**kwargs)
        context["descriptions"] = [
            [i["n.url"], i["n.description"]]
            for i in gr.SourceRepository.get_descriptions()
        ]

        if self.request.method == "GET":
            context |= self.process_get()
        elif self.request.method == "POST":
            context |= self.process_post()

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
        Обрабатывает GET-запрос к странице извлечения сущностей (IE).
        """
        user_pk = getattr(self.request.user, 'pk', None)
        result = {"show": True}

        if not user_pk or user_pk not in self.last_for_ents:
            return result

        sent_index, sents, ents, description = self.last_for_ents[user_pk]
        source = gr.SourceRepository.get_by_url(description)
        sent_form = generate_sent_form(sent_index, sents, ents)
        marked_ents = get_marked_ents(sent_index, sents, source)
        filtered_ents = filter_ents(marked_ents, sent_form[1])

        result |= {
            "sentence": sent_form[0],
            "ents": list(enumerate(filtered_ents)),
            "sent_index": sent_index,
            "sent_len": len(sents),
            "show_table": True,
            "ents_in_sent": marked_ents,
        }

        return result



    def process_post(self) -> Dict[str, Any]:
        """
        ...
        """
        print("DEBUG::", type(self.request.user), self.request.user)
        user = (
            self.request.user._wrapped
            if isinstance(self.request.user, SimpleLazyObject)
            else self.request.user
        )
        result: Dict[str, Any] = {"show": True, "show_table": True}

        # 1. Пользователь выбрал статью
        if "descriptions" in self.request.POST:
            result["source"] = self.request.POST.get("descriptions")

        # 2. Загрузить статью и предложение №0
        if "get_from_base" in self.request.POST:
            source = gr.SourceRepository.get_by_url(result["source"])

            last_text = get_parsed_html(source.url)
            ents = get_ents(source.url, crf)

            sent_index = 0
            sents = sent_tokenize(last_text, language="russian")

            # Кэшируем состояние по user.pk
            self.last_for_ents[user.pk] = [sent_index, sents, ents, source.url]

            sent_form = generate_sent_form(sent_index, sents, ents)
            marked_ents = get_marked_ents(sent_index, sents, source)
            filtered_ents = filter_ents(marked_ents, sent_form[1])

            result |= {
                "sentence": sent_form[0],
                "ents": list(enumerate(filtered_ents)),
                "sent_index": sent_index,
                "sent_len": len(sents),
                "ents_in_sent": marked_ents,
            }

        # 3. Добавление отмеченных сущностей
        elif "add_ents" in self.request.POST:
            if user.pk not in self.last_for_ents:     # защитимся от KeyError
                return result

            sent_index, sents, ents, description = self.last_for_ents[user.pk]
            sent_form = generate_sent_form(sent_index, sents, ents)

            source = gr.SourceRepository.get_by_url(description)
            marked_ents = get_marked_ents(sent_index, sents, source)
            filtered_ents = filter_ents(marked_ents, sent_form[1])

            applyed_ents = [self.request.POST.get(str(i)) for i in range(len(filtered_ents))]
            if any(applyed_ents):
                for i, ae in enumerate(applyed_ents):
                    if ae == "on":
                        gr.EntityRepository.create(
                            filtered_ents[i], source, sent_form[0], user.pk
                        )
                result["verdict"] = "Новые сущности внесены в базу"
            else:
                result["verdict"] = "Сущности не были отмечены"

            result |= {
                "sentence": sent_form[0],
                "ents": list(enumerate(filtered_ents)),
                "sent_index": sent_index,
                "sent_len": len(sents),
                "ents_in_sent": marked_ents,
            }

        # 4. Переключение предложений
        elif "next" in self.request.POST or "previous" in self.request.POST:
            if user.pk not in self.last_for_ents:
                return result

            sent_index, sents, ents, description = self.last_for_ents[user.pk]
            sent_index += 1 if "next" in self.request.POST else -1

            if not (0 <= sent_index < len(sents)):
                result["verdict"] = "Вы вышли за пределы предложений."
                return result

            # сохраняем новый индекс
            self.last_for_ents[user.pk][0] = sent_index

            source = gr.SourceRepository.get_by_url(description)
            sent_form = generate_sent_form(sent_index, sents, ents)
            marked_ents = get_marked_ents(sent_index, sents, source)
            filtered_ents = filter_ents(marked_ents, sent_form[1])

            result |= {
                "sentence": sent_form[0],
                "ents": list(enumerate(filtered_ents)),
                "sent_index": sent_index,
                "sent_len": len(sents),
                "ents_in_sent": marked_ents,
            }

        return result




def graph(request):
    """
    Обрабатывает запрос к представлению визуализации графа сущностей и триплетов.

    Выполняет следующее:
    - Вызывает функцию `build_graph_object`, которая формирует объект графа из узлов и связей,
      извлечённых из графовой базы данных Neo4j;
    - Оборачивает полученный объект в `mark_safe`, чтобы передать его как безопасный HTML/JS код в шаблон;
    - Передаёт объект графа в шаблон 'graph.html' для визуализации.

    Параметры:
        request (HttpRequest): объект запроса Django.

    Возвращает:
        HttpResponse: отрендеренный шаблон 'graph.html' с объектом графа.
    """
    context = {}
    context["graph_obj"] = mark_safe(str(build_graph_object()))
    return render(request, "graph.html", context)


def build_graph_object():
    """
    Строит объект графа из сущностей (Entity) и триплетов (Triple) на основе данных из Neo4j.

    Описание:
    - Выполняет Cypher-запрос к базе Neo4j, чтобы извлечь все триплеты в формате:
        (Entity) --> (Triple) --> (Entity)
    - Формирует структуру данных, пригодную для визуализации в виде графа:
        - `nodes`: словарь всех уникальных узлов (сущности и отношения);
        - `links`: список всех связей между узлами.

    Формат узлов:
    - Entity: тип "term", имя и идентификатор совпадают, а также добавляется ID эксперта;
    - Triple: тип "rel", идентификатор составляется из имени и индекса для уникальности.

    Связи (links):
    - От субъекта к отношению;
    - От отношения к объекта.

    Возвращает:
        dict: объект графа с ключами:
            - "nodes": список узлов;
            - "links": список связей между узлами.
    """
    result = execute_read(
        lambda tx: tx.run(
            "MATCH (sub: Entity)-->(pred: Triple)-->(obj: Entity) return sub, pred, obj"
        ).values()
    )

    graph_obj = {"nodes": {}, "links": []}

    _id = 0
    for sub, pred, obj in result:
        for i in [sub, obj]:
            graph_obj["nodes"][i["name"]] = {
                "id": i["name"],
                "name": i["name"],
                "expert": i["user"],
                "type": "term",
            }

        pred_id = pred.get("name") + str(_id)
        graph_obj["nodes"][pred_id] = {
            "id": pred_id,
            "type": "rel",
            "name": pred.get("name"),
        }
        graph_obj["links"].append({"source": sub["name"], "target": pred_id})
        graph_obj["links"].append({"source": pred_id, "target": obj["name"]})

        _id += 1

    graph_obj["nodes"] = list(graph_obj["nodes"].values())
    return graph_obj


def build_graph(request):
    """
    Django view-функция для получения объекта графа в формате JSON.

    Описание:
    - Оборачивает результат функции `build_graph_object()` в `JsonResponse`;
    - Используется для API-запросов, которые ожидают данные графа в формате JSON (например, на фронтенде для визуализации графа).

    Аргументы:
        request (HttpRequest): HTTP-запрос от клиента.

    Возвращает:
        JsonResponse: JSON-ответ, содержащий структуру графа с узлами и связями.
    """
    return JsonResponse(build_graph_object())


class AddView(TemplateView, TemplatePostViewMixin):
    """
    Представление (View) для интерфейса добавления триплетов в граф знаний.

    Основное назначение:
    - Предоставляет пользователю возможность выбрать статью из базы;
    - Позволяет просматривать предложения статьи и сущности, связанные с ними;
    - Обеспечивает интерфейс для ручного добавления новых триплетов (сущность-предикат-сущность);
    - Поддерживает навигацию между предложениями (вперёд/назад).

    Особенности:
    - Использует кэш `last_for_triples` для хранения состояния статьи (предложений и сущностей)
      для каждого пользователя (ключ — `user.pk`);
    - Использует словарь `articles` для хранения описания текущей статьи, связанной с пользователем.

    Атрибуты:
        template_name (str): путь к шаблону HTML, связанному с этим представлением (`add.html`);
        last_for_triples (dict): кэш состояния статьи для каждого пользователя;
        articles (dict): текущая выбранная статья для каждого пользователя.

    Методы:
        - get_context_data(): формирует контекст для рендера шаблона в зависимости от запроса;
        - process_get(): восстанавливает состояние для ранее выбранной статьи;
        - process_post(): обрабатывает действия пользователя (выбор статьи, добавление триплета, навигация).
    """
    template_name = "add.html"
    last_for_triples: dict[Any, list] = {}
    articles: dict[Any, int] = {}

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Формирует и возвращает контекст для шаблона, связанного с добавлением триплетов.

        Контекст включает:
        - descriptions: список пар [url, описание] всех источников из базы данных (используется в выпадающем списке).
        - preds: список всех доступных предикатов (предложений-связей), полученных из модели Predicate.
        - результат вызова `process_get()` или `process_post()` в зависимости от типа запроса.

        Метод применяется в классе-представлении AddView и определяет, какие данные будут доступны в шаблоне add.html.

        Внутри:
        - Если метод запроса GET — вызывается `process_get()` для отображения текущего состояния.
        - Если POST — вызывается `process_post()` для обработки действия пользователя (добавление триплета, переход и т.п.).

        Аргументы:
            kwargs (Any): Дополнительные именованные параметры (не используются явно, но поддерживаются для совместимости).

        Возвращает:
            Dict[str, Any]: Словарь с данными, которые будут переданы в шаблон.
        """
        context = super().get_context_data(**kwargs)
        context |= {
            "descriptions": [
                [i["n.url"], i["n.description"]]
                for i in gr.SourceRepository.get_descriptions()
            ],
            "preds": nm.Predicate.get_preds(),
        }

        if self.request.method == "GET":
            context |= self.process_get()
        elif self.request.method == "POST":
            context |= self.process_post()

        return context

    def process_get(self) -> Dict[str, Any]:
        """
        Обрабатывает GET-запрос в интерфейсе добавления триплетов (представление AddView).

        Основные действия:
        - Проверяет, есть ли сохранённое состояние статьи (sentence, ents и др.) для текущего пользователя.
        - Если да — восстанавливает:
            - текущее предложение,
            - связанные сущности,
            - уже существующие триплеты, привязанные к этому предложению.
        - Формирует контекст для отображения страницы.

        Применяется, когда пользователь возвращается к работе с ранее выбранной статьей.

        Важно:
        - Для корректной работы предполагается, что ранее уже была вызвана `process_post` и в 
        `self.last_for_triples` сохранено состояние для пользователя.

        Возвращает:
            dict: Контекст для шаблона add.html:
                - sentence: текущее предложение.
                - ents: сущности в предложении.
                - sent_index: индекс текущего предложения.
                - sent_len: общее число предложений.
                - show: флаг отображения секции.
                - triples: существующие триплеты, связанные с этим предложением.
        """
        # Гарантируем, что user — не ленивый объект, а настоящий пользователь
        user = self.request.user._wrapped if isinstance(self.request.user, SimpleLazyObject) else self.request.user
        result = {}

        if user not in self.last_for_triples.keys():
            return result

        last = self.last_for_triples[self.request.user]
        ents = [e[1] for e in last[2]]
        sent_form = generate_sent_form(last[0], last[1], ents)
        source = gr.SourceRepository.get_by_url(last[3])

        result |= {
            "sentence": sent_form[0],
            "ents": list(enumerate(sent_form[1])),
            "sent_index": last[0],
            "sent_len": len(last[1]),
            "show": True,
            "triples": nm.Triple.get_by_sent(source, last[1][last[0]]),
        }

        return result

    def process_post(self):
        """
        Обрабатывает POST-запросы на странице добавления триплетов.

        В зависимости от содержимого POST-запроса выполняет одну из следующих операций:
        1. Загрузка статьи из базы данных по URL и разметка предложений и сущностей.
        2. Добавление триплета (сущность–предикат–сущность) для текущего предложения.
        3. Переключение между предложениями (вперёд/назад) при аннотировании статьи.

        ВАЖНО:
        - Метод хранит данные в `self.last_for_triples` и `self.articles`, где ключами выступает `user.pk`,
        а не объект `user`, чтобы избежать проблем с сериализацией `SimpleLazyObject`.
        - Все операции выполняются на основе `user.pk` как уникального идентификатора пользователя.

        Возвращает:
            dict: Контекст с результатами обработки для отображения в шаблоне, может включать:
                - source: описание текущей статьи;
                - sentence: текущее предложение;
                - ents: список сущностей;
                - triples: уже сохранённые триплеты;
                - sent_index: индекс текущего предложения;
                - sent_len: общее количество предложений;
                - verdict_triple: сообщение о добавлении триплета;
                - show: флаг отображения секции.
        """
        # Гарантируем, что user — не ленивый объект, а настоящий пользователь
        user = self.request.user._wrapped if isinstance(self.request.user, SimpleLazyObject) else self.request.user
        result = {}

        if "get_from_base" in self.request.POST:
            description = self.request.POST.get("descriptions")
            self.articles[self.request.user] = description
            # Ниже очень непонятный код, нужно оптимизировать взаимодействие с БД

            source = gr.SourceRepository.get_by_url(description)

            last_url = source.url
            last_text = get_parsed_html(last_url)

            sents = sent_tokenize(last_text, "russian")
            sent_index = 0

            ents_for_article = source.get_connected_entities(sents[sent_index])

            ents = list(enumerate(i["e"]["name"] for i in ents_for_article))

            self.last_for_triples[self.request.user] = [
                sent_index,
                sents,
                ents,
                description,
            ]
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

        elif "add_triple" in self.request.POST:
            sent_index, sents, ents, description = self.last_for_triples[
                self.request.user
            ]  
            sub = self.request.POST.get("sub")
            obj = self.request.POST.get("obj")
            pred = self.request.POST.get("pred")

            sent_form = generate_sent_form(sent_index, sents, [e[1] for e in ents])
            sent = sent_form[0]
            ents = list(enumerate(sent_form[1]))

            source = gr.SourceRepository.get_by_url(description)

            # Сохраняем триплет и добавляем оценку эксперта
            triple = gr.TripleRepository.create_triple(
                sub, source, obj, pred, sent, user.pk
            )
            created = True

            if created:
                # Сохраняем экспертную оценку для триплета
                triple_score = nm.TripleScore(
                    triple=triple, expert=user, score=True
                )
                triple_score.save()

                result["verdict_triple"] = "Триплет успешно добавлен"
            else:
                result["verdict_triple"] = "Триплет уже есть в базе"


            result |= {
                "source": self.articles[user],
                "show": True,
                "sentence": sent,
                "ents": ents,
                "triples": nm.Triple.get_by_sent(source, sents[sent_index]),
                "sent_index": sent_index,
                "sent_len": len(sents),
            }

        elif "next" in self.request.POST or "previous" in self.request.POST:
            sent_index, sents, ents, description = self.last_for_triples[user]

            sent_index += 1 if "next" in self.request.POST else -1
            if sent_index < 0 or sent_index >= len(sents):
                return result

            source = gr.SourceRepository.get_by_url(description)
            ents_for_article = source.get_connected_entities(sents[sent_index])
            ents = list(enumerate(i["e"]["name"] for i in ents_for_article))

            self.last_for_triples[self.request.userlf][0] = sent_index
            self.last_for_triples[self.request.user][2] = ents
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
    Представление (View), отвечающее за управление предикатами в графе знаний.

    Это специализированная страница, где пользователь может:
    - Добавлять новые предикаты (отношения между сущностями);
    - Искать описание существующих предикатов.

    Используемые компоненты:
    - `TemplateView`: базовый класс Django для представлений на основе шаблонов.
    - `TemplatePostViewMixin`: миксин, добавляющий поведение при обработке POST-запросов.

    Шаблон:
    - `predicates.html` — отображает форму для добавления или поиска предикатов.

    Методы:
    - `get_context_data`: формирует и возвращает контекст шаблона, включая результат обработки POST-запроса (если есть).
    - `process_post`: логика обработки формы — добавление или поиск предикатов.

    Хранилище:
    - Все предикаты сохраняются в таблице модели `Predicate` в базе данных.

    Примечание:
    - Все действия пользователя сопровождаются сообщениями, которые отображаются в шаблоне: успешное добавление, ошибка валидации, предикат не найден и т.д.
    """
    template_name = "predicates.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Формирует и возвращает контекст для шаблона, связанного с управлением предикатами.

        Метод вызывается при обращении к представлению (View) `PredicateView`, которое отвечает
        за отображение и добавление предикатов (связей) между сущностями в графе знаний.

        Особенности поведения:
        - Если метод запроса POST, вызывается `process_post()` для обработки действия пользователя 
        (добавление или поиск предиката);
        - Результаты обработки добавляются в контекст и передаются в шаблон `predicates.html`.

        Аргументы:
            kwargs (Any): Дополнительные параметры, переданные в шаблон (обычно не используются явно).

        Возвращает:
            Dict[str, Any]: Контекст, содержащий результат обработки формы предикатов.
        """
        context = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            context |= self.process_post()
        return context

    def process_post(self):
        """
        Обрабатывает POST-запросы на странице управления предикатами.

        Метод используется для работы с формой предикатов (Predicate) и выполняет следующие действия:
        1. Если пользователь нажал кнопку "Добавить предикат":
        - Проверяет наличие введённого названия (`pred`) и описания (`pred_description`);
        - Добавляет новый предикат в базу данных, если он ещё не существует;
        - Возвращает сообщение об успехе или уведомляет, что такой предикат уже есть.
        2. Если пользователь нажал кнопку "Найти предикат":
        - Пытается найти предикат в базе данных по его названию;
        - Если найден — возвращает его описание;
        - Если не найден — уведомляет об этом пользователя.

        В результате метод формирует словарь с полями:
        - 'verdict_pred' — строка с результатом выполнения действия (успех/ошибка/найден/не найден);
        - 'pred_descriptions' — описание найденного предиката (если применимо);
        - 'preds' — список всех предикатов в базе данных (используется для отображения в шаблоне).

        Возвращает:
            dict: Контекст с результатами обработки формы, который будет передан в шаблон.
        """
        result = {}

        pred = self.request.POST.get("pred")
        if pred == "":
            result["verdict_pred"] = "Отсутствует наименование предиката"

        if "add_pred" in self.request.POST:
            description = self.request.POST.get("pred_description")
            if description == "":
                result["verdict_pred"] = "Отсутствует описание предиката"
            else:
                _, created = nm.Predicate.objects.get_or_create(
                    pred=pred,
                    defaults={"description": description, "expert": self.request.user},
                )
                result["verdict_pred"] = (
                    "Предикат успешно добавлен"
                    if created
                    else "Предикат уже есть в базе"
                )
        elif "find_pred" in self.request.POST:
            try:
                result["pred_descriptions"] = "Описание предиката : " + str(
                    nm.Predicate.objects.get(pred=pred).description
                )
            except nm.Predicate.DoesNotExist:
                result["verdict_pred"] = "Предикат не найден"

            result["preds"] = nm.Predicate.get_preds()

        return result
