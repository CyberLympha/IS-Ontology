import pickle
import re

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth import get_user_model
from nltk.tokenize import sent_tokenize, word_tokenize
from pymorphy2 import MorphAnalyzer
import requests

from ..Notes.models import Entity
from . import graph_repositories as gr


"""
ai_utils.py

Модуль вспомогательных функций для обработки текстов статей и работы с сущностями.

Содержит:
    - Загрузка и использование CRF-модели для разметки сущностей.
    - Нормализация текста и парсинг HTML-страниц.
    - Генерация формы предложений для отображения сущностей.
    - Фильтрация сущностей и разметка найденных сущностей.
    - Выделение признаков для токенов при работе с моделью.

Особенности:
    - Используется морфологический разбор текста с помощью pymorphy2.
    - Интеграция с Django ORM для работы с сущностями в базе данных.
    - Использование внешних библиотек: BeautifulSoup, NLTK, Requests.
"""

# Путь к обученной модели CRF для распознавания сущностей
path = str(settings.BASE_DIR) + "/crf_model.pickle"

# Загружаем обученную CRF-модель из файла
with open(path, "rb") as f:
    crf = pickle.load(f)

# Инициализация морфологического анализатора для нормализации текста
morph = MorphAnalyzer()


def generate_sent_form(i, sents, ents):
    """
    Формирует предложение и список сущностей, присутствующих в нём.

    Описание процесса:
        - Нормализует текст предложения (приведение слов к начальной форме).
        - Проверяет наличие сущностей в нормализованном предложении.
        - Возвращает оригинальное предложение и список сущностей, найденных в нём.

    Args:
        i (int): Индекс предложения в списке.
        sents (list[str]): Список предложений текста.
        ents (list[str] or list[dict]): Список сущностей или словарей с сущностями.

    Returns:
        tuple:
            - str: Оригинальный текст предложения.
            - list[str]: Список найденных в предложении сущностей.
    """
    ents_in_sent = []
    normal_sent = []

    # Нормализуем слова в предложении
    for word in word_tokenize(sents[i], language="russian"):
        normal_sent.append(morph.normal_forms(word)[0])
    normal_sent = " ".join(normal_sent)

    # Проверяем наличие сущностей в нормализованном предложении
    for ent in ents:
        if isinstance(ent, dict):
            ent=ent['e']['name']
        if normal_sent.find(ent) != -1:
            ents_in_sent.append(ent)
    return (sents[i], ents_in_sent)


def get_marked_ents(sent_index, sents, source):
    """
    Находит сущности, которые уже связаны с данным предложением в базе данных.

    Описание процесса:
        - Извлекает все сущности, связанные с указанным источником.
        - Нормализует текст предложения.
        - Проверяет, какие из сущностей встречаются в предложении.
        - Возвращает список найденных сущностей с именами экспертов.

    Args:
        sent_index (int): Индекс предложения в списке.
        sents (list[str]): Список предложений текста.
        source (Source): Объект источника, связанный с сущностями.

    Returns:
        list[tuple[str, str]]:
            Список кортежей (название сущности, имя эксперта), найденных в предложении.
    """
    # Получаем все сущности, связанные с источником
    ents = Entity.objects.filter(source=source)
    ents_new = [] # Новый список с сущностями и их экспертами
    marked_ents = []  # Итоговый список найденных сущностей

    # Собираем пары (сущность, эксперт)
    for ent in ents:
        ents_new.append([ent.ent, ent.expert.username])

    # Нормализуем текст предложения
    sent = sents[sent_index]
    normal_sent = []
    for word in word_tokenize(sent, language="russian"):
        normal_sent.append(morph.normal_forms(word)[0])
    normal_sent = " ".join(word for word in normal_sent)

    # Ищем, какие сущности присутствуют в нормализованном предложении
    for ent in ents_new:
        if normal_sent.find(ent[0]) != -1:
            marked_ents.append((ent[0], ent[1]))
    return marked_ents


