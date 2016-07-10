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
import traceback
import random
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

ACCESS_TOKEN =  os.environ['FACEBOOK_ACCESS_TOKEN']
VERIFY_TOKEN =  os.environ['FACEBOOK_VERIFY_TOKEN']

#ACCESS_TOKEN = "EAAW2qV8uIzIBAIjpfZCPaqxVkCQoJYwVeuZAFDfMCsqp7IXAA9kp5oRUUggVCwdcJOPt28d2OCaxAYOJ1UrTpWMPCDRq35n7u2oHaeL1KJ8ltKMrLX6Q3lDOdWBgLuXwuCZCn8xH3VUyAKDGRPlDFlvc9t2HaTZCyhibASUvmK1xATBRsn8m"
#VERIFY_TOKEN = "secret"


from models import *
from utils import *

def get_profile(number):
   user = User.query.filter_by(phone_number=number).first()
   return user

def get_fb_user_profile(fid):
   user = User.query.filter_by(facebook_id=fid).first()
   return user

def get_fb_profile(fbid):
   user_details_url = "https://graph.facebook.com/v2.6/%s"%fbid
   user_details_params = {'fields':'first_name,last_name,profile_pic', 'access_token': ACCESS_TOKEN}
   user_details = requests.get(user_details_url, user_details_params).json()
   return user_details

def create_user(sender,user_details):
    user = User(timestamp=datetime.datetime.utcnow(),facebook_id=sender)
    db.session.add(user)
    db.session.commit()
    user = get_fb_user_profile(sender)
    dialog_file = open("resources/pizza_sample.xml", 'r')
    dialog = DialogUtils(app)
    dialogid = dialog.createDialog(dialog_file, sender)
    dialog = Dialog(name=sender,dialogid=dialogid['dialog_id'])
    db.session.add(dialog)
    user.firstname = user_details['first_name']
    user.lastname = user_details['last_name']
    user.dialog_id = dialog.dialogid
    print dialog.dialogid
    db.session.commit()
    return user

def check_conversations(user):
    if Messages.query.filter_by(user_id=user.id).order_by(Messages.id.desc()).first():
        print "some messages have come in"
        status = True
    else:
        print 'no messages registered yet, send them a welcome'
        status = False
    return status
    

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
        if message.response == "Hello there! I'm Afya, your own personal health assistant. Before we get started can I ask you what your name is?":
            status = 'ask_name'
        else:
            status = 'process_questions'
    else:
        print 'no messages registered yet'
        status = False
    return status

def post_message(text,dialogid,number,body,userid):
    message = Messages(message=text,dialogid=dialogid,number=number,response=body,user=userid)
    db.session.add(message)
    db.session.commit()

def save_fb_message(message,dialogid,number,userid):
    message = Messages(message=message,dialogid=dialogid,number=number,user=userid)
    db.session.add(message)
    db.session.commit()
    return message

def save_fb_response(message,dialogid,response,user):
    response = Response(message=message, dialogid=dialogid,response=response,user=user)
    db.session.add(response)
    db.session.commit()

def chunkstring(string, length):
    return (string[0+i:length+i] for i in range(0, len(string), length))


