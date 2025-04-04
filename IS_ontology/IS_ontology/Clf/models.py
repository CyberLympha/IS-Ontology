from django.db import models # type: ignore

# Create your models here.

class Source(models.Model):
    """
    Модель для хранения информации об источнике (статье, веб-странице и т.п.).

    Атрибуты:
        url (URLField): Уникальный адрес источника.
        description (TextField): Краткое описание содержания источника.
        date (DateField): Дата добавления источника (устанавливается автоматически при создании).
    """
    url = models.URLField(unique=True, help_text="Уникальный URL источника")
    description = models.TextField(help_text="Описание статьи или веб-страницы")
    date = models.DateField(auto_now_add=True, help_text="Дата добавления записи")

    def __str__(self):
        """
        Возвращает строковое представление объекта Source.

        В данном случае — URL источника, что удобно для отображения в админке,
        логах и отладке.
        """
        return self.url
