from dataclasses import dataclass
from datetime import datetime
from django.contrib.auth import get_user_model
from neo4j.time import DateTime

from .database import execute, execute_read
from ..Notes.models import Source


"""
graph_repositories.py

Модуль репозиториев для работы с графовой базой данных Neo4j.

Содержит:
    - SourceRepository: Работа с узлами источников (Source).
    - EntityRepository: Работа с узлами сущностей (Entity) и их связями с источниками.
    - TripleRepository: Работа с триплетами (субъект — предикат — объект) и их связями.

Особенности:
    - Использует execute и execute_read для выполнения транзакций в Neo4j.
    - Интеграция с Django для получения информации о пользователях (экспертах).
    - Предусматривает операции создания, поиска и фильтрации сущностей и триплетов.

Замечание:
    - Некоторые методы ещё могут быть оптимизированы для повышения производительности и читаемости запросов.
"""


@dataclass
class SourceRepository:
    """
    Репозиторий для работы с узлами источников (Source) в базе данных Neo4j.

    Атрибуты:
        url (str): URL источника.
        description (str): Описание источника.
        date (datetime | DateTime): Дата добавления источника.
        user (int): Идентификатор пользователя (эксперта), добавившего источник.

    Методы:
        create(): Создаёт новый узел источника в графовой базе данных.
        get_descriptions(): Возвращает список всех источников (URL и описание).
        get_by_url(url): Находит источник по URL.
        get_connected_entities(source_sentence): Находит сущности, связанные с данным предложением источника.
    """
    url: str
    description: str
    date: datetime | DateTime
    user: int

    def create(self):
        """
        Создаёт новый узел источника (Source) в базе данных Neo4j.

        Выполняет:
            - Создание узла с атрибутами URL, описанием, датой и пользователем.

        Returns:
            None
        """
        execute(
            # Открываем сессию и выполняем транзакцию создания нового узла Source
            lambda tx, url, description, date, user: tx.run(
                """
                CREATE (s: Source {
                    url: $url,
                    description: $description,
                    date: datetime($date),
                    user: $user
                })
                RETURN id(s)
                """,
                url=url,
                description=description,
                date=date,
                user=user,
            ).single(), # Берём первую (и единственную) строку результат
            self.url,
            self.description,
            self.date,
            self.user,
        )

    @staticmethod
    def get_descriptions() -> dict:
        """
        Получает список всех доступных источников (URL и описание) из базы данных.

        Returns:
            dict: Список источников в формате [{"n.url": ..., "n.description": ...}, ...]
        """
        return execute_read(
            # Выполняем запрос для получения всех узлов Source (их URL и описания)
            lambda tx: tx.run(
                "match (n:Source) return n.url, n.description"
                ).data()
        )

    @staticmethod
    def get_by_url(url: str):
        """
        Находит источник в базе данных по заданному URL и возвращает его как объект SourceRepository.

        Описание процесса:
            - Выполняет запрос к базе данных Neo4j для поиска узла Source с заданным URL.
            - Преобразует полученные данные в экземпляр SourceRepository.

        Args:
            url (str): URL источника, который нужно найти.

        Returns:
            SourceRepository: Объект репозитория с данными найденного источника.

        Замечание:
            - Если источник по указанному URL не найден, метод вызовет ошибку IndexError.
            Следует предусмотреть обработку исключений на более высоком уровне при необходимости.
        """
        obj = execute_read(
            # Выполняем запрос к Neo4j: ищем узел Source по URL
            lambda tx, url: tx.run(
                "MATCH (n:Source {url: $url}) return n", url=url
            ).data()[0]["n"],
            url,
        )
        # Создаём и возвращаем экземпляр репозитория на основе полученных данных
        return SourceRepository(**obj)

    def get_connected_entities(self, source_sentence: str):
        """
        Находит все сущности, связанные с данным предложением указанного источника.

        Описание процесса:
            - Выполняет запрос к базе данных Neo4j.
            - Ищет все сущности (Entity), которые имеют связь HAS_ENTITY с данным предложением (source_sentence).

        Args:
            source_sentence (str): Текст предложения, к которому привязаны сущности.

        Returns:
            list[dict]: Список сущностей, каждая в формате словаря с данными узла Entity.
        """
        return execute_read(
            # Выполняем запрос: находим все сущности, связанные с источником по тексту предложения
            lambda tx, url, source_sentence: tx.run(
                """MATCH (s: Source {url: $url})-[:HAS_ENTITY{
            source_sentence: $source_sentence
            }]->(e: Entity)
            return e""",
                url=url,
                source_sentence=source_sentence,
            ).data(),
            self.url,
            source_sentence,
        )


class EntityRepository:
    """
    Репозиторий для работы с сущностями (Entity) в базе данных Neo4j.

    Отвечает за:
        - Получение всех сущностей и их связей с источниками.
        - Поиск сущностей по имени.
        - Создание новых сущностей и привязку их к источникам.
        - Фильтрацию сущностей по пользователям и источникам.

    Методы:
        all(): Возвращает все сущности вместе с их связями HAS_ENTITY.
        get_by_name(name): Ищет сущность по имени.
        create(name, source, source_sentence, expert): Создаёт сущность и устанавливает связь с источником.
        filter(users, sources): Фильтрует сущности по заданным пользователям и/или источникам.
    """

    @staticmethod
    def all():
        """
        Получает все сущности и их связи HAS_ENTITY с источниками из базы данных Neo4j.

        Описание процесса:
            - Выполняет запрос на поиск всех пар (источник — сущность) через связь HAS_ENTITY.
            - Возвращает результаты в виде списка кортежей (source, relation, entity).

        Returns:
            list[tuple]: Список кортежей (s, r, t), где:
                - s: узел источника (Source),
                - r: отношение HAS_ENTITY,
                - t: узел сущности (Entity).
        """
        return execute_read(
            lambda tx: tx.run(
                "MATCH (s:Source)-[r:HAS_ENTITY]->(t:Entity) return s, r, t"
            ).values()
        )

    @staticmethod
    def get_by_name(name: str):
        """
        Ищет сущность в базе данных Neo4j по её имени.

        Описание процесса:
            - Выполняет запрос к базе данных для поиска узла Entity с заданным именем.
            - Возвращает один найденный узел сущности.

        Args:
            name (str): Имя сущности для поиска.

        Returns:
            dict: Данные узла сущности (Entity) в формате словаря,
                либо None, если сущность не найдена.

        Замечание:
            - При отсутствии сущности может быть возвращено None или выброшено исключение,
            если не обрабатывать результат отдельно.
        """
        return execute_read(
            # Выполняем запрос к Neo4j для получения всех сущностей и их связей с источниками: ищем узел Entity по имени
            lambda tx, name: tx.run(
                "MATCH (t:Entity {name: $name}) return t", name=name
            ).single(), # Ожидаем один результат
            name,
        )

    def create(name: str, source: SourceRepository, source_sentence: str, expert: int) -> bool:
        """
        Создаёт сущность (Entity) в базе данных Neo4j и связывает её с источником (Source).

        Описание процесса:
            - Проверяет, существует ли уже связь HAS_ENTITY между данным источником, сущностью и предложением.
            - Если связь уже существует, ничего не создаёт и возвращает False.
            - Если связи нет, создаёт узел сущности (при необходимости) и новую связь HAS_ENTITY с источником.

        Args:
            name (str): Имя сущности (Entity).
            source (SourceRepository): Источник (Source), к которому будет привязана сущность.
            source_sentence (str): Предложение из текста источника, с которым будет связана сущность.
            expert (int): Идентификатор пользователя (эксперта), добавившего сущность.

        Returns:
            bool: 
                - True, если новая сущность и связь успешно созданы.
                - False, если такая связь уже существует.

        Замечания:
            - Возможны повторы сущностей или связей без дополнительных ограничений на уровне БД.
            - Желательно добавить дополнительную проверку уникальности связей в будущем.
        """
        # Проверяем, существует ли уже такая связь (источник — предложение — сущность)

        # TODO: возможны повторы отношений

        # Проверяем, существует ли уже такая связь (источник — предложение — сущность)
        r = execute_read(
            lambda tx, name, source_sentence, source: tx.run(
                """
                MATCH (s: Source {description:$source})-[r:HAS_ENTITY {
            source_sentence: $source_sentence
            }]->(e: Entity {
            name: $name
        })
        RETURN s, r, e
            """,
                name=name,
                source=source,
                source_sentence=source_sentence,
            ).data(),
            name,
            source_sentence,
            source.description,
        )

        if len(r) > 0:
            # Связь уже существует — ничего не создаём
            return False

        # Создаём сущность (если нужно) и новую связь HAS_ENTITY
        execute(
            lambda tx, name, source_sentence, source, expert: tx.run(
                """
                MATCH (s: Source {description:$source})
                MERGE (e: Entity {
            name: $name
        })
        ON CREATE SET e.user=$user
            CREATE (s)-[:HAS_ENTITY {
            date: datetime($date),
            user: $user,
            source_sentence: $source_sentence
            }]->(e)
        RETURN id(e)
            """,
                name=name,
                date=datetime.now(),
                user=expert,
                source=source,
                source_sentence=source_sentence,
            ),
            name,
            source_sentence,
            source.description,
            expert,
        )
        return True
    
    @staticmethod
    def filter(users: list[str | int] | None, sources: list[str] | None):
        """
        Фильтрует сущности в базе данных Neo4j по заданным пользователям и/или источникам.

        Описание процесса:
            - Если указаны пользователи и источники: возвращает сущности, соответствующие обоим условиям.
            - Если указаны только пользователи: фильтрует по пользователям.
            - Если указаны только источники: фильтрует по источникам.
            - Если фильтры не заданы: возвращает все сущности.

        Args:
            users (list[str | int] | None): Список идентификаторов пользователей (экспертов) для фильтрации.
            sources (list[str] | None): Список URL источников для фильтрации.

        Returns:
            list[tuple]: Список кортежей (s, r, t), где:
                - s: узел источника (Source),
                - r: отношение HAS_ENTITY,
                - t: узел сущности (Entity).

        Замечания:
            - Приведение users к int осуществляется внутри метода.
            - Код можно оптимизировать для устранения дублирования запросов и повышения читаемости.
        """

        # Приводим пользователей к типу int
        if users:
            users = list(map(int, users))

        # Обнуляем пустые списки для корректной работы условий
        if users == []:
            users = None
        if sources == []:
            sources = None

        # TODO: переписать

         # Фильтрация по пользователям и источникам одновременно
        if users is not None and sources is not None:
            return execute_read(
                lambda tx, users, sources: tx.run(
                    "match (s:Source)-[r:HAS_ENTITY]->(t:Entity) where t.user IN $users and s.url IN $sources return s,r,t",
                    users=users,
                    sources=sources,
                ).values(),
                users,
                sources,
            )
        
        # Фильтрация только по пользователям
        if users is not None:
            return execute_read(
                lambda tx, users: tx.run(
                    "match (s:Source)-[r:HAS_ENTITY]->(t:Entity) where t.user IN $users return s,r,t",
                    users=users,
                ).values(),
                users,
            )
        
        # Фильтрация только по источникам
        if sources is not None:
            return execute_read(
                lambda tx, sources: tx.run(
                    "match (s:Source)-[r:HAS_ENTITY]->(t:Entity) where s.url IN $sources return s,r,t",
                    sources=sources,
                ).values(),
                sources,
            )
        
        # Без фильтров — возвращаем все сущности
        return execute_read(
                lambda tx: tx.run(
                    "match (s:Source)-[r:HAS_ENTITY]->(t:Entity) return s,r,t"
                ).values()
            )

class TripleRepository:
    """
    Репозиторий для работы с триплетами (Triple) в базе данных Neo4j.

    Отвечает за:
        - Создание новых триплетов (связей субъект-предикат-объект) и их привязку к источникам.
        - Получение всех существующих триплетов с их связанными сущностями и источниками.
        - Фильтрацию триплетов по пользователям и источникам.

    Методы:
        create_triple(subject, source, object, predicate, sent, user): Создаёт новый триплет и устанавливает связи в графе.
        all(): Возвращает все триплеты вместе с их субъектами, предикатами, объектами и источниками.
        filter(users, sources): Фильтрует триплеты по пользователям и/или источникам.
    """

    @staticmethod
    def create_triple(
        subject: str,
        source: Source, 
        object: str,
        predicate: str,
        sent: str,
        user: int,
    ):
        """
        Создаёт новый триплет (Triple) между двумя сущностями в базе данных Neo4j
        и связывает его с источником.

        Описание процесса:
            - Находит узлы субъект (Entity), объект (Entity) и источник (Source) по их атрибутам.
            - Создаёт новый узел триплета (Triple) с атрибутами предиката, текста предложения, пользователя и даты создания.
            - Создаёт связи:
                - субъект → триплет (T_LINK),
                - триплет → объект (T_LINK),
                - источник → триплет (HAS_TRIPLE).

        Args:
            subject (str): Имя сущности-субъекта.
            source (Source): Экземпляр источника (Source), содержащий URL.
            object (str): Имя сущности-объекта.
            predicate (str): Название предиката (отношения) между субъектом и объектом.
            sent (str): Предложение, в рамках которого обнаружена связь.
            user (int): Идентификатор пользователя (эксперта), добавившего триплет.

        Returns:
            None
        """

        # Формируем Cypher-запрос для создания триплета и установления связей 
        # subject-source->object
        query = (
            "MATCH "
            "    (subject:Entity), (object:Entity), (s_obj: Source) "
            "    WHERE subject.name=$subject AND object.name=$object AND s_obj.url=$source "
            "CREATE (subject)-[:T_LINK]->(t: Triple {name: $predicate, sent: $sent, user: $user, date: datetime()})-[:T_LINK]->(object), (s_obj)-[:HAS_TRIPLE]->(t)"
        )

        # Выполняем запрос с переданными параметрами
        execute(
            lambda tx, subject, source, object, predicate, sent, user: tx.run(
                query,
                subject=subject,
                source=source,
                object=object,
                predicate=predicate,
                sent=sent,
                user=user,
            ),
            subject,
            source.url,
            object,
            predicate,
            sent,
            user,
        )

    @staticmethod
    def all():
        """
        Получает все триплеты из базы данных Neo4j вместе с их связанными сущностями и источниками.

        Описание процесса:
            - Выполняет запрос к базе данных, находя все триплеты и их связи:
                - Субъект (Entity) → Триплет (Triple) → Объект (Entity),
                - Источник (Source) → Триплет (HAS_TRIPLE).

        Returns:
            list[dict]: Список словарей, каждый из которых содержит:
                - e1: узел сущности-субъекта,
                - t: узел триплета (Triple),
                - e2: узел сущности-объекта,
                - s: узел источника.
        """
        return execute_read(
            # Выполняем запрос к Neo4j для получения всех триплетов с субъектами, объектами и источниками
            lambda tx: tx.run(
                "match (e1:Entity)-->(t:Triple)-->(e2:Entity), (s:Source)-->(t) return e1, t, e2, s"
            ).data(),
        )

    @staticmethod
    def filter(users: list[str | int] | None, sources: list[str] | None):
        """
        Фильтрует триплеты в базе данных Neo4j по заданным пользователям и/или источникам.

        Описание процесса:
            - Если указаны пользователи и источники: находит триплеты, созданные указанными пользователями и относящиеся к указанным источникам.
            - Если указаны только пользователи: находит триплеты, созданные указанными пользователями.
            - Если указаны только источники: находит триплеты, относящиеся к указанным источникам.
            - Если фильтры не заданы: возвращает все триплеты.

        Args:
            users (list[str | int] | None): Список идентификаторов пользователей (экспертов) для фильтрации.
            sources (list[str] | None): Список URL источников для фильтрации.

        Returns:
            list[dict]: Список словарей с найденными триплетами и их связанными субъектами, объектами и источниками.

        Замечания:
            - Приведение users к типу int происходит внутри метода.
            - Структура запроса может быть оптимизирована для уменьшения дублирования кода.
        """
        # Приводим список пользователей к int
        if users:
            users = list(map(int, users))

        # Обнуляем пустые списки для корректной проверки условий
        if users == []:
            users = None
        if sources == []:
            sources = None

        # Фильтрация по пользователям и источникам одновременно    
        # TODO: gереписать
        if users is not None and sources is not None:
            return execute_read(
                lambda tx, users, sources: tx.run(
                    "match (e1:Entity)-->(t:Triple)-->(e2:Entity), (s:Source)-->(t) where t.user IN $users and s.url IN $sources return e1, t, e2, s",
                    users=users,
                    sources=sources,
                ).data(),
                users,
                sources,
            )
        
        # Фильтрация только по пользователям
        if users is not None:
            return execute_read(
                lambda tx, users: tx.run(
                    "match (e1:Entity)-->(t:Triple)-->(e2:Entity), (s:Source)-->(t) where t.user IN $users return e1, t, e2, s",
                    users=users,
                ).data(),
                users,
            )
        
        # Фильтрация только по источникам
        if sources is not None:
            return execute_read(
                lambda tx, sources: tx.run(
                    "match (e1:Entity)-->(t:Triple)-->(e2:Entity), (s:Source)-->(t) where s.url IN $sources return e1, t, e2, s",
                    sources=sources,
                ).data(),
                sources,
            )
        
        # Без фильтрации — возвращаем все триплеты
        return execute_read(
            lambda tx: tx.run(
                "match (e1:Entity)-->(t:Triple)-->(e2:Entity), (s:Source)-->(t) return e1, t, e2, s"
            ).data()
        )


