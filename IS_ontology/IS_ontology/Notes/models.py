from django.db import models
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse


class model_Note(models.Model):
    STATUS_CHOICES = (
        ("private", "Private"),
        ("public", "Public"),
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique_for_date="publish")
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="note_posts"
    )
    obj = models.CharField(max_length=200)
    predicat = models.CharField(max_length=200)
    subj = models.CharField(max_length=200)
    source = models.CharField(max_length=200)
    publish = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="private")

    class Meta:
        ordering = ("publish",)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse(
            "Notes:note_details",
            args=[self.publish.year, self.publish.month, self.publish.day, self.slug],
        )


class Source(models.Model):
    url = models.CharField(max_length=350, primary_key=True)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_descriptions(cls) -> list[tuple[int, str]]:
        return [(i, elem.description) for i, elem in enumerate(cls.objects.all())]


class Text(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    text = models.TextField()
    date = models.DateTimeField(auto_now_add=True)


class Entity(models.Model):
    ent = models.CharField(max_length=400)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    source_sentence = models.TextField()
    expert = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.ent


class Predicate(models.Model):
    pred = models.CharField(max_length=200, primary_key=True)
    expert = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_preds(cls) -> list[tuple[int, str]]:
        return [(i, elem.pred) for i, elem in enumerate(cls.objects.all())]
    
    def __str__(self) -> str:
        return self.pred


class Triple(models.Model):
    sub = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="sub")
    obj = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="obj")
    predicate = models.ForeignKey(
        Predicate, on_delete=models.CASCADE, related_name="predicate"
    )
    source_sentence = models.TextField()
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    expert = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_by_sent(cls, source: Source, sentence: str) -> list[list]:
        return [
            [
                triple.sub.ent,
                triple.obj.ent,
                triple.predicate.pred,
                triple.expert.username,
            ]
            for triple in cls.objects.filter(source=source, source_sentence=sentence)
        ]
    
    @classmethod
    def create(cls,sub, obj, pred, source, sent, user) -> tuple[models.Model, bool]:
        sub_ent = Entity.objects.filter(ent=sub)[0]
        obj_ent = Entity.objects.filter(ent=obj)[0]
        predicate = Predicate.objects.filter(pred=pred)[0]
        return cls.objects.get_or_create(
            sub=sub_ent,
            obj=obj_ent,
            predicate=predicate,
            source=source,
            source_sentence=sent,
            expert=user,
        )
    
    def __str__(self) -> str:
        return f"{self.sub}-{self.predicate}->{self.obj}"


class EntScore(models.Model):
    ent = models.ForeignKey(Entity, on_delete=models.CASCADE)
    expert = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.BooleanField()


class TripleScore(models.Model):
    triple = models.ForeignKey(Triple, on_delete=models.CASCADE)
    expert = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.BooleanField()
