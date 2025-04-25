import pickle # Загрузка сериализованной CRF-модели
import re # Регулярные выражения для очистки текста

from bs4 import BeautifulSoup # Для парсинга HTML
from django.conf import settings # Настройки Django
from django.contrib.auth import get_user_model # Получение модели пользователя
from nltk.tokenize import sent_tokenize, word_tokenize  # Токенизация текста
from pymorphy2 import MorphAnalyzer # Морфологический разбор слов
import requests # Для HTTP-запросов

from ..Notes.models import Entity # Модель сущности из базы данных
from . import graph_repositories as gr # Работа с графовой БД


"""
Модуль `ai_utils.py` содержит утилиты для извлечения и обработки сущностей из текста на русском языке.
Используется в проекте IS-Ontology для работы с CRF-моделью, парсинга HTML-документов и взаимодействия с графовой БД.

Функциональность:
- Предобработка текста (токенизация, нормализация, лемматизация);
- Извлечение и фильтрация сущностей с помощью CRF-модели;
- Маркировка сущностей, связанных с источником;
- Получение текста с веб-страниц;
- Вспомогательные функции для формирования признаков токенов.
"""

# Путь к сохранённой CRF-модели
path = str(settings.BASE_DIR) + "/crf_model.pickle"

# Загрузка модели CRF из файла
with open(path, "rb") as f:
    crf = pickle.load(f)

# Морфологический анализатор для русского языка
morph = MorphAnalyzer()


def generate_sent_form(i, sents, ents):
    """
    Возвращает кортеж из предложения и списка сущностей, найденных в этом предложении.

    Функция нормализует (лемматизирует) слова в заданном предложении, а затем ищет в нем
    упоминания сущностей из переданного списка.

    Параметры:
    - i (int): индекс предложения в списке `sents`.
    - sents (list[str]): список предложений.
    - ents (list[str] | list[dict]): список сущностей в виде строк или словарей (с ключом 'e' -> {'name': ...}).

    Возвращает:
    - tuple[str, list[str]]: оригинальное предложение и список сущностей, упомянутых в нем (по леммам).
    """
    ents_in_sent = []
    normal_sent = []

    # Лемматизация каждого слова в предложении
    for word in word_tokenize(sents[i], language="russian"):
        normal_sent.append(morph.normal_forms(word)[0])
    normal_sent = " ".join(normal_sent)

    # Поиск упоминаний сущностей в нормализованном предложении
    for ent in ents:
        if isinstance(ent, dict):
            ent=ent['e']['name']
        if normal_sent.find(ent) != -1:
            ents_in_sent.append(ent)

    return (sents[i], ents_in_sent)

# TODO: Устаревшая версия. Использует Django ORM.
# Используется только если нужно работать напрямую с Entity из SQL-базы.
# Актуальная версия ниже — через SourceRepository и графовую БД.
def get_marked_ents(sent_index, sents, source):
    """
    Возвращает список размеченных сущностей, найденных в заданном предложении.

    Сначала извлекает все сущности, связанные с источником (source), из базы данных.
    Затем нормализует (лемматизирует) предложение и ищет в нём упоминания этих сущностей.

    P.S. Каждой найденной сущности сопоставляется имя пользователя-эксперта, который её разметил.

    Параметры:
    - sent_index (int): индекс предложения в списке `sents`.
    - sents (list[str]): список предложений.
    - source (Source): объект источника, связанный с сущностями.

    Возвращает:
    - list[tuple[str, str]]: список кортежей (сущность, имя эксперта), найденных в предложении.
    """
    # Получаем сущности, связанные с источником
    ents = Entity.objects.filter(source=source)
    ents_new = [] # Список [имя_сущности, имя_эксперта]
    marked_ents = []
    for ent in ents:
        ents_new.append([ent.ent, ent.expert.username])

    # Лемматизация предложения
    sent = sents[sent_index]
    normal_sent = []
    for word in word_tokenize(sent, language="russian"):
        normal_sent.append(morph.normal_forms(word)[0])
    normal_sent = " ".join(word for word in normal_sent)

    # Поиск сущностей в нормализованном предложении
    for ent in ents_new:
        if normal_sent.find(ent[0]) != -1:
            marked_ents.append((ent[0], ent[1]))
    return marked_ents


