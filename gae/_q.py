#!/usr/bin/env python
#
import re
import os
import cgi
import urllib
import jinja2
import webapp2
from random import randint
#import boto
import time
from datetime import datetime
#import cloudstorage as gcs
import wsgiref.handlers

import logging

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import db

from google.appengine.ext.webapp.util import run_wsgi_app

#from gslib.third_party.oauth2_plugin import oauth2_plugin

JINJA_ENVIRONMENT = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
        extensions=['jinja2.ext.autoescape'],
        autoescape=True)

#_INSTANCE_NAME = 'q-versace:a'

_STORAGE = 'gs'
_FILE = 'file'

DEFAULT_NAME = 'gucci'
DEFAULT_COLOR = 'blue'
FIRST_INITIAL = 'R'
DEFAULT_TIME = 'just now'
DEFAULT_CLASS = 'l'

def question_key(question_name=DEFAULT_NAME):
    """ Yo """
    return ndb.Key('Question', question_name)

class Keyword(db.Model):
    keyword = db.StringProperty()

class Question(ndb.Model):
    """ Models an individual Question entry with author, content, and date. """

    author = ndb.UserProperty()
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    q_id = ndb.StringProperty(indexed=False)
    done = ndb.BooleanProperty()
    answered = ndb.BooleanProperty()
    tally = ndb.IntegerProperty()

class JoinOhPage(webapp2.RequestHandler):

    def get(self):

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'

        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template = JINJA_ENVIRONMENT.get_template('join_oh.html')
        template_values = {
            'url': url,
            'url_linktext': url_linktext,
        }

        self.response.write(template.render(template_values))

class SelectClassPage(webapp2.RequestHandler):

    def get(self):

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'

        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template = JINJA_ENVIRONMENT.get_template('select_class.html')
        template_values = {
            'url': url,
            'url_linktext': url_linktext,
        }

        self.response.write(template.render(template_values))

class MainPage(webapp2.RequestHandler):

    def get(self):

        question_name = self.request.get('question_name', DEFAULT_CLASS)
        questions_query = Question.query(ancestor=question_key(question_name)).order(-Question.date)
        questions = questions_query.fetch(8)

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'

        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'


        color = self.get_color_for_email('SWAAG')

        for question in questions:
            question.color = self.get_random_color()
            
        template = JINJA_ENVIRONMENT.get_template('index.html')
        template_values = {
                'questions': questions,
                'question_name': question_name,
                'url': url,
                'url_linktext': url_linktext,
                'name_color': color,
                'name_tag': 'generic_tag',
                'author_initial': FIRST_INITIAL,
                'question_time': question_time,
        }

        self.response.write(template.render(template_values))

    def get_random_color(self):
        random_index = randint(0, 5)
        return {0: 'red',
                1: 'orange',
                2: 'yellow',
                3: 'green',
                4: 'blue',
                5: 'purple'}.get(random_index)

    def get_color_for_email(self, email_address):
        hash_number = hash(email_address)
        color_index = hash_number % 5
        return {0: 'blue',
                1: 'yellow',
                2: 'orange',
                3: 'red',
                4: 'purple',
                5: 'green'}.get(color_index)

class QPage(webapp2.RequestHandler):

    def get(self, queue):

        question_name = queue
        questions_query = Question.query(ancestor=question_key(queue)).order(-Question.date)
        questions = questions_query.fetch(8)

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            current_user = True

        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
            current_user = False

        for question in questions:
            question.color = self.get_random_color()

        template = JINJA_ENVIRONMENT.get_template('index.html')
        template_values = {
                'questions': questions,
                'question_name': question_name,
                'url': url,
                'url_linktext': url_linktext,
                'name_tag': 'generic_tag',
                'question_time': DEFAULT_TIME,
                'current_user': current_user,
        }

        self.response.write(template.render(template_values))

    def get_random_color(self):
        random_index = randint(0, 5)
        return {0: 'red',
                1: 'orange',
                2: 'yellow',
                3: 'green',
                4: 'blue',
                5: 'purple'}.get(random_index)

    def get_color_for_email(self, email_address):
        hash_number = hash(email_address)
        color_index = hash_number % 5
        return {0: 'blue',
                1: 'yellow',
                2: 'orange',
                3: 'red',
                4: 'purple',
                5: 'green'}.get(color_index)

"""
class Problem(webapp2.RequestHandler):

    def post(self):
        question_name = self.request.get('question_name', DEFAULT_NAME)
        question = Question(parent=question_key(question_name))

        if users.get_current_user():
            question.author = users.get_current_user()

        question.content = self.request.get('content')
        question.answered = self.request.get('question_answered', False)
        question.put()

        query_params = {'question_name': question_name}
        self.redirect('/q/' + urllib.urlencode(query_params))
"""

class Problem(webapp2.RequestHandler):

    def post(self, arg):
        question_name = arg
        question = Question(parent=question_key(question_name))

        if users.get_current_user():
            question.author = users.get_current_user()

        question.content = self.request.get('content')
        question.answered = False
        question.q_id = self.get_question_id(question.author)
        question.done = False 
        question.tally = 1
        question.put()

        query_params = {'question_name': question_name}
        self.redirect('/q/' + question_name)

    def get_question_id(self, author):
        q = str(hash(author)) + str(datetime.now().microsecond)
        logging.info(q)
        logging.info('*****')
        return q

class Join(webapp2.RequestHandler):

    def post(self, arg):

        question_name = arg.split('+')[0]
        question_id = arg.split('+')[1]

        question = Question(parent=question_key(question_name))

        if users.get_current_user():
            joiner = users.get_current_user()

        questions_query = Question.query(ancestor=question_key(question_name)).order(-Question.date)
        questions = questions_query.fetch()

        for question in questions:
            if question.q_id == question_id:
                if question.done == True:
                    question.tally -= 1
                    question.done = None
                else:
                    question.tally += 1
                    question.done = True 
                question.put()

        query_params = {'question_name': question_name}
        self.redirect('/q/' + question_name)

class Remove(webapp2.RequestHandler):

    def post(self, arg):
        question_name = arg.split('+')[0]
        question_id = arg.split('+')[1]
        
        questions_query = Question.query(ancestor=question_key(question_name)).order(-Question.date)
        questions = questions_query.fetch()

        logging.info('$$$$$$')
        logging.info(question_name)
        logging.info(question_id)

        for question in questions: 
            if question.q_id == question_id:
                logging.info('WOAH')
                logging.info(question)
                if question.answered == None:
                    question.answered = True
                else:
                    question.answered = True 

                question.put()

        query_params = {'question_name': question_name}
        self.redirect('/q/' + question_name)

app = webapp2.WSGIApplication([
    (r'/', SelectClassPage),
    (r'/schedule', JoinOhPage), 
    (r'/q', MainPage),
    (r'/q/([^/]+)', QPage), 
    (r'/ask/([^/]+)', Problem),
    (r'/join/([^/]+)', Join),
    (r'/remove/([^/]+)', Remove)
], debug=True)
