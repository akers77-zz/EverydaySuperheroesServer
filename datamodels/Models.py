from peewee import *

database = "/tmp/EverydaySuperheroesServer.db"
db = SqliteDatabase(database, threadlocals="true")


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    email = CharField()
    id = PrimaryKeyField()
    name = CharField()
    password = CharField()



class Job(BaseModel):
    accepted = BooleanField()
    attendee = ForeignKeyField(User, related_name="acceptor", null=True)
    completed = BooleanField()
    date = DateTimeField()
    description = CharField()
    id = PrimaryKeyField()
    latitude = CharField()
    longitude = CharField()
    name = CharField()
    type = CharField()
    requester = ForeignKeyField(User, related_name="requester")


class UserLocation(BaseModel):
    user = ForeignKeyField(User, related_name="user", unique=True)
    latitude = CharField()
    longitude = CharField()
    time = DateTimeField()


db.connect()
db.create_tables([Job, User, UserLocation], safe=True)
