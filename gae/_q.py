#!/usr/bin/env python
#

import os
import urllib
import jinja2
import webapp2

from google.appengine.api import users
from google.appengine.ext import ndb

JINJA_ENVIRONMENT = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
        extensions=['jinja2.ext.autoescape'],
        autoescape=True)

DEFAULT_NAME = 'gucci'

def question_key(question_name=DEFAULT_NAME):
    """ Yo """
    return ndb.Key('Question', question_name)

class Question(ndb.Model):
    """ Models an individual Question entry with author, content, and date. """

    author = ndb.UserProperty()
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)

class MainPage(webapp2.RequestHandler):

    def get(self):
        #self.populate_q()
        question_name = self.request.get('question_name', DEFAULT_NAME)

        questions_query = Question.query(
                ancestor=question_key(question_name)).order(-Question.date)

        questions = questions_query.fetch(10)

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            template = JINJA_ENVIRONMENT.get_template('index.html')

        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
            template = JINJA_ENVIRONMENT.get_template('login.html')

        template_values = {
                'questions': questions,
                'question_name': type(questions),
                'url': url,
                'url_linktext': url_linktext,
        }

        #template = JINJA_ENVIRONMENT.get_template('login.html')
        self.response.write(template.render(template_values))

    def get_name_from_email(self, email):
        a = email.partition('@')
        return a[0]

class Problem(webapp2.RequestHandler):

    def post(self):

        question_name = self.request.get('question_name', DEFAULT_NAME)
        question = Question(parent=question_key(question_name))

        if users.get_current_user():
            question.author = users.get_current_user()

        question.content = self.request.get('content')
        question.put()

        query_params = {'question_name': question_name}
        self.redirect('/?' + urllib.urlencode(query_params))


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/sign', Problem),
], debug=True)
