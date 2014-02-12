#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2

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
        question_name = self.request.get('name', DEFAULT_NAME)

        questions_query = Question.query(
                ancestor=question_key(question_name)).order(-Question.date)
        questions = questions_query.fetch(10)

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
                'questions': questions,
                'question_name': urllib.quote_plus(question_name),
                'url': url,
                'url_linktext': url_linktext,
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))

        self.response.write('Tiurd ... !')

class Problem(webapp2.RequestHandler):

    def post(self):

        question_name = self.request.get('question_name',
                                         DEFAULT_NAME)
        question = Question(parent=question_key(question_name))

        if users.get_current_user():
            question.author = users.get_current_user()

        question.content = self.request.get('content')
        question.put()

        query_params = {'question_name': question_name}
        self.redirect('/?' + urllib.urlencode(query_params))


app = webapp2.WSGIApplication([
    ('/', MainPage)
    ('/sign', Question),
], debug=True)
