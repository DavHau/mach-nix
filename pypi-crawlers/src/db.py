import os

from peewee import *
from playhouse.postgres_ext import *

db = PostgresqlExtDatabase(
    'almighty',
    user='almighty',
    password=os.environ.get('DB_PASS'),
    host=os.environ.get('DB_HOST'),
    port=5432
)


class BaseModel(Model):
    class Meta:
        database = db


class Package(BaseModel):
    name = CharField(index=True)
    version = CharField(index=True)
    py_ver = CharField(index=True)
    error = TextField(null=True, index=True)
    install_requires = BinaryJSONField(null=True)
    setup_requires = BinaryJSONField(null=True)
    extras_require = BinaryJSONField(null=True)
    tests_require = BinaryJSONField(null=True)
    python_requires = BinaryJSONField(null=True)
    class Meta:
        indexes = (
            (('name', 'version', 'py_ver'), True),
        )

    @classmethod
    def defaults(cls):
        return dict(
            error=None,
            install_requires=None,
            setup_requires=None,
            extras_require=None,
            tests_require=None,
            python_requires=None,
        )


def init_db():
    pass
    db.drop_tables([])
    db.create_tables([Package])


if __name__ == "__main__":
    init_db()
