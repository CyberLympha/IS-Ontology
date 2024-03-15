from django.conf import settings
from neo4j import GraphDatabase, BoltDriver, Session

_driver: BoltDriver = GraphDatabase.driver(settings.NEO4J_URL, auth=settings.NEO4J_AUTH)

def close():
    _driver.close()

def get_session() -> Session:
    return _driver.session()

def execute(tf, *args, **kwargs):
    with get_session() as session:
        return session.write_transaction(tf, *args, **kwargs)

def execute_read(tf, *args, **kwargs):
    with get_session() as session:
        return session.read_transaction(tf, *args, **kwargs)

