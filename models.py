from receive_sms import db
#from app import db
import datetime
from sqlalchemy.dialects.postgresql import JSON

class Dialog(db.Model):
    __tablename__ = 'dialogs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    dialogid = db.Column(db.String(120), unique=True)
    timestamp = db.Column(db.DateTime)

    def __init__(self, name, dialogid):
        self.dialogid = dialogid
        self.name = name
        self.timestamp = datetime.datetime.utcnow()

    def __repr__(self):
        return '<Dialog %r>' % self.name

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    phone_number = db.Column(db.String(120), unique=True)
    timestamp = db.Column(db.DateTime)
    messages = db.relationship('Messages', backref='user', lazy='dynamic')

    def __init__(self, phone_number,timestamp):
        #self.username = username
        #self.email = email
        self.phone_number = phone_number
        self.timestamp = timestamp

    def __repr__(self):
        return '<User %r>' % self.username

class Messages(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String())
    response = db.Column(db.String())
    dialogid = db.Column(db.String())
    timestamp = db.Column(db.DateTime)
    number = db.Column(db.String(120))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __init__(self, message, dialogid, number, response, user):
        self.message = message
        self.dialogid = dialogid
        self.number = number
        self.response = response
        self.user_id = user
        self.timestamp = datetime.datetime.utcnow()

    def __repr__(self):
        return '<id {}>'.format(self.id)
