from dataclasses import dataclass
from datetime import datetime
from django.contrib.auth import get_user_model
from neo4j.time import DateTime

from .database import execute, execute_read


@dataclass
class SourceRepository:
    url: str
    description: str
    date: datetime | DateTime
    user: int

    def create(self):
        execute(
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
            ).single(),
            self.url,
            self.description,
            self.date,
            self.user,
        )

    @staticmethod
    def get_descriptions() -> dict:
        return execute_read(
            lambda tx: tx.run("match (n:Source) return n.url, n.description").data()
        )

    @staticmethod
    def get_by_url(url: str):
        obj = execute_read(
            lambda tx, url: tx.run(
                "MATCH (n:Source {url: $url}) return n", url=url
            ).data()[0]["n"],
            url,
        )
        return SourceRepository(**obj)

    def get_connected_entities(self, source_sentence: str):
        return execute_read(
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
    @staticmethod
    def all():
        return execute_read(
            lambda tx: tx.run(
                "MATCH (s:Source)-[r:HAS_ENTITY]->(t:Entity) return s, r, t"
            ).values()
        )

    @staticmethod
    def get_by_name(name: str):
        return execute_read(
            lambda tx, name: tx.run(
                "MATCH (t:Entity {name: $name}) return t", name=name
            ).single(),
            name,
        )

    def create(
        name: str, source: SourceRepository, source_sentence: str, expert: int
    ) -> bool:
        # TODO: возможны повторы отношений
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
            return False

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
        if users:
            users = list(map(int, users))
        if users == []:
            users = None
        if sources == []:
            sources = None
        # TODO: gереписать
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
        if users is not None:
            return execute_read(
                lambda tx, users: tx.run(
                    "match (s:Source)-[r:HAS_ENTITY]->(t:Entity) where t.user IN $users return s,r,t",
                    users=users,
                ).values(),
                users,
            )
        if sources is not None:
            return execute_read(
                lambda tx, sources: tx.run(
                    "match (s:Source)-[r:HAS_ENTITY]->(t:Entity) where s.url IN $sources return s,r,t",
                    sources=sources,
                ).values(),
                sources,
            )
        return execute_read(
                lambda tx: tx.run(
                    "match (s:Source)-[r:HAS_ENTITY]->(t:Entity) return s,r,t"
                ).values()
            )

class TripleRepository:
    @staticmethod
    def create_triple(
        subject: str,
        source: SourceRepository,
        object: str,
        predicate: str,
        sent: str,
        user: int,
    ):
        # subject-source->object
        query = (
            "MATCH "
            "    (subject:Entity), (object:Entity), (s_obj: Source) "
            "    WHERE subject.name=$subject AND object.name=$object AND s_obj.url=$source "
            "CREATE (subject)-[:T_LINK]->(t: Triple {name: $predicate, sent: $sent, user: $user, date: datetime()})-[:T_LINK]->(object), (s_obj)-[:HAS_TRIPLE]->(t)"
        )
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
        return execute_read(
            lambda tx: tx.run(
                "match (e1:Entity)-->(t:Triple)-->(e2:Entity), (s:Source)-->(t) return e1, t, e2, s"
            ).data(),
        )

    @staticmethod
    def filter(users: list[str | int] | None, sources: list[str] | None):
        if users:
            users = list(map(int, users))
        if users == []:
            users = None
        if sources == []:
            sources = None
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
        if users is not None:
            return execute_read(
                lambda tx, users: tx.run(
                    "match (e1:Entity)-->(t:Triple)-->(e2:Entity), (s:Source)-->(t) where t.user IN $users return e1, t, e2, s",
                    users=users,
                ).data(),
                users,
            )
        if sources is not None:
            return execute_read(
                lambda tx, sources: tx.run(
                    "match (e1:Entity)-->(t:Triple)-->(e2:Entity), (s:Source)-->(t) where s.url IN $sources return e1, t, e2, s",
                    sources=sources,
                ).data(),
                sources,
            )
        return execute_read(
            lambda tx: tx.run(
                "match (e1:Entity)-->(t:Triple)-->(e2:Entity), (s:Source)-->(t) return e1, t, e2, s"
            ).data()
        )


def get_user_name(user_pk: str | int) -> str:
    user_pk = int(user_pk)
    return (
        get_user_model().objects.get(pk=user_pk).get_username()
        if user_pk >= 0
        else "unknown"
    )
