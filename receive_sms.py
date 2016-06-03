#!/usr/bin/env python
# -*- coding: utf-8 -*-

import plivo, plivoxml
import os
import re
import wolframalpha
import requests
import nltk
import jinja2
import json
import datetime
from flask import Flask, request, make_response
from flask.ext.sqlalchemy import SQLAlchemy
from xml.etree import ElementTree

from watsonutils.dialog import DialogUtils
from watsonutils.nlpclassifier import NLPUtils
from watson_developer_cloud import WatsonException
from nltk import word_tokenize, pos_tag

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
##app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://waguhplidoqlao:gkOntEWO-1nOeWawrA0sqiVu9r@ec2-54-163-225-208.compute-1.amazonaws.com:5432/d2c1f8q9j9i8dr'

db = SQLAlchemy(app)
client = wolframalpha.Client('L38Q2P-K67YKTJ88X')

from models import *

def get_profile(number):
   user = User.query.filter_by(phone_number=number).first()
   return user

def send_message(type,from_number,to_number,body):
    if type == "Afyadevice":
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

def check_last_thread(number):
    if Messages.query.filter_by(number=number).order_by(Messages.id.desc()).first():
        message = Messages.query.filter_by(number=number).order_by(Messages.id.desc()).first()
        status = True
        if message.response == "Welcome to Afya, and what shall we call you?":
            status = 'onboard'
    else:
        print 'no messages registered yet'
        status = False
    return status

@app.route("/receive_sms/", methods=['GET','POST'])
def receive_sms():
    # Sender's phone numer
    from_number = request.values.get('From')
    # Receiver's phone number - Plivo number
    to_number = request.values.get('To')
    # The text which was received
    text = request.values.get('Text')
    device = request.values.get('Device')
 
    # Print the message
    print 'Text received: %s - From: %s' % (text, from_number)
    # Generate a Message XML with the details of the reply to be sent.
    dialog_file = open("resources/pizza_sample.xml", 'r')
    dialog = DialogUtils(app)
    #return "Text received"
    ret_response = 'Test'
    if get_profile(from_number):
        user = get_profile(from_number)
    else:
        user = User(phone_number=from_number,timestamp=datetime.datetime.utcnow())
        db.session.add(user)
        db.session.commit()
        dialogid = dialog.createDialog(dialog_file, from_number)
        print dialogid
        dialog = Dialog(name=from_number,dialogid=dialogid['dialog_id'])
        db.session.add(dialog)
        db.session.commit()
        body = "Welcome to Afya, and what shall we call you?"
        message = Messages(text,dialogid=dialog.dialogid,number=from_number,timestamp=datetime.datetime.utcnow(),response=body,user=user)
        db.session.add(message)
        db.session.commit()
        ret_response = send_message(device,from_number,to_number, body)
    status = check_last_thread(from_number)
    if status == 'onboard':
        user.username = text
        db.session.commit()
        body = "Okay,%s ask any question such as What is malaria" % (text) 
        ret_response = send_message(device,from_number,to_number, body)
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