def filter_ents(marked_ents, ents_in_sent):
    """
    Фильтрует сущности, оставляя только новые (ещё не размеченные).

    Описание процесса:
        - Получает список уже размеченных сущностей.
        - Исключает их из списка сущностей, найденных в текущем предложении.

    Args:
        marked_ents (list[tuple[str, str]]): Список размеченных сущностей (название, эксперт).
        ents_in_sent (list[str]): Список всех сущностей, найденных в предложении.

    Returns:
        list[str]: Список новых сущностей, ещё не отмеченных пользователем.
    """
    # Извлекаем только имена размеченных сущностей
    marked_ents = [m[0] for m in marked_ents]

    # Возвращаем сущности, которые ещё не размечены
    return [ent for ent in ents_in_sent if ent not in marked_ents]


def get_marked_ents(sent_index: int, sents: list[str], source: gr.SourceRepository):
    """
    Находит сущности, связанные с предложением через графовую базу данных (Neo4j).

    Описание процесса:
        - Запрашивает связанные сущности через SourceRepository.get_connected_entities().
        - Нормализует текст предложения.
        - Проверяет, какие сущности содержатся в нормализованном предложении.
        - Определяет пользователя (эксперта), который добавил сущность.

    Args:
        sent_index (int): Индекс предложения в списке.
        sents (list[str]): Список предложений текста.
        source (SourceRepository): Объект источника для запроса связанных сущностей.

    Returns:
        list[tuple[str, str]]:
            Список кортежей (название сущности, имя эксперта), найденных в предложении.
    """
    # Запрашиваем связанные сущности для данного предложения из графа
    ents = source.get_connected_entities(sents[sent_index])
    ents_new = []  # Новый список (сущность, эксперт)
    marked_ents = [] # Итоговый список сущностей, найденных в предложении

    # Обрабатываем каждую сущность: определяем её имя и эксперта
    for ent in ents:
        user_pk = int(ent['e'].get('user', '-1'))
        user = get_user_model().objects.get(pk=user_pk).get_username() if user_pk >= 0 else 'unknown'
        ents_new.append([ent['e']['name'], user])
    sent = sents[sent_index]
    normal_sent = []

    # Нормализуем текст предложения
    for word in word_tokenize(sent, language="russian"):
        normal_sent.append(morph.normal_forms(word)[0])
    normal_sent = " ".join(word for word in normal_sent)

    # Проверяем, какие сущности содержатся в нормализованном предложении
    for ent in ents_new:
        if normal_sent.find(ent[0]) != -1:
            marked_ents.append((ent[0], ent[1]))

    return marked_ents


def get_parsed_html(link: str) -> str:
    """
    Загружает HTML-страницу по ссылке и извлекает из неё чистый текст.

    Описание процесса:
        - Делает HTTP-запрос по переданной ссылке.
        - Ищет все абзацы текста (<p> теги).
        - Отбирает абзацы, содержащие более 4 слов.
        - Очищает текст: убирает специальные символы и лишние пробелы.
        - Объединяет текст в одну строку.

    Args:
        link (str): URL-адрес страницы для загрузки.

    Returns:
        str: Очищенный текст, извлечённый из HTML-документа.
    """

    # Загружаем страницу по ссылке
    doc = requests.get(link)

    # Парсим HTML-контент с помощью BeautifulSou
    soup = BeautifulSoup(doc.text, "html.parser")
    
    text = []

    # Ищем все теги <p> (абзацы)
    for p in soup.find_all("p"):
        # Берем только те абзацы, где больше 4 слов
        if len(p.text.split()) > 4:
            
            s = p.text

            # Очищаем текст абзаца
            s = s.replace("\xa0", " ")  # Убираем неразрывные пробелы
            s = re.sub(r"\d\)", "", s).strip() # Убираем маркеры вроде "1)" или "2)"
            text.append(s)

    # Склеиваем все отобранные абзацы в один текст
    return " ".join([p for p in text])


