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
    firstname = db.Column(db.String(80))
    lastname = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    phone_number = db.Column(db.String(120))
    facebook_id = db.Column(db.String(250), unique=True)
    dialog_id = db.Column(db.String(250), unique=True)  
    timestamp = db.Column(db.DateTime)
    messages = db.relationship('Messages', backref='user', lazy='dynamic')


    def __init__(self, timestamp, facebook_id):
        #self.username = username
        #self.email = email
        #self.phone_number = phone_number
        self.timestamp = timestamp
        self.facebook_id = facebook_id

class Messages(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String())
    dialogid = db.Column(db.String())
    timestamp = db.Column(db.DateTime)
    number = db.Column(db.String(120))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    response = db.relationship('Response', backref='messages', lazy='dynamic')

    def __init__(self, message, dialogid, number, user):
        self.message = message
        self.dialogid = dialogid
        self.number = number
        self.user_id = user
        self.timestamp = datetime.datetime.utcnow()

    def __repr__(self):
        return '<id {}>'.format(self.id)

class Response(db.Model):
    __tablename__ = 'responses'

    id = db.Column(db.Integer, primary_key=True)
    response = db.Column(db.String())
    dialogid = db.Column(db.String())
    timestamp = db.Column(db.DateTime)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __init__(self, message, dialogid, response, user):
        self.message = message
        self.dialogid = dialogid
        self.response = response
        self.user_id = user
        self.timestamp = datetime.datetime.utcnow()

    def __repr__(self):
        return '<id {}>'.format(self.id)

 
