import flask_login
from lib.admin.database import db
from datetime import datetime


class Accesspoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bssid = db.Column(db.String(128))
    essid = db.Column(db.String(128))
    passphrase = db.Column(db.String(256))
    time_captured = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )
    last_modified = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )
