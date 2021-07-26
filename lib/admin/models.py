import flask_login
from lib.admin.database import db


class User(flask_login.UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True)
    password = db.Column(db.String(64))
    attempt = db.relationship('Attempt', backref='user', uselist=False)
    lockout = db.relationship('Lockout', backref='user', uselist=False)


class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    failed_attempts = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)


class Lockout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_locked = db.Column(db.Boolean, default=False)
    time_locked = db.Column(db.String(32))  # string to hold precise data
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
