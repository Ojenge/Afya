import plivo, plivoxml
import os
import re
import wolframalpha
import requests
import nltk
import jinja2
import json
from flask import Flask, request, make_response
from flask.ext.sqlalchemy import SQLAlchemy
from xml.etree import ElementTree

from watsonutils.dialog import DialogUtils
from watsonutils.nlpclassifier import NLPUtils
from watson_developer_cloud import WatsonException
from nltk import word_tokenize, pos_tag

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
##app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://waguhplidoqlao:gkOntEWO-1nOeWawrA0sqiVu9r@ec2-54-163-225-208.compute-1.amazonaws.com:5432/d2c1f8q9j9i8dr'

db = SQLAlchemy(app)
client = wolframalpha.Client('L38Q2P-K67YKTJ88X')


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

    # The text which was received
    source = request.values.get('source')
    source = "Kenya" 
    afyasecret = request.values.get('afyasecret')
    print afyasecret
    device = request.values.get('Device')
    print device
    print request.values
 
    # Print the message
    print 'Text received: %s - From: %s' % (text, from_number)
    #return "Text received"
    # Generate a Message XML with the details of the reply to be sent.
    dialog_file = open("resources/pizza_sample.xml", 'r')
    body = 'Thank you for your message'
    try:
        dialog = DialogUtils(app)
        dialogid = dialog.getDialogs()
        nlp = NLPUtils(app)
        #classes = nlp.service.classify('3a84dfx64-nlc-2891', text)
        classes = nlp.service.classify('3a84dfx64-nlc-5204', text)
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
            print 'The text %s' %(text)
            search_text = Messages.query.filter(Messages.message == text).count()
            print search_text
            if search_text:
                print search_text
            else:
                # means it exists so we create it
                message = Messages(message=text,dialogid=dialogid,number=from_number)
                db.session.add(message)
                db.session.commit()
            print dialogid
            print classes
            nouns = [token for token, pos in pos_tag(word_tokenize(text)) if pos.startswith('N')]
            confidence = classes['classes'][0]['confidence']
            if confidence > 0.9: 
                if classes['top_class'] == 'SearchDisease':
                    #we google the text
                    res = client.query(text)
                    body = None
                    try:
                        primary_search = res.pods[0].text
                        for pod in res.pods:
                            if pod.title == 'Definition':
                                body = pod.text[7:]
                                print 'The wolf is here'
                                print body
                            if (body is None) and (pod.title == 'Medical codes'):
                                print 'it should appear here'
                                payload = {'db':'healthTopics','term': primary_search}
                                print payload
                                req = requests.get("https://wsearch.nlm.nih.gov/ws/query", params=payload)
                                tree = ElementTree.fromstring(req.content)
                                rank = tree.find( './/*[@rank="0"]' )
                                content = rank.find('.//*[@name="FullSummary"]')
                                content = jinja2.filters.do_striptags(content.text)  
                                body = re.match(r'(?:[^.:;]+[.:;]){4}', content).group()
                    except:
                        print nouns
                        query_text = ""
                        for item in nouns:
                            query_text = query_text + " " + item
                        print query_text
                        if query_text is "":
                            foreign = [token for token, pos in pos_tag(word_tokenize(text)) if pos.startswith('FW')]
                            for item in foreign:
                                query_text = query_text + " " + item 
                        print "now the payload"
                        payload = {'db':'healthTopics','term': query_text}
                        print payload
                        req = requests.get("https://wsearch.nlm.nih.gov/ws/query", params=payload)
                        tree = ElementTree.fromstring(req.content)
                        rank = tree.find( './/*[@rank="0"]' )
                        content = rank.find('.//*[@name="FullSummary"]')
                        content = jinja2.filters.do_striptags(content.text)
                        lines = content.split('.')
                        definition = lines[:2]
                        for item in definition:
                            body = body + item
                if classes['top_class'] == 'DiseaseSymptoms':
                    print nouns
                    regex = re.compile(".*(symptoms).*",re.IGNORECASE)
                    search = [m.group(0) for l in nouns for m in [regex.search(l)] if m]
                    if len(search) == 0 :
                        nouns.append("symptoms")
                    query_text = ""
                    for item in nouns:
                        query_text = query_text + " " + item
                    print query_text
                    print "now the payload"
                    payload = {'db':'healthTopics','term': query_text}
                    print payload
                    req = requests.get("https://wsearch.nlm.nih.gov/ws/query", params=payload)
                    tree = ElementTree.fromstring(req.content)
                    rank = tree.find( './/*[@rank="0"]' )
                    content = rank.find('.//*[@name="FullSummary"]')
                    content = jinja2.filters.do_striptags(content.text)
                    symptom = re.search('symptoms',content, re.IGNORECASE)
                    if symptom:
                        sentence = re.findall(r"([^.]*?symptoms[^.]*\.)",content, re.IGNORECASE)
                        body = sentence[0]
                if classes['top_class'] == 'Treatment':
                    print nouns
                    regex = re.compile(".*(treat).*",re.IGNORECASE)
                    search = [m.group(0) for l in nouns for m in [regex.search(l)] if m]
                    if len(search) == 0 :
                        nouns.append("treat")
                    query_text = ""
                    for item in nouns:
                        query_text = query_text + " " + item
                    print query_text
                    print "now the payload"
                    payload = {'db':'healthTopics','term': query_text}
                    print payload
                    req = requests.get("https://wsearch.nlm.nih.gov/ws/query", params=payload)
                    tree = ElementTree.fromstring(req.content)
                    rank = tree.find( './/*[@rank="0"]' )
                    content = rank.find('.//*[@name="FullSummary"]')
                    content = jinja2.filters.do_striptags(content.text)
                    treat = re.search('treat',content, re.IGNORECASE)
                    if treat:
                        sentence = re.findall(r"([^.]*?treat[^.]*\.)",content, re.IGNORECASE)
                    else:
                        sentence = re.findall(r"([^.]*?cure[^.]*\.)",content, re.IGNORECASE)
                    body = sentence[0]
                if classes['top_class'] == 'Finish':
                    body = "Will that be all?"
                    if text == "Yes":
                        body = "You are welcome"
                    if text == "yes":
                        body = "You are welcome"
                    if (text == "No") or (text == "no"):
                        body = "What else are you curious about"
                    print body
            else:
                body = "Sorry I couldn’t find anything on that. Could you ask another question?"
                body = unicode(body)
    except WatsonException as err:
        print err
    if device == "Afyadevice":
        payload = {"apiKey":"90303b65-2240-4316-9898-6493af7364e1", "payload":{"message": body, "recipients":[{ "type":"mobile", "value": from_number }]}}
        print payload
        print json.dumps(payload)
        frontline_resp = requests.post("https://cloud.frontlinesms.com/api/1/webhook",data=json.dumps(payload))
        print frontline_resp.content
        response = { "payload": { "success": "true", "task": "send",
        "messages": [
            {
                "to": from_number,
                "message": body,
            }]}}
        ret_response = json.dumps(response)
    else:
 

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

@app.route('/')
def kenyan_numbers():
    print request.values.get('task')
    return 'Hello World!'

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port,debug=True)
#if __name__ == "__main__":
#    port = int(os.environ.get("PORT", 5000))
#    app.run(host='0.0.0.0', port=port)

# Sample successful output
# Text received: Hello, from Plivo - From: 2222222222