def classify(text):
    classification = None
    try:
        nlp = NLPUtils(app)
        classes = nlp.service.classify('3a84dfx64-nlc-5204', text)
        confidence = classes['classes'][0]['confidence']
        if confidence > 0.9:
            classification = classes['top_class']
        else:
            classification = 'low_classification'
            #class_response = nlp.service.classify('c115edx72-nlc-1770', text)
            #confidence_response = class_response['classes'][0]['confidence']
            #if confidence_response > 0.9:
            #    if class_response['top_class'] == 'YES':
            #        classification = 'SendYes'
            #    if class_response['top_class'] == 'NO':
            #        classification = 'SendNo'
       
        ####to do we will need to add an else here to check low confidence levels
    except WatsonException as err:
        print err
    return classification

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
    #we first get the last message
    status = check_last_thread(from_number)
    print status 
    create_user = None
    if get_profile(from_number):
        user = get_profile(from_number)
    else:
        create_user = True
        user = User(phone_number=from_number,timestamp=datetime.datetime.utcnow())
        db.session.add(user)
        db.session.commit()
        user = User.query.filter_by(phone_number=from_number).first()
        dialogid = dialog.createDialog(dialog_file, from_number)
        dialog = Dialog(name=from_number,dialogid=dialogid['dialog_id'])
        db.session.add(dialog)
        db.session.commit()
        body = "Hello there! I'm Afya, your own personal health assistant. Before we get started can I ask you what your name is?"
        post_message(text,dialog.dialogid,from_number,body,user.id)
        ret_response = send_message(device,from_number,to_number, body)
    if status == 'ask_name':
        user.username = text
        db.session.commit()
        body = "Great %s, feel free to ask me any health related questions you may have. I'm here to look after your well being. Remember, just like your doctor, the more you interact with me the more I learn about you to keep you healthy.I specialize in questions such as 'What is malaria?' or 'What are symptoms of malaria?'. By asking me such questions, I can learn what's important to you" % (text)
        dialog = Dialog.query.filter_by(name=from_number).order_by(Dialog.id.desc()).first()
        post_message(text,dialog.dialogid,from_number,body,user.id)
        ret_response = send_message(device,from_number,to_number, body)
    if status == 'process_questions' and create_user is None:
        #now send it to watson to gets its classification
        classification = classify(text)
        if classification == 'SearchDisease':
            dialog = Dialog.query.filter_by(name=from_number).order_by(Dialog.id.desc()).first()
            body = search_disease(text)
            if body is None:
                body = "Hm sorry about this %s, but it seems I can't find anything on that. I will however remember that this is important for you. Could you ask another question?" % (user.username)
            print body
            post_message(text,dialog.dialogid,from_number,body,user.id)    
            ret_response = send_message(device,from_number,to_number, body)
        elif classification == 'DiseaseSymptoms':
            dialog = Dialog.query.filter_by(name=from_number).order_by(Dialog.id.desc()).first()
            body = disease_symptoms(text)
            if body is None:
                body = "Hm sorry about this %s, but it seems I can't find anything on that. I will however remember that this is important for you. Could you ask another question?" % (user.username)
            post_message(text,dialog.dialogid,from_number,body,user.id)
            ret_response = send_message(device,from_number,to_number, body)
        elif classification == 'Treatment':
            dialog = Dialog.query.filter_by(name=from_number).order_by(Dialog.id.desc()).first()
            body = disease_treatment(text)
            if body is None:
                body = "Hm sorry about this %s, but it seems I can't find anything on that. I will however remember that this is important for you. Could you ask another question?" % (user.username)
            post_message(text,dialog.dialogid,from_number,body,user.id)
            ret_response = send_message(device,from_number,to_number, body)
        elif classification == 'low_classification':
            dialog = Dialog.query.filter_by(name=from_number).order_by(Dialog.id.desc()).first()
            body = 'Sorry I could not find anything on that, %s. Could you ask another question?' % (user.username)
            post_message(text,dialog.dialogid,from_number,body,user.id)
            ret_response = send_message(device,from_number,to_number, body)
        else:
            pass  
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

def reply(user_id, msg):
    data = {
        "recipient": {"id": user_id},
        "message": {"text": msg}
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data)
    return resp


def reply_button(user_id, msg):
    data = {
        "recipient": {"id": user_id},
        "message": {
          "attachment":{
            "type":"template", 
            "payload":{
              "template_type":"button",
              "text":msg,
              "buttons": [{
                "type":"postback",
                "title":"Yes",
                "payload": "YES"
               },{
                "type":"postback",
                "title":"No",
                "payload": "NO"
               }]
              }
          }
        }
    }
    resp = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + ACCESS_TOKEN, json=data)
    print resp.content
    return resp


@app.route('/', methods=['GET'])
def handle_verification():
    if request.args['hub.verify_token'] == VERIFY_TOKEN:
        return request.args['hub.challenge']
    else:
        return "Invalid verification token"


