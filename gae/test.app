#!/usr/bin/env python
#

import os
import cgi
import urllib
import jinja2
import webapp2
from random import randint
#import boto
import time
#import cloudstorage as gcs
import wsgiref.handlers

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
DEFAULT_CLASS = 'Q'

def create_bucket(bucket_name):
    # URI scheme for Google Cloud Storage.
    _STORAGE = 'gs'
    _LOCAL_FILE = 'file'

    now = time.time()
    _BUCKET = "{0}-{1}".format(bucket_name, now)


def question_key(question_name=DEFAULT_NAME):
    """ Yo """
    return ndb.Key('Question', question_name)

class Question(ndb.Model):
    """ Models an individual Question entry with author, content, and date. """

    author = ndb.UserProperty()
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)

class OH(ndb.Model):
    """ Models an individual Office Hours entry with host, time, location, and class. """
    host = ndb.UserProperty()

class MainPage(webapp2.RequestHandler):

    def get(self):

        question_name = self.request.get('question_name', DEFAULT_CLASS)
        questions_query = Question.query(

        ancestor=question_key(question_name)).order(-Question.date)
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
                'question_name': DEFAULT_CLASS,
                'url': url,
                'url_linktext': url_linktext,
                'name_color': color,
                'name_tag': 'generic_tag',
                'author_initial': FIRST_INITIAL,
                'question_time': DEFAULT_TIME,
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

class SelectClassPage(webapp2.RequestHandler):

    def get(self):

        if users.get_current_user():
            url = users.create_logout_url(self.request_uri)
            url_linktext = 'Logout'

        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template = JINJA_ENVIRONMENT.get_template('index.html')
        template_values = {}

        self.response.write(template.render(template_values))

class Class(webapp2.RequestHandler):

    def post(self):
        class_name = self.request.get('class_name', DEFAULT_CLASS)

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
        self.redirect('/?' + urllib.urlencode(query_params))


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/select_class', SelectClassPage),
    ('/sign', Problem),
], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
