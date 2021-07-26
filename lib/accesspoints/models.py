from lib.admin.database import db

# class AccesspointInfo(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     bssid = db.Column(db.String(17), nullable=False)
#     essid = db.Column(db.String(128))
#     handshake = db.relationship('Handshake', backref='Accesspoint_info', uselist=False)
#     preshared_key = db.relationship('PresharedKey', backref='Accesspoint_info', uselist=False)


# class Handshake(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     date_captured = db.Column(db.String(19))
#     capture_file_path = db.Column(db.Text())
#     accesspoint_info_id = db.Column(db.Integer, db.ForeignKey('accesspoint_info.id'), unique=True)


# class PresharedKey(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     date_captured = db.Column(db.String(19))
#     preshared_key = db.Column(db.String(1024))
#     accesspoint_info_id = db.Column(db.Integer, db.ForeignKey('accesspoint_info.id'), unique=True)