def get_ents(link, crf):
    """
    Извлекает сущности из текста по ссылке с использованием CRF-модели.

    Описание процесса:
        - Загружает HTML-страницу и очищает её текст через get_parsed_html().
        - Разбивает текст на предложения.
        - Предсказывает сущности в каждом предложении с помощью CRF-модели.

    Args:
        link (str): URL-адрес страницы для анализа.
        crf (sklearn_crfsuite.CRF): Загруженная модель CRF для извлечения сущностей.

    Returns:
        list[str] или str:
            Список найденных сущностей или сообщение "Сущности не были найдены.".
    """

    # Загружаем и очищаем текст страницы
    text = get_parsed_html(link)

    # Разбиваем текст на отдельные предложения
    sents = sent_tokenize(text, language="russian")

    # Предсказываем сущности в предложениях с помощью CRF
    return predict_ents(sents, crf)


def predict_ents(sents, crf):
    """
    Предсказывает сущности в списке предложений с использованием CRF-модели.

    Описание процесса:
        - Токенизирует каждое предложение на слова.
        - Добавляет части речи для каждого токена.
        - Извлекает признаки для CRF-модели.
        - Предсказывает разметку токенов (B-TERM, I-TERM, O).
        - Собирает выделенные сущности из предсказанных меток.
        - Нормализует найденные сущности.

    Args:
        sents (list[str]): Список предложений.
        crf (sklearn_crfsuite.CRF): Обученная CRF-модель.

    Returns:
        list[str] или str:
            Список уникальных сущностей или сообщение "Сущности не были найдены.".
    """
    all_ents = [] # Список всех найденных сущностей по каждому предложению
    ents_all = [] # Уникальные сущности без повторов

    for sent in sents:
        # Токенизация предложения
        tokenized_sent = word_tokenize(sent, language="russian")
        
        # Определяем часть речи для каждого токена
        sent_pos = [
            (word, str(morph.parse(word)[0][1]).split(",")[0])
            for word in tokenized_sent
        ]

        # Извлекаем признаки для каждого токена
        tokens = [extractWordFeatures(sent_pos, i) for i in range(len(sent_pos))]

        # Получаем предсказания меток для токенов
        preds = crf.predict([tokens])[0]

        ents = [] # Временный список сущностей в текущем предложении
        temp = [] # Буфер для сбора сущностей, состоящих из нескольких слов

        for i in range(len(preds)):
            if preds[i] == "B-TERM":
                if len(temp) != 0:
                    # Завершаем предыдущую сущность
                    ents.append(
                        " ".join(morph.normal_forms(token)[0] for token in temp)
                    )
                    temp = [tokenized_sent[i]]
                else:
                    temp = [tokenized_sent[i]]

            elif preds[i] == "I-TERM" and len(temp) != 0:
                temp.append(tokenized_sent[i])

            elif preds[i] == "O" and len(temp) != 0:
                # Завершаем сущность при выходе из разметки
                ents.append(" ".join(morph.normal_forms(token)[0] for token in temp))
                temp = []

        all_ents.append(ents)

        # Добавляем уникальные сущности
        for elem in all_ents:
            for ent in elem:
                if ent not in ents_all:
                    ents_all.append(ent)

    # Возвращаем результат
    if ents_all:
        return ents_all
    else:
        return "Сущности не были найдены."


