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


last_for_triples = {}


class TemplatePostViewMixin:
    def post(self, request, *args, **kwargs):
        return super(TemplateView, self).render_to_response(
            self.get_context_data(**kwargs)
        )


class IndexView(TemplateView, TemplatePostViewMixin):
    template_name = "ie.html"
    last_for_ents: dict[Any, list] = {}

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
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
        result = {
            "show": True,
        }
        # views.py:50
        if self.request.user not in self.last_for_ents.keys():
            return result

        sent_index, sents, ents, description = self.last_for_ents[self.request.user]

        source = nm.Source.objects.get(description=description)

        sent_form = generate_sent_form(sent_index, sents, ents)
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
        result = {"show": True, "show_table": True}
        if "descriptions" in self.request.POST:
            result["source"] = self.request.POST.get("descriptions")
        if "get_from_base" in self.request.POST:
            source = gr.SourceRepository.get_by_url(result["source"])

            last_text = get_parsed_html(source.url)
            ents = get_ents(source.url, crf)
            sent_index = 0
            sents = sent_tokenize(last_text, language="russian")

            self.last_for_ents[self.request.user] = [
                sent_index,
                sents,
                ents,
                source.url,
            ]
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
        elif "add_ents" in self.request.POST:
            sent_index, sents, ents, description = self.last_for_ents[self.request.user]
            sent_form = generate_sent_form(sent_index, sents, ents)

            source = gr.SourceRepository.get_by_url(description)
            marked_ents = get_marked_ents(sent_index, sents, source)
            ents = filter_ents(marked_ents, sent_form[1])

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
        elif "next" in self.request.POST or "previous" in self.request.POST:
            sent_index, sents, ents, description = self.last_for_ents[self.request.user]
            source = gr.SourceRepository.get_by_url(description)
            sent_index += 1 if "next" in self.request.POST else -1
            if sent_index < 0 or sent_index >= len(sents):
                return result
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
    context = {}
    context["graph_obj"] = mark_safe(str(build_graph_object()))
    return render(request, "graph.html", context)


def build_graph_object():
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
    return JsonResponse(build_graph_object())


class AddView(TemplateView, TemplatePostViewMixin):
    template_name = "add.html"
    last_for_triples: dict[Any, list] = {}
    articles: dict[Any, int] = {}

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
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
        result = {}

        if self.request.user not in self.last_for_triples.keys():
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

            # preds = nm.Predicate.get_preds()
            sub = self.request.POST.get("sub")
            obj = self.request.POST.get("obj")
            pred = self.request.POST.get("pred")

            sent_form = generate_sent_form(sent_index, sents, [e[1] for e in ents])
            sent = sent_form[0]
            ents = list(enumerate(sent_form[1]))

            source = gr.SourceRepository.get_by_url(description)
            gr.TripleRepository.create_triple(
                sub, source, obj, pred, sent, self.request.user.pk
            )
            created = True
            # triple_score = nm.TripleScore(
            #     triple=triple, expert=self.request.user, score=True
            # )
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
        elif "next" in self.request.POST or "previous" in self.request.POST:
            sent_index, sents, ents, description = self.last_for_triples[
                self.request.user
            ]

            sent_index += 1 if "next" in self.request.POST else -1
            if sent_index < 0 or sent_index >= len(sents):
                return result

            source = gr.SourceRepository.get_by_url(description)
            ents_for_article = source.get_connected_entities(sents[sent_index])
            ents = list(enumerate(i["e"]["name"] for i in ents_for_article))

            self.last_for_triples[self.request.user][0] = sent_index
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
    template_name = "predicates.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            context |= self.process_post()
        return context

    def process_post(self):
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
