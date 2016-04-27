from receive_sms import db
from sqlalchemy.dialects.postgresql import JSON


class Messages(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String())
    dialogid = db.Column(db.String())
    number = db.Column(db.String(120), unique=True)
    
    def __init__(self, dialogid):
        self.dialogid= dialogid

    def __repr__(self):
        return '<id {}>'.format(self.id)