def extractWordFeatures(sentence, i):
    """
    Извлекает признаки (features) для токена в предложении для подачи в CRF-модель.

    Описание процесса:
        - Извлекает базовые характеристики токена (форма записи, суффиксы, часть речи).
        - Добавляет характеристики соседних токенов (предыдущего и следующего).
        - Помечает начало или конец предложения специальными признаками (BOS/EOS).

    Args:
        sentence (list[tuple[str, str]]): Список токенов с их частями речи [(токен, POS), ...].
        i (int): Индекс токена в предложении.

    Returns:
        dict: Словарь признаков для выбранного токена.
    """
    Token = sentence[i][0]
    POS = sentence[i][1]

    # Базовые признаки токена
    featureDict = {
        "POS[:2]": POS[:2], # Первые две буквы части речи
        "POS": POS, # Полная часть речи
        "Token.isdigit()": Token.isdigit(), # Является ли токен числом
        "Token.istitle()": Token.istitle(), # Начинается ли токен с заглавной буквы
        "Token.isupper()": Token.isupper(), # Является ли токен полностью заглавным
        "Token[-2:]": Token[-2:], # Последние 2 буквы токена
        "Token[-3:]": Token[-3:], # Последние 3 буквы токена
        "Token.lower()": Token.lower(), # Приведение токена к нижнему регистру
        "bias": 1.0,  # Базовый признак смещения
    }

    # Признаки предыдущего токена (если он существует)
    if i > 1:
        previousWord = sentence[i - 1][0]
        previousPosTag = sentence[i - 1][1]

        # Add characteristics of the sentence's previous word and POS to the feature dictionary
        featureDict.update(
            {
                "-1:Token.lower()": previousWord.lower(),
                "-1:Token.istitle()": previousWord.istitle(),
                "-1:Token.isupper()": previousWord.isupper(),
                "-1:POS": previousPosTag,
                "-1:POS[:2]": previousPosTag[:2],
            }
        )

    # Add "Beginning of Sentence" at the start of the dictionary
    else:
        # Признак начала предложения
        featureDict["BOS"] = True

    # Признаки следующего токена (если он существует)
    if i < len(sentence) - 1:
        nextWord = sentence[i + 1][0]
        nextPos = sentence[i + 1][1]

        # Add characteristics of the sentence's previous next and POS to the feature dictionary
        featureDict.update(
            {
                "+1:Token.lower()": nextWord.lower(),
                "+1:Token.istitle()": nextWord.istitle(),
                "+1:Token.isupper()": nextWord.isupper(),
                "+1:POS": nextPos,
                "+1:POS[:2]": nextPos[:2],
            }
        )

    else:
        # Признак конца предложения
        featureDict["EOS"] = True

    return featureDict


# ------------------------------------------------------------------------------
# Замечания и предложения по улучшению кода и логики

"""
1. Дублирование кода нормализации текста:
   - Код нормализации предложения повторяется в нескольких функциях.
   - Решение: вынести нормализацию текста в отдельную функцию (например, normalize_sentence).

2. Смешение логики получения сущностей:
   - Функции get_marked_ents используют две разные логики (через ORM и через граф).
   - Решение: явно разделить эти функции или унифицировать подход к получению сущностей.

3. Отсутствие обработки ошибок при сетевых запросах:
   - В get_parsed_html нет обработки ошибок при запросах (requests.get).
   - Решение: добавить try-except с обработкой ошибок HTTP (например, requests.exceptions.RequestException).

4. Возможное падение при загрузке модели:
   - При загрузке файла crf_model.pickle не предусмотрена обработка ошибок FileNotFoundError или UnpicklingError.
   - Решение: обернуть открытие файла в блок try-except.

5. Улучшение производительности:
   - В predict_ents возможно оптимизировать двойной проход по all_ents для формирования списка ents_all.
   - Решение: использовать set для быстрого отсечения повторов.

6. Плохая поддержка мультиязычности:
   - В функциях предполагается работа только с русским языком.
   - Решение: сделать язык параметром функций (например, по умолчанию "russian").

7. Отсутствие логирования:
   - Нет логирования важных событий (например, ошибок сетевых запросов, проблем с разбором текста).
   - Решение: добавить базовое логирование через стандартный модуль logging.

8. Структура признаков в extractWordFeatures:
   - Возможна генерализация признаков, например, через списки правил вместо жёстко прописанных полей.
   - Решение: вынести схему генерации признаков в отдельную структуру для удобства расширения модели.

9. Разделение ответственности:
   - Сейчас функции перемешивают "низкоуровневую обработку текста" и "логику сущностей".
   - Решение: разделить модули на "текстовые утилиты" и "графовые/модельные утилиты".

10. Улучшение читаемости:
    - Некоторые функции (например, predict_ents) перегружены вложенными циклами.
    - Решение: рефакторинг крупных функций через дополнительные вспомогательные методы.

"""
# ------------------------------------------------------------------------------
