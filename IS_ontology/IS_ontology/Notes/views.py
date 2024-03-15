import json

from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Entity, EntScore, Source, Triple, TripleScore, Predicate
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404

from .serializers import NoteSerializer
from .models import model_Note
from .forms import InputNoteForm

from ..Ie import graph_repositories as gr


def index(request):
    return render(request, "index.html")


def main(request):
    return render(request, "main.html")


def fz(request):
    return render(request, "fz.html")


def pp(request):
    return render(request, "pp.html")


def fstek(request):
    return render(request, "fstek.html")


def terms(request):
    context = {
            "filter": mark_safe(
                json.dumps(
                    {
                        "users": request.POST.getlist("user[]", []),
                        "sources": request.POST.getlist("source[]", []),
                    }
                )
            )
        }

    return render(request, "terms.html", context)


def terms_table(request):
    ent_objects = gr.EntityRepository.filter(
        request.POST.getlist("users", None), request.POST.getlist("sources", None)
    )
    terms = []
    for elem in ent_objects:
        terms.append(
            {
                "term": elem[2]["name"],
                "doc": {"desc": elem[0]["description"], "url": elem[0]["url"]},
                "expert": gr.get_user_name(elem[2].get("user", "-1")),
                "date": elem[1]["date"],
            }
        )
    return render(request, "terms_table.html", {"terms": terms})


def triplets(request):
    return render(
        request,
        "triplets.html",
        {
            "filter": mark_safe(
                json.dumps(
                    {
                        "users": request.POST.getlist("user[]", []),
                        "sources": request.POST.getlist("source[]", []),
                    }
                )
            )
        },
    )


def triplet_table(request):
    triples = gr.TripleRepository.filter(
        request.POST.getlist("users", None), request.POST.getlist("sources", None)
    )
    tbl = [
        {
            "sub": t["e1"]["name"],
            "obj": t["e2"]["name"],
            "pred": t["t"]["name"],
            "source": {
                "desc": t["s"]["description"],
                "url": t["s"]["url"],
            },
            "expert": gr.get_user_name(t["t"]["user"]),
            "date": t["t"]["date"],
        }
        for t in triples
    ]
    return render(request, "triplet_table.html", {"triples": tbl})


def eng_rate(request):
    context = {}
    if request.method == "GET":
        expert_rates = []
        score_ent = Entity.objects.all()
        score_triples = Triple.objects.all()
        experts = []
        for score in score_ent:
            experts.append(score.expert.username)
        for score in score_triples:
            experts.append(score.expert.username)

        experts = list(set(experts))

        for expert in experts:
            count_ents, count_triples, rate = get_eng_rating(expert)
            print(experts, count_ents, count_triples, rate)
            expert_rates.append((expert, count_ents, count_triples, rate))
        expert_rates = sorted(expert_rates, key=lambda rate: rate[3], reverse=True)
        context["eng_rate"] = expert_rates
    return render(request, "eng_rate.html", context)


def exp_rate(request):
    context = {}
    if request.method == "GET":
        expert_rates = []
        score_ent = EntScore.objects.all()
        score_triples = TripleScore.objects.all()
        experts = []
        for score in score_ent:
            experts.append(score.expert.username)
        for score in score_triples:
            experts.append(score.expert.username)

        experts = list(set(experts))

        for expert in experts:
            count, rate = get_exp_rating(expert)
            print(experts, count, rate)
            expert_rates.append((expert, count, rate))
        expert_rates = sorted(expert_rates, key=lambda rate: rate[2], reverse=True)
        context["exp_rate"] = expert_rates
    return render(request, "exp_rate.html", context)