def filter_ents(marked_ents, ents_in_sent):
    """
    Фильтрует сущности, которые уже были размечены экспертами.

    Из списка всех найденных в предложении сущностей (`ents_in_sent`)
    исключаются те, которые уже есть в списке размеченных (`marked_ents`).

    Параметры:
    - marked_ents (list[tuple[str, str]]): список размеченных сущностей (имя сущности, имя эксперта).
    - ents_in_sent (list[str]): список всех сущностей, обнаруженных в предложении.

    Возвращает:
    - list[str]: список сущностей, которые ещё не размечены.
    """
    # Выделяем только имена сущностей из размеченных кортежей
    marked_ents = [m[0] for m in marked_ents]

    # Исключаем из общего списка те сущности, которые уже размечены
    return [ent for ent in ents_in_sent if ent not in marked_ents]


def get_marked_ents(sent_index: int, sents: list[str], source: gr.SourceRepository):
    ents = source.get_connected_entities(sents[sent_index])
    ents_new = []
    marked_ents = []
    for ent in ents:
        user_pk = int(ent['e'].get('user', '-1'))
        user = get_user_model().objects.get(pk=user_pk).get_username() if user_pk >= 0 else 'unknown'
        ents_new.append([ent['e']['name'], user])
    sent = sents[sent_index]
    normal_sent = []
    for word in word_tokenize(sent, language="russian"):
        normal_sent.append(morph.normal_forms(word)[0])
    normal_sent = " ".join(word for word in normal_sent)
    for ent in ents_new:
        if normal_sent.find(ent[0]) != -1:
            marked_ents.append((ent[0], ent[1]))
    return marked_ents


def get_parsed_html(link: str) -> str:
    """
    Загружает HTML-страницу по ссылке и извлекает из неё текст.

    Используется для предварительной подготовки текста перед токенизацией и
    извлечением сущностей. Извлекаются только абзацы (`<p>`) длиной более 4 слов.
    Также производится очистка текста от неразрывных пробелов и некоторых маркеров.

    Параметры:
    - link (str): URL-адрес страницы, с которой нужно извлечь текст.

    Возвращает:
    - str: объединённый текст из всех подходящих абзацев.
    """
    # Загружаем страницу по ссылке
    doc = requests.get(link)

    # Парсим HTML
    soup = BeautifulSoup(doc.text, "html.parser")
    text = []

    # Проходим по всем абзацам
    for p in soup.find_all("p"):
        # Отбираем только те, где больше 4 слов
        if len(p.text.split()) > 4:
            s = p.text

            # Удаляем неразрывные пробелы и маркеры вида "1)", "2)" и т.п.
            s = s.replace("\xa0", " ")
            s = re.sub(r"\d\)", "", s).strip()
            text.append(s)
    
    # Объединяем отфильтрованные абзацы в один текст
    return " ".join([p for p in text])


"""
Эта функция — связывающее звено между интернет-страницей и моделью CRF. 
Очень удобна для извлечения сущностей "одной строкой": get_ents(url, crf).
"""
def get_ents(link, crf):
    """
    Загружает HTML-документ по ссылке, извлекает текст, разбивает его на предложения
    и передаёт в CRF-модель для извлечения сущностей.

    Параметры:
    - link (str): URL-адрес страницы, откуда извлекается текст.
    - crf: обученная модель CRF (Conditional Random Fields) для NER-задачи.

    Возвращает:
    - list[str] | str: список уникальных сущностей, найденных моделью,
      или строка "Сущности не были найдены." если список пуст.
    """
    # Получение очищенного текста со страницы
    text = get_parsed_html(link)

    # Разделение текста на предложения
    sents = sent_tokenize(text, language="russian")

    # Предсказание сущностей из предложений
    return predict_ents(sents, crf)


