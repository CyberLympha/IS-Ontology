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


path = str(settings.BASE_DIR) + "/crf_model.pickle"

with open(path, "rb") as f:
    crf = pickle.load(f)

morph = MorphAnalyzer()


def generate_sent_form(i, sents, ents):
    ents_in_sent = []
    normal_sent = []
    for word in word_tokenize(sents[i], language="russian"):
        normal_sent.append(morph.normal_forms(word)[0])
    normal_sent = " ".join(normal_sent)
    for ent in ents:
        if isinstance(ent, dict):
            ent=ent['e']['name']
        if normal_sent.find(ent) != -1:
            ents_in_sent.append(ent)
    return (sents[i], ents_in_sent)


def get_marked_ents(sent_index, sents, source):
    ents = Entity.objects.filter(source=source)
    ents_new = []
    marked_ents = []
    for ent in ents:
        ents_new.append([ent.ent, ent.expert.username])
    sent = sents[sent_index]
    normal_sent = []
    for word in word_tokenize(sent, language="russian"):
        normal_sent.append(morph.normal_forms(word)[0])
    normal_sent = " ".join(word for word in normal_sent)
    for ent in ents_new:
        if normal_sent.find(ent[0]) != -1:
            marked_ents.append((ent[0], ent[1]))
    return marked_ents


def filter_ents(marked_ents, ents_in_sent):
    marked_ents = [m[0] for m in marked_ents]
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
    doc = requests.get(link)
    soup = BeautifulSoup(doc.text, "html.parser")
    text = []
    for p in soup.find_all("p"):
        if len(p.text.split()) > 4:
            s = p.text
            s = s.replace("\xa0", " ")
            s = re.sub(r"\d\)", "", s).strip()
            text.append(s)
    return " ".join([p for p in text])


def get_ents(link, crf):
    text = get_parsed_html(link)
    sents = sent_tokenize(text, language="russian")
    return predict_ents(sents, crf)


def predict_ents(sents, crf):
    all_ents = []
    ents_all = []
    for sent in sents:
        tokenized_sent = word_tokenize(sent, language="russian")
        sent_pos = [
            (word, str(morph.parse(word)[0][1]).split(",")[0])
            for word in tokenized_sent
        ]
        tokens = [extractWordFeatures(sent_pos, i) for i in range(len(sent_pos))]
        preds = crf.predict([tokens])[0]

        ents = []
        temp = []
        for i in range(len(preds)):
            if preds[i] == "B-TERM":
                if len(temp) != 0:
                    ents.append(
                        " ".join(morph.normal_forms(token)[0] for token in temp)
                    )
                    temp = [tokenized_sent[i]]
                else:
                    temp = [tokenized_sent[i]]

            elif preds[i] == "I-TERM" and len(temp) != 0:
                temp.append(tokenized_sent[i])

            elif preds[i] == "O" and len(temp) != 0:
                ents.append(" ".join(morph.normal_forms(token)[0] for token in temp))
                temp = []
        all_ents.append(ents)
        for elem in all_ents:
            for ent in elem:
                if ent not in ents_all:
                    ents_all.append(ent)
    if ents_all:
        return ents_all
    else:
        return "Сущности не были найдены."


def extractWordFeatures(sentence, i):
    Token = sentence[i][0]
    POS = sentence[i][1]

    featureDict = {
        "POS[:2]": POS[:2],
        "POS": POS,
        "Token.isdigit()": Token.isdigit(),
        "Token.istitle()": Token.istitle(),
        "Token.isupper()": Token.isupper(),
        "Token[-2:]": Token[-2:],
        "Token[-3:]": Token[-3:],
        "Token.lower()": Token.lower(),
        "bias": 1.0,
    }

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
        featureDict["BOS"] = True

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
        featureDict["EOS"] = True

    return featureDict
