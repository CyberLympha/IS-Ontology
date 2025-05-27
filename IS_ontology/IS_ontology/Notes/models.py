"""
Django-модели для управления аннотированными данными, источниками, сущностями и триплетами.

Модуль содержит модели для:
- пользовательских заметок (`model_Note`);
- сохранения источников (`Source`) и их текстов (`Text`);
- выделенных сущностей (`Entity`) и предикатов (`Predicate`);
- триплетов (subject-predicate-object) (`Triple`);
- оценки аннотаций экспертами (`EntScore`, `TripleScore`).

Функции:
- `get_absolute_url` в заметках — генерация ссылки на подробный просмотр;
- `get_descriptions` и `get_preds` — вспомогательные методы для получения описаний и предикатов;
- `Triple.get_by_sent` — извлечение триплетов по предложению;
- `Triple.create` — создание триплета при наличии сущностей и предиката.

Связи моделей:
- `Source` и `Text`, `Entity`, `Triple` — через внешние ключи;
- `Entity`, `Triple`, `Predicate` — аннотируются пользователями (`User`);
- `EntScore`, `TripleScore` — оценка сущностей и триплетов.

Примечания:
- Каждая сущность и предикат хранят информацию об эксперте и времени добавления.
- Текст привязывается к источнику.
- Система предназначена для построения онтологий или графов знаний на основе аннотированных текстов.
"""

from django.db import models
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse


class model_Note(models.Model):
    """
    Модель пользовательских заметок с аннотированными триплетами.

    Атрибуты:
        title (str): Заголовок заметки.
        slug (str): Уникальный slug, используемый в URL.
        author (User): Автор заметки.
        obj (str): Объект триплета.
        predicat (str): Предикат триплета.
        subj (str): Субъект триплета.
        source (str): Источник, к которому относится заметка.
        publish (datetime): Дата публикации.
        created (datetime): Дата создания.
        updated (datetime): Дата последнего обновления.
        status (str): Статус видимости заметки (private/public).
    """
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
        """
        Возвращает абсолютный URL для доступа к деталям заметки.

        Returns:
            str: URL для страницы заметки.
        """
        return reverse(
            "Notes:note_details",
            args=[self.publish.year, self.publish.month, self.publish.day, self.slug],
        )


class Source(models.Model):
    """
    Модель источника, к которому могут привязываться тексты, сущности и триплеты.

    Атрибуты:
        url (str): Уникальный URL источника (PK).
        description (str): Описание источника.
        date (datetime): Дата добавления.
    """
    url = models.CharField(max_length=350, primary_key=True)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_descriptions(cls) -> list[tuple[int, str]]:
        """
        Получает список описаний всех источников.

        Returns:
            list[tuple[int, str]]: Индекс и описание источника.
        """
        return [(i, elem.description) for i, elem in enumerate(cls.objects.all())]


class Text(models.Model):
    """
    Модель текста, связанного с определённым источником.

    Атрибуты:
        source (Source): Связанный источник.
        text (str): Содержимое текста.
        date (datetime): Дата добавления текста.
    """
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    text = models.TextField()
    date = models.DateTimeField(auto_now_add=True)


class Entity(models.Model):
    """
    Модель сущности, выделенной из текста.

    Атрибуты:
        ent (str): Содержание сущности.
        source (Source): Источник, в котором встречается сущность.
        source_sentence (str): Предложение, из которого извлечена сущность.
        expert (User): Пользователь, создавший сущность.
        date (datetime): Дата создания.
    """
    ent = models.CharField(max_length=400)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    source_sentence = models.TextField()
    expert = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """
        Возвращает строковое представление сущности.

        Returns:
            str: Текст сущности.
        """
        return self.ent


class Predicate(models.Model):
    """
    Модель предиката (отношения) между сущностями.

    Атрибуты:
        pred (str): Уникальное название предиката (PK).
        expert (User): Пользователь, предложивший предикат.
        description (str): Описание смысла предиката.
        date (datetime): Дата создания.
    """
    pred = models.CharField(max_length=200, primary_key=True)
    expert = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)  # Сделали описание необязательным
    date = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_preds(cls) -> list[tuple[int, str]]:
        """
        Получает список всех предикатов в виде (индекс, имя).

        Returns:
            list[tuple[int, str]]: Список предикатов.
        """
        return [(i, elem.pred) for i, elem in enumerate(cls.objects.all())]
    
    def __str__(self) -> str:
        """
        Возвращает строковое представление предиката.

        Returns:
            str: Название предиката.
        """
        return self.pred


class Triple(models.Model):
    """
    Модель триплета (subject — predicate — object) из текста.

    Атрибуты:
        sub (Entity): Субъект.
        obj (Entity): Объект.
        predicate (Predicate): Отношение между субъектом и объектом.
        source_sentence (str): Предложение, из которого получен триплет.
        source (Source): Источник, к которому относится триплет.
        expert (User): Автор аннотации.
        date (datetime): Дата создания.
    """
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
        """
        Возвращает все триплеты по источнику и предложению.

        Args:
            source (Source): Источник.
            sentence (str): Предложение из текста.

        Returns:
            list[list]: Список триплетов в формате [sub, obj, pred, expert].
        """
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
        """
        Создаёт триплет, если он ещё не существует.

        Args:
            sub (str): Название субъекта.
            obj (str): Название объекта.
            pred (str): Название предиката.
            source (Source): Источник.
            sent (str): Исходное предложение.
            user (User): Эксперт.

        Returns:
            tuple[Triple, bool]: Триплет и флаг, создан ли он (True) или уже существовал (False).
        """
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
        """
        Возвращает строковое представление триплета.

        Returns:
            str: Формат "{sub}-{predicate}->{obj}".
        """
        return f"{self.sub}-{self.predicate}->{self.obj}"


class EntScore(models.Model):
    """
    Оценка сущности экспертом.

    Атрибуты:
        ent (Entity): Оцениваемая сущность.
        expert (User): Эксперт, поставивший оценку.
        score (bool): Оценка (True — корректно, False — некорректно).
    """
    ent = models.ForeignKey(Entity, on_delete=models.CASCADE)
    expert = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.BooleanField()


class TripleScore(models.Model):
    """
    Оценка триплета экспертом.

    Атрибуты:
        triple (Triple): Оцениваемый триплет.
        expert (User): Эксперт, поставивший оценку.
        score (bool): Оценка (True — корректно, False — некорректно).
    """
    triple = models.ForeignKey(Triple, on_delete=models.CASCADE)
    expert = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.BooleanField()
