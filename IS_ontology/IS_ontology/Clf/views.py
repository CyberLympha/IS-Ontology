import os

from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import render
import requests
import re
from bs4 import BeautifulSoup
import pickle
# from tensorflow.keras.models import Sequential
# from tensorflow.keras.layers import Dense, Embedding, LSTM
# from tensorflow.keras.preprocessing.sequence import pad_sequences
from django.conf import settings
import pickle

from ..Ie.graph_repositories import SourceRepository
from ..Notes.models import Source, Text


tokenizer_path = os.path.join(str(settings.BASE_DIR), "tokenizer.pickle")

model_path = os.path.join(str(settings.BASE_DIR), "clf_is.h5")
print(model_path)

# with open(tokenizer_path, "rb") as handle:
#     tokenizer = pickle.load(handle)


# classifier = Sequential()
# classifier.add(Embedding(20000, 64, input_length=400))
# classifier.add(LSTM(64))
# classifier.add(Dense(1, activation="sigmoid"))
# classifier.compile(
#     optimizer="adam", loss="binary_crossentropy", metrics=["AUC", "accuracy"]
# )

# classifier.load_weights(model_path)

last = {}


def index(request: WSGIRequest):
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
    try:
        if str(requests.get(url)) != "<Response [404]>":
            return True
        return False
    except requests.exceptions.SSLError:
        return False


def check_text(text):
    if len(text) != 0:
        return True
    return False


def check_source(url: str, description: str, user) -> tuple[str, str]:
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
    text = get_parsed_html(url)
    sequence = tokenizer.texts_to_sequences([text])
    sequence = pad_sequences(sequence, maxlen=400)
    proba = model.predict(sequence)[0][0]
    return (
        "Cтатья относится к информационной безопасности с вероятностью "
        + str(proba)[:4]
    )


def get_parsed_html(link):
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