def terms_to_vote(request):
    context = {}
    if request.method == "GET":
        ents_table = get_ents_table(request.user)
        context["terms"] = ents_table
    if request.method == "POST" and "commit_votes" in request.POST:
        applyed_ents_for = []
        applyed_ents_against = []
        ents_table = get_ents_table(request.user)
        for i in range(len(ents_table)):
            applyed_ents_for.append(request.POST.get("for " + str(i)))
            applyed_ents_against.append(request.POST.get("against " + str(i)))

        if any(applyed_ents_for):
            for i in range(len(applyed_ents_for)):
                if applyed_ents_for[i] == "on":
                    ent = Entity.objects.get(
                        ent=ents_table[i][0],
                        source=Source.objects.filter(description=ents_table[i][1])[0],
                        expert=User.objects.filter(username=ents_table[i][2])[0],
                    )
                    score = EntScore(ent=ent, expert=request.user, score=True)
                    score.save()

        if any(applyed_ents_against):
            for i in range(len(applyed_ents_against)):
                if applyed_ents_against[i] == "on":
                    ent = Entity.objects.get(
                        ent=ents_table[i][0],
                        source=Source.objects.filter(description=ents_table[i][1])[0],
                        expert=User.objects.filter(username=ents_table[i][2])[0],
                    )
                    score = EntScore(ent=ent, expert=request.user, score=False)
                    score.save()

        ents_table = get_ents_table(request.user)
        context["terms"] = ents_table

    return render(request, "terms_to_vote.html", context)


def triples_to_vote(request):
    context = {}
    if request.method == "GET":
        triples_table = get_triples_table(request.user)
        context["triples"] = triples_table
    if request.method == "POST" and "commit_votes" in request.POST:
        applyed_triples_for = []
        applyed_triples_against = []
        triples_table = get_triples_table(request.user)
        for i in range(len(triples_table)):
            applyed_triples_for.append(request.POST.get("for " + str(i)))
            applyed_triples_against.append(request.POST.get("against " + str(i)))

        if any(applyed_triples_for):
            for i in range(len(applyed_triples_for)):
                if applyed_triples_for[i] == "on":
                    sub = Entity.objects.filter(
                        ent=triples_table[i][0],
                        source=Source.objects.filter(description=triples_table[i][3])[
                            0
                        ],
                    )[0]
                    obj = Entity.objects.filter(
                        ent=triples_table[i][1],
                        source=Source.objects.filter(description=triples_table[i][3])[
                            0
                        ],
                    )[0]
                    pred = Predicate.objects.filter(pred=triples_table[i][2])[0]

                    score = TripleScore(
                        triple=Triple.objects.filter(
                            sub=sub,
                            obj=obj,
                            predicate=pred,
                            source=Source.objects.filter(
                                description=triples_table[i][3]
                            )[0],
                            expert=User.objects.filter(username=triples_table[i][4])[0],
                        )[0],
                        expert=request.user,
                        score=True,
                    )
                    print(score.triple, score.expert, score.score)
                    score.save()
        if any(applyed_triples_against):
            for i in range(len(applyed_triples_against)):
                if applyed_triples_against[i] == "on":
                    sub = Entity.objects.filter(
                        ent=triples_table[i][0],
                        source=Source.objects.filter(description=triples_table[i][3])[
                            0
                        ],
                    )[0]
                    obj = Entity.objects.filter(
                        ent=triples_table[i][1],
                        source=Source.objects.filter(description=triples_table[i][3])[
                            0
                        ],
                    )[0]
                    pred = Predicate.objects.filter(pred=triples_table[i][2])[0]

                    score = TripleScore(
                        triple=Triple.objects.filter(
                            sub=sub,
                            obj=obj,
                            predicate=pred,
                            source=Source.objects.filter(
                                description=triples_table[i][3]
                            )[0],
                            expert=User.objects.filter(username=triples_table[i][4])[0],
                        )[0],
                        expert=request.user,
                        score=False,
                    )
                    print(score.triple, score.expert, score.score)
                    score.save()

        triples_table = get_triples_table(request.user)
        context["triples"] = triples_table
    return render(request, "triples_to_vote.html", context)


def rep_2021_jul(request):
    return render(request, "rep-2021-jul.html")


def rep_2021_aug(request):
    return render(request, "rep-2021-aug.html")


def companies(request):
    return render(request, "companies.html")


def members(request):
    return render(request, "members.html")


def view_StartPage(request):
    return render(request, "page_StartPage.html")