@app.route('/', methods=['POST'])
def handle_incoming_messages():
    try:
      data = json.loads(request.data)
      print 'here'
      #we check for any response payloads
      response_payloads = data['entry'][0]['messaging'][0]
      if 'postback' in response_payloads.keys():
          answer = response_payloads['postback']['payload']
          sender = response_payloads['sender']['id']
          user = get_fb_user_profile(sender) 
          if answer == "YES":
              res = "Ok great, I'm glad I could help %s. Please ask me anything else you have on your mind. I'm here to provide you quick access to the information that matters, your health." % (user.firstname)
              reply(sender,res)
          if answer == 'NO':
              res = "I'm sorry about that %s, can you ask your question a different way?" % (user.firstname)
              reply(sender,res)

      text = data['entry'][0]['messaging'][0]['message']['text'] # Incoming Message Text
      sender = data['entry'][0]['messaging'][0]['sender']['id'] # Sender ID
      user_details= get_fb_profile(sender)
      user = get_fb_user_profile(sender)
      user_firstname = user_details['first_name']
      if not user:
          #we create the user in our users table
          user = create_user(sender,user_details)
      # we not need to know if this is a continuing convo or new
      status = check_conversations(user)
      if status is False:
          message = save_fb_message(text,user.dialog_id,"from_facebook",user.id)
          text = "Great %s, feel free to ask me any health related questions you may have. I'm here to look after your well being." % (user_firstname)
          response = reply(sender, text)
          if response.status_code == 200:
              save_fb_response(message,user.dialog_id,text,user.id)
              text = "I specialize in questions such as 'What is malaria?' or 'What are symptoms of malaria?'. By asking me such questions, I can learn what's important to you"
              response = reply(sender, text)
              save_fb_response(message,user.dialog_id,text,user.id)
      else:
          message = save_fb_message(text,user.dialog_id,"from_facebook",user.id)
          #now send it to watson to gets its classification
          classification = classify(text)
          #we remove the question mark when folks ask questions, WILL NEED to resolve this comprehensively in future
          text = text.replace('?', '')
          body_exists = True
          if classification == 'SearchDisease':
              body = search_disease(text)
              if body is None:
                  body_exists = False
                  body = "Hm sorry about this %s, but it seems I can't find anything on that. I will however remember that this is important for you. Could you ask another question?" % (user.firstname)
              if body_exists:
                  reply_sentences = ["I'm glad I can help. Here's an answer I found", "Here is what I found, %s" % (user.firstname),
                                     "Here is what I found. I hope this is useful", "I hope this answer helps %s" % (user.firstname)]
                  sentence = random.choice(reply_sentences)
                  reply(sender,sentence)
              if len(body) > 320:
                  lists = list(chunkstring(body, 320))
                  for chunk in lists:
                      response = reply(sender, chunk)
                      save_fb_response(message,user.dialog_id,chunk,user.id)
              else:
                  response = reply(sender, body)
                  save_fb_response(message,user.dialog_id,body,user.id)
              if body_exists:
                  reply_button(sender, "Did this help?")
          elif classification == 'DiseaseSymptoms':
              body = disease_symptoms(text)
              if body is None:
                  body_exists = False 
                  body = "Hm sorry about this %s, but it seems I can't find anything on that. I will however remember that this is important for you. Could you ask another question?" % (user.firstname)
              if body_exists:
                  reply_sentences = ["I'm glad I can help. Here's an answer I found", "Here is what I found, %s" % (user.firstname),
                                     "Here is what I found. I hope this is useful", "I hope this answer helps %s" % (user.firstname)]
                  sentence = random.choice(reply_sentences)
                  reply(sender,sentence)
              if len(body) > 320:
                  lists = list(chunkstring(body, 320))
                  for chunk in lists:
                      response = reply(sender, chunk)
                      save_fb_response(message,user.dialog_id,chunk,user.id)
              else:
                  response = reply(sender, body)
                  save_fb_response(message,user.dialog_id,body,user.id)
              if body_exists:
                  reply_button(sender, "Did this help?")
          elif classification == 'Treatment':
              body = disease_treatment(text)
              if body is None:
                  body_exists = False
                  body = "Hm sorry about this %s, but it seems I can't find anything on that. I will however remember that this is important for you. Could you ask another question?" % (user.firstname)
              if body_exists:
                  reply_sentences = ["I'm glad I can help. Here's an answer I found", "Here is what I found, %s" % (user.firstname),
                                     "Here is what I found. I hope this is useful", "I hope this answer helps %s" % (user.firstname)]
                  sentence = random.choice(reply_sentences)
                  reply(sender,sentence)
              if len(body) > 320:
                  lists = list(chunkstring(body, 320))
                  for chunk in lists:
                      response = reply(sender, chunk)
                      save_fb_response(message,user.dialog_id,chunk,user.id)
              else: 
                  response = reply(sender, body)
                  save_fb_response(message,user.dialog_id,body,user.id)
              if body_exists:
                  reply_button(sender, "Did this help?")          
          elif classification == 'SendYes':
                  res = "Ok great, I'm glad I could help %s. Please ask me anything else you have on your mind. I'm here to provide you quick access to the information that matters, your health." % (user.firstname)
                  reply(sender,res)
          elif classification == 'SendNo':
                  res = "I'm sorry about that %s, can you ask your question a different way?" % (user.firstname)
                  reply(sender,res)
          elif classification == 'low_classification':
              body = 'Sorry I could not find anything on that, %s. Could you ask another question?' % (user.firstname)
              response = reply(sender, body)
              save_fb_response(message,user.dialog_id,body,user.id)
          else:
              pass
           
      #payload = {'recipient': {'id': sender}, 'message': {'text': text}} # We're going to send this back
      #r = requests.post('https://graph.facebook.com/v2.6/me/messages/?access_token=' + ACCESS_TOKEN, json=payload) # Lets send it
      #print r.content
    except Exception as e:
      print traceback.format_exc() # something went wrong
    return "Hello Worlds" #Not Really Necessary


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port,debug=True)
#if __name__ == "__main__":
#    port = int(os.environ.get("PORT", 5000))
#    app.run(host='0.0.0.0', port=port)

# Sample successful output
# Text received: Hello, from Plivo - From: 2222222222
