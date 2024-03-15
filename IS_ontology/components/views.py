from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from IS_ontology.Ie import graph_repositories as gr


# Create your views here.
def filter_view(request: HttpRequest) -> HttpResponse:
    users = get_user_model().objects.all()
    sources = [{'desc':i['n.description'], 'url':i['n.url']} for i in gr.SourceRepository.get_descriptions()]
    filter_type = request.htmx.current_url_abs_path
    return render(
        request, "components/filter.html", {"users": users, "sources": sources, "type": filter_type}
    )