def get_ents_table(expert):
    table_ents = []
    ents = list(Entity.objects.all())
    distinct_ents = list(set([ent.ent for ent in ents]))
    ents_for_table = []
    for ent in distinct_ents:
        descriptions_experts = []
        ent_objects = list(Entity.objects.filter(ent=ent))
        for elem in ent_objects:
            descriptions_experts.append((elem.source.description, elem.expert.username))
        descriptions_experts = list(set(descriptions_experts))
        ents_for_table.append([ent, descriptions_experts])
    rows = []
    for elem in ents_for_table:
        for pair in elem[1]:
            rows.append((elem[0], pair[0], pair[1]))
    filtered_rows = filter_ent_rows(expert, rows)
    for i in range(len(filtered_rows)):
        table_ents.append(
            (
                filtered_rows[i][0],
                filtered_rows[i][1],
                filtered_rows[i][2],
                "for " + str(i),
                "against " + str(i),
            )
        )
    return table_ents


def get_triples_table(expert):
    table_triples = []
    triples = list(Triple.objects.all())
    distinct_triples = list(
        set([(triple.sub, triple.obj, triple.predicate) for triple in triples])
    )
    triples_for_table = []
    for triple in distinct_triples:
        descriptions_experts = []
        triple_objects = list(
            Triple.objects.filter(sub=triple[0], obj=triple[1], predicate=triple[2])
        )
        for elem in triple_objects:
            descriptions_experts.append((elem.source.description, elem.expert.username))
        descriptions_experts = list(set(descriptions_experts))
        triples_for_table.append([triple, descriptions_experts])
    rows = []
    for triple in triples_for_table:
        for pair in triple[1]:
            rows.append(
                (
                    triple[0][0].ent,
                    triple[0][1].ent,
                    triple[0][2].pred,
                    pair[0],
                    pair[1],
                )
            )
    filtered_rows = filter_triple_rows(expert, rows)
    for i in range(len(filtered_rows)):
        table_triples.append(
            (
                filtered_rows[i][0],
                filtered_rows[i][1],
                filtered_rows[i][2],
                filtered_rows[i][3],
                filtered_rows[i][4],
                "for " + str(i),
                "against " + str(i),
            )
        )
    return table_triples


def filter_ent_rows(expert, rows):
    expert_votes = list(EntScore.objects.filter(expert=expert))
    expert_votes_list = []
    for vote in expert_votes:
        expert_votes_list.append(
            (vote.ent.ent, vote.ent.source.description, vote.ent.expert.username)
        )
    filtered_rows = [row for row in rows if row not in expert_votes_list]
    return filtered_rows


def filter_triple_rows(expert, rows):
    expert_votes = list(TripleScore.objects.filter(expert=expert))
    expert_votes_list = []
    for vote in expert_votes:
        expert_votes_list.append(
            (
                vote.triple.sub.ent,
                vote.triple.obj.ent,
                vote.triple.predicate.pred,
                vote.triple.source.description,
                vote.triple.expert.username,
            )
        )
    filtered_rows = [row for row in rows if row not in expert_votes_list]
    return filtered_rows


def get_exp_rating(expert):
    user_score = 0
    user_ent_scores = {
        score.ent: score.score
        for score in EntScore.objects.filter(
            expert=User.objects.filter(username=expert)[0]
        )
    }
    user_triple_scores = {
        score.triple: score.score
        for score in TripleScore.objects.filter(
            expert=User.objects.filter(username=expert)[0]
        )
    }
    other_ent_scores = {}
    other_triple_scores = {}

    for ent in user_ent_scores.keys():
        other_ent_scores[ent] = EntScore.objects.filter(ent=ent)
    for ent in user_ent_scores.keys():
        score = 0
        for ent_score in other_ent_scores[ent]:
            if ent_score.score:
                score += 1
            else:
                score -= 1
        if score > 0 and user_ent_scores[ent]:
            user_score += 1
        elif score < 0 and user_ent_scores[ent]:
            user_score -= 1
        elif score < 0 and not user_ent_scores[ent]:
            user_score += 1
        elif score > 0 and not user_ent_scores[ent]:
            user_score -= 1

    for triple in user_triple_scores.keys():
        other_triple_scores[triple] = TripleScore.objects.filter(triple=triple)
    for triple in other_triple_scores.keys():
        score = 0
        for triple_score in other_triple_scores[triple]:
            if triple_score.score:
                score += 1
            else:
                score -= 1
        if score > 0 and user_triple_scores[triple]:
            user_score += 1
        elif score < 0 and user_triple_scores[triple]:
            user_score -= 1
        elif score < 0 and not user_triple_scores[triple]:
            user_score += 1
        elif score > 0 and not user_triple_scores[triple]:
            user_score -= 1
    return (len(user_ent_scores) + len(user_triple_scores), user_score * 1.0)


