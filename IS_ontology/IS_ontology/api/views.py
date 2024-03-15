from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from ..Ie import graph_repositories

@api_view(["POST"])
def get_terms(request):
    ent_objects = graph_repositories.EntityRepository.filter(
        request.POST.getlist("users", None), request.POST.getlist("sources", None)
    )
    terms = []
    for elem in ent_objects:
        terms.append(
            {
                "term": elem[2]["name"],
                "doc": {"desc": elem[0]["description"], "url": elem[0]["url"]},
                "expert": graph_repositories.get_user_name(elem[2].get("user", "-1")),
                "date": str(elem[1]["date"]),
            }
        )
    return Response({"terms": terms})

@api_view(["POST"])
def get_triples(request):
    ent_objects = graph_repositories.TripleRepository.filter(
        request.POST.getlist("users", None), request.POST.getlist("sources", None)
    )
    terms = []
    for elem in ent_objects:
        terms.append(
            {
                "left": elem['e1']["name"],
                "rel": elem['t']['name'],
                "right": elem['e2']['name'],
                "doc": {"desc": elem['s']["description"], "url": elem['s']["url"]},
                "expert": graph_repositories.get_user_name(elem['t'].get("user", "-1")),
                "date": str(elem['t']["date"]),
            }
        )
    return Response({"triples": terms})

@api_view(["GET"])
def user_info(request: Request) -> Response:
    user = request.user
    return Response({
        'username': user.username,
        'repr': repr(user)
    })