def get_user_name(user_pk: str | int) -> str:
    """
    Получает имя пользователя по его первичному ключу (ID).

    Описание процесса:
        - Преобразует переданный user_pk в int.
        - Если идентификатор положительный:
            - Пытается найти пользователя через Django ORM и вернуть его имя пользователя (username).
        - Если идентификатор отрицательный:
            - Возвращает строку 'unknown'.

    Args:
        user_pk (str | int): Первичный ключ пользователя (может быть строкой или числом).

    Returns:
        str: Имя пользователя или 'unknown', если идентификатор некорректный.
    """
    # Приводим user_pk к типу int
    user_pk = int(user_pk)

    # Если идентификатор положительный, ищем пользователя по ID 
    return (
        get_user_model().objects.get(pk=user_pk).get_username()
        if user_pk >= 0
        else "unknown"
    )




# ------------------------------------------------------------------------------
# Замечания и предложения по улучшению кода и логики (Technical Debt)

"""
1. Необработанные ошибки в методах:
   - В методах get_by_url и get_user_name возможны ошибки (IndexError, DoesNotExist).
   - Решение: добавить try-except для более безопасной работы с отсутствием данных.

2. Игнорирование результата выполнения запросов:
   - В методе SourceRepository.create результат (id созданного узла) загружается, но никак не используется.
   - Решение: либо явно сохранять id и возвращать его, либо убрать возврат id из Cypher-запроса, если он не нужен.

3. Дублирование Cypher-запросов в методах filter:
   - В классах EntityRepository и TripleRepository в методах filter много копипаста в запросах.
   - Решение: генерировать запрос динамически в зависимости от наличия фильтров users и sources.

4. Отсутствие строгой типизации в некоторых местах:
   - Например, в методах возвращаются списки кортежей или словарей, но типизация не всегда отражена в сигнатуре функций.
   - Решение: при возможности дополнительно уточнить типы возвращаемых данных.

5. Улучшение читаемости больших методов:
   - Некоторые методы (`create_triple`, `create`) можно разбить на более мелкие функции (например, построение запроса — отдельно).
   - Решение: повысить модульность кода для упрощения поддержки.

6. Логгирование ошибок и ключевых событий:
   - Сейчас отсутствует логгирование событий работы с базой данных.
   - Решение: добавить базовое логгирование для операций создания, поиска, ошибок.

7. Уточнение семантики возвратов:
   - В некоторых методах стоит явно указывать, что возвращается None, если ничего не найдено (например, в get_by_name).

8. Отсутствие проверки прав пользователя:
   - Сейчас любой пользователь с доступом к базе может создавать сущности и триплеты.
   - Решение: предусмотреть в будущем проверку прав доступа на уровне сервисов или репозиториев.

"""
# ------------------------------------------------------------------------------