def get_eng_rating(engineer):
    user_score = 0
    user_ents = Entity.objects.filter(expert=User.objects.filter(username=engineer)[0])
    user_triples = Triple.objects.filter(
        expert=User.objects.filter(username=engineer)[0]
    )
    for ent in user_ents:
        ent_score = 0
        ent_scores = EntScore.objects.filter(ent=ent)
        for score in ent_scores:
            if score.score:
                ent_score += 1
            else:
                ent_score -= 1
        user_score += ent_score
    for triple in user_triples:
        triple_score = 0
        triple_scores = TripleScore.objects.filter(triple=triple)
        for score in triple_scores:
            if score.score:
                triple_score += 1
            else:
                triple_score -= 1
        user_score += triple_score * 1.5
    return (len(user_ents), len(user_triples), user_score)


def view_NotesList(request):
    objects_all = model_Note.objects.all()
    objects_list = []
    for obj in objects_all:
        if (obj.author == request.user) or (obj.status == "public"):
            objects_list.append(obj)

    paginator = Paginator(objects_list, 3)  # 3 articles on page
    page = request.GET.get("page")
    try:
        notes = paginator.page(page)
    except PageNotAnInteger:
        notes = paginator.page(1)
    except EmptyPage:
        notes = paginator.page(paginator.num_pages)
    return render(request, "page_NotesList.html", {"page": page, "notes": notes})


def view_NoteDetails(request, year, month, day, code):
    note = model_Note.objects.get(
        slug=code, publish__year=year, publish__month=month, publish__day=day
    )
    return render(request, "page_NoteDetails.html", {"note": note})


def view_InputNote(request):
    note = model_Note()
    saved = False
    if request.method == "POST":
        form = InputNoteForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            note = form.save(commit=False)
            note.slug = cd["title"].replace(" ", "").lower()
            note.author = request.user
            note.save()
            saved = True
            return render(
                request,
                "page_InputNote.html",
                {"note": note, "form": form, "saved": saved},
            )
        else:
            form = InputNoteForm()
            return render(
                request,
                "page_InputNote.html",
                {"note": note, "form": form, "saved": saved},
            )
    else:
        form = InputNoteForm()
        return render(
            request, "page_InputNote.html", {"note": note, "form": form, "saved": saved}
        )


class NoteAPIView(APIView):
    def get(self, request):
        notes = model_Note.objects.all()
        serializer = NoteSerializer(notes, many=True)
        return Response({"notes": serializer.data})

    def post(self, request):
        note_saved = None
        note = request.data.get("note")
        serializer = NoteSerializer(data=note)
        if serializer.is_valid(raise_exception=True):
            note_saved = serializer.save()
        return Response(
            {"success": "Note '{}' created successfully".format(note_saved.title)}
        )

    def put(self, request, year, month, day, code):
        note_saved = None
        saved_note = get_object_or_404(
            model_Note.objects.all(),
            slug=code,
            publish__year=year,
            publish__month=month,
            publish__day=day,
        )
        data = request.data.get("note")
        serializer = NoteSerializer(instance=saved_note, data=data, partial=True)
        if serializer.is_valid(raise_exception=True):
            note_saved = serializer.save()
        return Response(
            {"success": "Note '{}' updated successfully".format(note_saved.title)}
        )

    def delete(self, request, pk):
        note = get_object_or_404(model_Note.objects.all(), pk=pk)
        note.delete()
        return Response(
            {"message": "Note with id `{}` has been deleted.".format(pk)}, status=204
        )
