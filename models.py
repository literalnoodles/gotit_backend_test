from platform import platform
import peewee

from database import db


class User(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    email = peewee.CharField()
    platform = peewee.CharField()
    name = peewee.CharField()
    phone_number = peewee.CharField()
    occupation = peewee.CharField()

    class Meta:
        database = db


class Post(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    title = peewee.CharField()
    body = peewee.TextField()
    author = peewee.IntegerField()
    created = peewee.DateTimeField()

    class Meta:
        database = db


class PostLike(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    post_id = peewee.IntegerField()
    user_id = peewee.IntegerField()
    created = peewee.DateTimeField()

    class Meta:
        database = db
        table_name = "Post_Like"
