from peewee import *
import os

DB_HOST = os.getenv('DBHOST', 'localhost')
DB_PORT = int(os.getenv('DBPORT', 3306))
DB_USER = os.getenv('DBUSER', 'root')
DB_PASS = os.getenv('DBPASS', 'root')
database = MySQLDatabase('trendshift',
                         **{'charset': 'utf8mb4', 'sql_mode': 'PIPES_AS_CONCAT', 'use_unicode': True, 'user': DB_USER,
                            'password': DB_PASS, 'host': DB_HOST, 'port': DB_PORT})


class BaseModel(Model):
    class Meta:
        database = database


class Config(BaseModel):
    expire = DateTimeField()
    key = CharField(unique=True)
    value = CharField()

    class Meta:
        table_name = 'config'


class Language(BaseModel):
    name = CharField(unique=True)

    class Meta:
        table_name = 'language'


class Repository(BaseModel):
    created_at = DateTimeField(constraints=[SQL('DEFAULT current_timestamp()')], null=True)
    description = TextField(null=True)
    error = IntegerField(constraints=[SQL('DEFAULT 0')], null=True)
    forks = IntegerField(constraints=[SQL('DEFAULT 0')], null=True)
    github = CharField()
    lang = ForeignKeyField(column_name='lang_id', field='id', model=Language, null=True)
    name = CharField()
    stars = IntegerField(constraints=[SQL('DEFAULT 0')], null=True)
    trendshift_id = IntegerField(null=True, unique=True)
    updated_at = DateTimeField(constraints=[SQL('DEFAULT current_timestamp()')], null=True)
    website = CharField(null=True)

    class Meta:
        table_name = 'repository'


class Ranking(BaseModel):
    created_at = DateTimeField(constraints=[SQL('DEFAULT current_timestamp()')], null=True)
    lang = ForeignKeyField(column_name='lang_id', constraints=[SQL('DEFAULT 0')], field='id', model=Language, null=True)
    rank = IntegerField(constraints=[SQL('DEFAULT 0')], null=True)
    rank_date = DateField(null=True)
    repository = ForeignKeyField(column_name='repository_id', field='id', model=Repository)
    updated_at = DateTimeField(constraints=[SQL('DEFAULT current_timestamp()')], null=True)

    class Meta:
        table_name = 'ranking'
