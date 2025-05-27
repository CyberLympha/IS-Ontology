"""
Django view-модуль для классификации веб-страниц по теме информационной безопасности.

Этот модуль реализует:
- загрузку предобученной LSTM-модели и токенизатора;
- маршрутизацию и обработку запросов на главной странице;
- парсинг HTML-документов по URL;
- классификацию текста по теме информационной безопасности;
- сохранение результатов и источников в базу данных.

Функциональность:
- `index(request)`: основная view-функция, обрабатывающая GET и POST-запросы;
- `check_url(url)`: проверка доступности ссылки;
- `check_text(text)`: проверка наличия содержимого текста;
- `check_source(url, description, user)`: сохранение источника и текста в БД;
- `predict(tokenizer, model, url)`: запуск модели для предсказания принадлежности к ИБ;
- `get_parsed_html(link)`: парсинг текста из HTML по ссылке.

Используемые зависимости:
- Django
- requests, re, BeautifulSoup (для HTTP-запросов и парсинга)
- TensorFlow/Keras (для загрузки и использования модели)
- pickle (для десериализации токенизатора)

Предполагается, что:
- файл токенизатора (`tokenizer.pickle`) и модель (`clf_is.h5`) лежат в корне проекта;
- база данных содержит модели `Source` и `Text`;
- репозиторий `SourceRepository` отвечает за внешнюю логику создания графов или связей.

Автор: [Ваше имя или команда]
Дата: [указать актуальную дату]
"""


import os

from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import render
import requests
import re
from bs4 import BeautifulSoup
import pickle
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Embedding, LSTM
from tensorflow.keras.preprocessing.sequence import pad_sequences
from django.conf import settings
import pickle

from ..Ie.graph_repositories import SourceRepository
from ..Notes.models import Source, Text

# Формирование пути к файлу токенизатора
tokenizer_path = os.path.join(str(settings.BASE_DIR), "tokenizer.pickle")

# Формирование пути к файлу обученной модели
model_path = os.path.join(str(settings.BASE_DIR), "clf_is.h5")
print(model_path)

# Загрузка токенизатора из файла
with open(tokenizer_path, "rb") as handle:
     tokenizer = pickle.load(handle)

# Инициализация модели нейросети с архитектурой LSTM
classifier = Sequential()
classifier.add(Embedding(20000, 64, input_length=400))  # Слой эмбеддингов
classifier.add(LSTM(64)) # Рекуррентный слой LSTM
classifier.add(Dense(1, activation="sigmoid"))  # Выходной слой для бинарной классификации
# Компиляция модели с функцией потерь и метриками
classifier.compile(
    optimizer="adam", loss="binary_crossentropy", metrics=["AUC", "accuracy"]
)

# Загрузка весов предобученной модели
classifier.load_weights(model_path)

# Словарь для хранения последнего URL, отправленного пользователем
last = {}


def index(request: WSGIRequest):
    """
    Обрабатывает GET и POST-запросы на главной странице классификации.

    GET:
        - Отображает пустую форму.

    POST:
        - При нажатии на кнопку 'classify': выполняет проверку URL и классифицирует статью.
        - При нажатии на кнопку 'add_to_base': сохраняет статью в базу, если она ранее не была добавлена.

    Args:
        request (WSGIRequest): HTTP-запрос от пользователя.

    Returns:
        HttpResponse: Отображение шаблона clf.html с результатами классификации или добавления в базу.
    """

    context = {}
    global last

    if request.method == "GET":
        context["show_verdict"] = False
        context["show"] = False

    if request.method == "POST" and "classify" in request.POST:
        last_url = request.POST.get("request_url")
        if check_url(last_url):
            if check_text(get_parsed_html(last_url)):
                result = predict(tokenizer, classifier, last_url)
                context["request_type"] = result
                context["show"] = True
                last[request.user] = last_url
            else:
                context["request_type"] = "Не удалось спарсить текст."

    if request.method == "POST" and "add_to_base" in request.POST:
        description = request.POST.get("request_description")
        url = last[request.user]
        verdict = check_source(url, description, request.user.pk)
        context["verdict"] = verdict[0]
        context["description"] = verdict[1]
        context["show_verdict"] = True

    return render(request, "clf.html", context)


def check_url(url):
    """
    Проверяет доступность URL по HTTP-запросу.

    Args:
        url (str): Ссылка на веб-страницу.

    Returns:
        bool: True, если URL существует и не возвращает ошибку 404 или SSL, иначе False.
    """
    try:
        if str(requests.get(url)) != "<Response [404]>":
            return True
        return False
    except requests.exceptions.SSLError:
        return False


def check_text(text):
    """
    Проверяет, что полученный текст не пустой.

    Args:
        text (str): Текст, полученный после парсинга HTML.

    Returns:
        bool: True, если текст не пустой, иначе False.
    """
    if len(text) != 0:
        return True
    return False


def check_source(url: str, description: str, user) -> tuple[str, str]:
    """
    Добавляет источник в базу данных, если он ранее не был добавлен.

    Args:
        url (str): URL источника.
        description (str): Описание статьи, предоставленное пользователем.
        user (User): Пользователь, добавивший источник.

    Returns:
        tuple[str, str]: Вердикт и описание (либо информация о существующей записи, либо подтверждение добавления).
    """
    if Source.objects.filter(url=url):
        return (
            "Статья уже есть в базе",
            "Описание статьи: " + str(Source.objects.filter(url=url)[0].description),
        )
    else:
        source = Source(url=url, description=description)
        source.save()
        SourceRepository(url, description, source.date, user).create()
        text = Text(source=source, text=get_parsed_html(url))
        text.save()
        return (
            "Статья добавлена",
            "Описание статьи: " + Source.objects.filter(url=url)[0].description,
        )


def predict(tokenizer, model, url):
    """
    Классифицирует статью как относящуюся или не относящуюся к информационной безопасности.

    Args:
        tokenizer: Объект токенизатора, загруженный из файла.
        model: Предобученная модель нейросети.
        url (str): Ссылка на статью для классификации.

    Returns:
        str: Результат классификации с вероятностью.
    """
    text = get_parsed_html(url)
    sequence = tokenizer.texts_to_sequences([text])
    sequence = pad_sequences(sequence, maxlen=400)
    proba = model.predict(sequence)[0][0]
    return (
        "Cтатья относится к информационной безопасности с вероятностью "
        + str(proba)[:4]
    )


def get_parsed_html(link):
    """
    Получает HTML-документ по ссылке и извлекает текст из абзацев.

    Args:
        link (str): URL статьи.

    Returns:
        str: Объединённый текст всех абзацев, очищенный от спецсимволов.
    """
    doc = requests.get(link)
    soup = BeautifulSoup(doc.text, "html.parser")
    text = []
    for p in soup.find_all("p"):
        if len(p.text.split()) > 4:
            s = p.text
            s = s.replace("\xa0", " ")
            s = re.sub("\d\)", "", s).strip()
            text.append(s)
    return " ".join([x for x in text])
