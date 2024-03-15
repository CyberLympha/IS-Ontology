from django.contrib import admin

from IS_ontology.Notes.models import Source, Text, Entity, Triple, Predicate, EntScore, TripleScore



@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ['url']
    list_filter = ['url']
        
@admin.register(Text)
class TextAdmin(admin.ModelAdmin):
    list_display = ['source', 'date']
    list_filter = ['date']
    
@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ['ent', 'source']
    list_filter = ['ent']
    
@admin.register(Predicate)
class PredicateAdmin(admin.ModelAdmin):
    list_display = ['pred']
    list_filter = ['pred']
    
@admin.register(Triple)
class TripleAdmin(admin.ModelAdmin):
    list_display = ['sub', 'obj', 'predicate' , 'source', 'date']
    list_filter = ['source']
    
@admin.register(EntScore)
class EntScoreAdmin(admin.ModelAdmin):
    list_display = ['ent', 'expert', 'score']
    list_filter = ['ent', 'expert']
    
@admin.register(TripleScore)
class TripleScoreAdmin(admin.ModelAdmin):
    list_display = ['triple', 'expert', 'score']
    list_filter = ['triple', 'expert']