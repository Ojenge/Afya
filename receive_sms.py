import plivo, plivoxml
import os
from flask import Flask, request, make_response
from flask.ext.sqlalchemy import SQLAlchemy

from watsonutils.dialog import DialogUtils
from watson_developer_cloud import WatsonException

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
##app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://waguhplidoqlao:gkOntEWO-1nOeWawrA0sqiVu9r@ec2-54-163-225-208.compute-1.amazonaws.com:5432/d2c1f8q9j9i8dr'

db = SQLAlchemy(app)

class Messages(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String())
    dialogid = db.Column(db.String())
    number = db.Column(db.String(120))

    def __init__(self, message, dialogid, number):
        self.dialogid= dialogid
        self.message = message
        self.number = number

    def __repr__(self):
        return '<id {}>'.format(self.id)


@app.route("/receive_sms/", methods=['GET','POST'])
def receive_sms():

    # Sender's phone numer
    from_number = request.values.get('From')

    # Receiver's phone number - Plivo number
    to_number = request.values.get('To')

    # The text which was received
    text = request.values.get('Text')
    
    # Print the message
    print 'Text received: %s - From: %s' % (text, from_number)
    #return "Text received"
    # Generate a Message XML with the details of the reply to be sent.
    dialog_file = open("resources/pizza_sample.xml", 'r')
    body = 'Thank you for your message'
    try:
        dialog = DialogUtils(app)
        dialogid = dialog.getDialogs()
        if not db.session.query(Messages).filter(Messages.number == from_number).count():
            dialogid = dialog.createDialog(dialog_file, from_number)
            message = Messages(text,dialogid=dialogid['dialog_id'],number=from_number)
            db.session.add(message)
            db.session.commit()
            dialogid = dialogid['dialog_id']
            response = dialog.getConversation(dialogid)
            print response['conversation_id']
            body = response['response'][0]
        else:
           #we will need to filter the dialog id based on the number
           # we have been having a conversation already
            dialogid = Messages.query.filter(Messages.number == from_number).first().dialogid
            search_text = Messages.query.filter(Messages.message == text)
            print search_text
            if search_text:
                print search_text
            else:
                # means it exists so we create it
                message = Messages(text,dialogid=dialogid['dialog_id'],number=from_number)
                db.session.add(message)
                db.session.commit()
            print dialogid
            response = dialog.getConversation(dialogid)
            print response['conversation_id']
            print response['client_id']
            #message = Messages(text,dialogid=dialogid['dialog_id'],number=from_number)
            messages = Messages.query.filter(Messages.number == from_number).all()
            for message in messages:
                print message
                ##answer = dialog.service.conversation(dialog_id=dialogid,dialog_input=message['message'], conversation_id=response['conversation_id'], client_id=response['client_id'])
                print answer
            responses = answer['response']
            if len(responses) > 1:
                responses = filter(None, responses)
                body = responses[0]
            else:
                body = responses[0]
    except WatsonException as err:
        print err 

    resp = plivoxml.Response()

    params = {
    'src' : to_number, # Sender's phone number
    'dst' : from_number, # Receiver's phone Number
    'callbackUrl': "http://afya.herokuapp.com/report/", # URL that is notified by Plivo when a response is available and to which the response is sent
    'callbackMethod' : "GET" # The method used to notify the callbackUrl
    }

    # Message added
    resp.addMessage(body, **params)

    ret_response = make_response(resp.to_xml())
    ret_response.headers["Content-type"] = "text/xml"

    # Prints the XML
    print resp.to_xml()
    # Returns the XML
    return ret_response

@app.route("/report/", methods=['GET','POST'])
def report():

    # Sender's phone number
    from_number = request.values.get('From')

    # Receiver's phone number - Plivo number
    to_number = request.values.get('To')

    # Status of the message
    status = request.values.get('Status')

    # Message UUID
    uuid = request.values.get('MessageUUID')

    # Prints the status and messageuuid
    print "From : %s To : %s Status : %s MessageUUID : %s" % (from_number, to_number, status,uuid)
    return "Delivery reported"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port,debug=True)
#if __name__ == "__main__":
#    port = int(os.environ.get("PORT", 5000))
#    app.run(host='0.0.0.0', port=port)

# Sample successful output
# Text received: Hello, from Plivo - From: 2222222222
