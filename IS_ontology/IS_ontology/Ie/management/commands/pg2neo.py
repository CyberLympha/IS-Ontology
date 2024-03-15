from typing import Any
from django.core.management.base import BaseCommand
from IS_ontology.Notes import models as m
from IS_ontology.Ie import graph_repositories as gr

class Command(BaseCommand):
    help = "migrate postgres data to neo4j"

    def handle(self, *args: Any, **options: Any) -> str | None:
        # add source

        for s in m.Source.objects.all():
            gr.SourceRepository(s.url, s.description, s.date, 0).create()

        # add entity

        for e in m.Entity.objects.all():
            gr.EntityRepository.create(e.ent, gr.SourceRepository.get_by_url(e.source.url), e.source_sentence, e.expert.pk)

        # add triple

        for t in m.Triple.objects.all():
            gr.TripleRepository.create_triple(t.sub.ent, gr.SourceRepository.get_by_url(t.source.url), t.obj.ent, t.predicate.pred, t.source_sentence, t.expert.pk)
        