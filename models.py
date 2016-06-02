from receive_sms import db
from sqlalchemy.dialects.postgresql import JSON


class Messages(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String())
    response = db.Column(db.String())
    dialogid = db.Column(db.String())
    timestamp = db.Column(db.DateTime)
    number = db.Column(db.String(120))

    def __init__(self, message, dialogid, number, timestamp):
        self.dialogid= dialogid
        self.message = message
        self.timestamp = timestamp
        self.number = number

    def __repr__(self):
        return '<id {}>'.format(self.id)