"""
Эта функция делает всё "тяжёлое" извлечение: от разбора до формирования BIO-маркировки. 
Важно, что она нормализует слова перед тем, как вернуть сущности — это позволяет избежать дублирования 
(например, "базы данных" и "базу данных").
"""
def predict_ents(sents, crf):
    """
    Обрабатывает список предложений и извлекает из них именованные сущности с помощью CRF-модели.

    Для каждого предложения:
    - выполняется токенизация и морфологический разбор;
    - формируются признаки (features) для каждого токена;
    - CRF-модель предсказывает BIO-теги для каждого слова;
    - из тегов извлекаются сущности, при этом слова нормализуются.

    Параметры:
    - sents (list[str]): список предложений.
    - crf: обученная модель CRF, обученная на задаче NER (распознавание сущностей).

    Возвращает:
    - list[str] или str: список уникальных сущностей или строка "Сущности не были найдены."
    """
    all_ents = [] # Сущности по каждому предложению
    ents_all = [] # Уникальные сущности по всему тексту
    for sent in sents:
        # Токенизация
        tokenized_sent = word_tokenize(sent, language="russian")

        # Получение POS-тегов и лемм
        sent_pos = [
            (word, str(morph.parse(word)[0][1]).split(",")[0])
            for word in tokenized_sent
        ]

        # Формирование признаков для каждого токена
        tokens = [extractWordFeatures(sent_pos, i) for i in range(len(sent_pos))]

        # Предсказание тегов BIO для токенов
        preds = crf.predict([tokens])[0]

        ents = []
        temp = []
        for i in range(len(preds)):
            if preds[i] == "B-TERM":
                if len(temp) != 0:
                    # Завершаем предыдущую сущность
                    ents.append(
                        " ".join(morph.normal_forms(token)[0] for token in temp)
                    )
                    temp = [tokenized_sent[i]]  # Начинаем новую сущность
                else:
                    temp = [tokenized_sent[i]]

            elif preds[i] == "I-TERM" and len(temp) != 0:
                temp.append(tokenized_sent[i])

            elif preds[i] == "O" and len(temp) != 0:
                # Завершаем текущую сущность
                ents.append(" ".join(morph.normal_forms(token)[0] for token in temp))
                temp = []
        all_ents.append(ents)

        # Уникальные сущности
        for elem in all_ents:
            for ent in elem:
                if ent not in ents_all:
                    ents_all.append(ent)
    if ents_all:
        return ents_all
    else:
        return "Сущности не были найдены."


def extractWordFeatures(sentence, i):
    """
    Формирует словарь признаков (features) для i-го слова в предложении.

    Используется для подачи в CRF-модель. Признаки включают:
    - морфологические и позиционные характеристики текущего слова;
    - признаки соседних слов (предыдущего и следующего), если они есть;
    - признаки длины, регистра, окончания и т.д.

    Параметры:
    - sentence (list[tuple[str, str]]): список пар (слово, POS-тег), полученных из морфоразбора.
    - i (int): индекс слова в предложении, для которого формируются признаки.

    Возвращает:
    - dict: словарь с признаками для текущего слова.
    """
    Token = sentence[i][0] # Само слово
    POS = sentence[i][1] # Его часть речи

    featureDict = {
        "POS[:2]": POS[:2],  # Первые 2 символа POS
        "POS": POS, # Полный POS-тег
        "Token.isdigit()": Token.isdigit(), # Является ли числом
        "Token.istitle()": Token.istitle(), # Начинается ли с заглавной
        "Token.isupper()": Token.isupper(), # Все ли буквы заглавные
        "Token[-2:]": Token[-2:], # Последние 2 символа
        "Token[-3:]": Token[-3:], # Последние 3 символа
        "Token.lower()": Token.lower(), # Слово в нижнем регистре
        "bias": 1.0, # Смещение — для стабильности модели
    }

    # Признаки предыдущего слова, если оно есть
    if i > 1:
        previousWord = sentence[i - 1][0]
        previousPosTag = sentence[i - 1][1]

        # Добавляем признаки предыдущего слова и его части речи
        featureDict.update(
            {
                "-1:Token.lower()": previousWord.lower(), # Слово в нижнем регистре
                "-1:Token.istitle()": previousWord.istitle(), # Начинается ли с заглавной
                "-1:Token.isupper()": previousWord.isupper(), # Все ли буквы заглавные
                "-1:POS": previousPosTag, # Полный POS-тег
                "-1:POS[:2]": previousPosTag[:2], # Первые два символа POS
            }
        )

    # Если предыдущее слово отсутствует — начало предложения
    else:
        featureDict["BOS"] = True # Признак начала предложения (Beginning of Sentence)

     # Признаки следующего слова, если оно есть
    if i < len(sentence) - 1:
        nextWord = sentence[i + 1][0]
        nextPos = sentence[i + 1][1]
        # Добавляем признаки следующего слова и его части речи
        featureDict.update(
            {
                "+1:Token.lower()": nextWord.lower(), # Слово в нижнем регистре
                "+1:Token.istitle()": nextWord.istitle(), # Начинается ли с заглавной
                "+1:Token.isupper()": nextWord.isupper(), # Все ли буквы заглавные
                "+1:POS": nextPos,  # Полный POS-тег
                "+1:POS[:2]": nextPos[:2], # Первые два символа POS
            }
        )

    # Если следующего слова нет — конец предложения
    else:
        featureDict["EOS"] = True # Признак конца предложения (End of Sentence)

    return featureDict
