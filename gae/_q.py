#!/usr/bin/env python
#
import re
import os
import cgi
import urllib
import jinja2
import webapp2
import json
import time

from random import randint
from datetime import datetime

import wsgiref.handlers
import logging

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import db

from google.appengine.ext.webapp.util import run_wsgi_app

JINJA_ENVIRONMENT = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
        extensions=['jinja2.ext.autoescape'],
        autoescape=True)

_STORAGE = 'gs'
_FILE = 'file'

DEFAULT_NAME = 'gucci'
DEFAULT_TIME = 'just now'
DEFAULT_CLASS = 'Science'

def get_random_color():
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

def question_key(question_name=DEFAULT_NAME):
    return ndb.Key('Question', question_name)

def class_key(class_name=DEFAULT_CLASS):
    return ndb.Key('Class', class_name)

class Keyword(db.Model):
    keyword = db.StringProperty()


class Question(ndb.Model):
    """ Models an individual Question entry with author, content, and date. """

    author = ndb.UserProperty()
    content = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    q_id = ndb.StringProperty('q_id')
    done = ndb.BooleanProperty('done')
    answered = ndb.BooleanProperty('answered')
    tally = ndb.IntegerProperty('tally')
    title = ndb.StringProperty('title')
    students = ndb.JsonProperty('students')
    removable = ndb.BooleanProperty('removable')


class Class(ndb.Model):
    """ Models an individual Class entry """

    creator = ndb.UserProperty()
    creation_time = ndb.DateTimeProperty(auto_now_add=True)
    number = ndb.StringProperty('number')
    title = ndb.StringProperty('title')
    teacher = ndb.StringProperty('teacher')
    tas = ndb.JsonProperty('tas')
    students = ndb.JsonProperty('students')
    valid_class = ndb.BooleanProperty('valid_class')


class OfficeHours(ndb.Model):
    """ Models and individual office hours instance """

    creator = ndb.UserProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    first_name = ndb.StringProperty('first_name')
    last_name = ndb.StringProperty('last_name')
    start_time = ndb.StringProperty('start_time')
    end_time = ndb.StringProperty('end_time')
    day = ndb.StringProperty('day')
    class_name = ndb.StringProperty('class_name')
    attending_count = ndb.IntegerProperty('count')


class Student(ndb.Model):
    """ Models an individual student entry """

    user = ndb.UserProperty()
    classes = ndb.JsonProperty('class_list')


class JoinOhPage(webapp2.RequestHandler):
    """ Handles joining an instance of office hours """

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


class ViewSchedulePage(webapp2.RequestHandler):
    """ Handles the viewing of each classes OH schedule """

    def get(self, class_name):
        
        url = users.create_logout_url(self.request.uri)
        url_linktext = 'Logout'

        
        class_query = Class.query(Class.title == class_name)
        class_ = class_query.fetch()
        if class_:
            current_class = class_[0]
            current_user = users.get_current_user()
            if current_user.user_id() in current_class.tas:
                is_ta = True
            else:
                is_ta = False

        else:
            is_ta = True

        oh_query = OfficeHours.query(OfficeHours.class_name == class_name) #.order(-OfficeHours.date)
        office_hours = oh_query.fetch()

        template = JINJA_ENVIRONMENT.get_template('join_oh.html')

        template_values = {
            'class_name': class_name,
            'office_hours': office_hours,
            'url': url,
            'url_linktext': url_linktext,
            'is_ta': is_ta
        }

        self.response.write(template.render(template_values))


class MyClassesPage(webapp2.RequestHandler):
    """ Handles selecting a class """

    def get(self):

        current_user = users.get_current_user()
        my_classes = []

        if current_user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            html_template = 'select_class.html'

            student_query = Student.query(Student.user == current_user)
            result = student_query.fetch()

            if result:
                current_student = result[0]
                if current_student.classes:
                    my_classes = current_student.classes
                    if not isinstance(my_classes, list):
                        my_classes = json.loads(my_classes)

            else:
                new_student = Student()
                new_student.user = current_user
                new_student.classes = []
                new_student.put()

        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
            html_template = 'login.html'

        template = JINJA_ENVIRONMENT.get_template(html_template)

        template_values = {
            'classes': my_classes,
            'url': url,
            'url_linktext': url_linktext,
        }

        self.response.write(template.render(template_values))


class JoinClassPage(webapp2.RequestHandler):
    """ Handles joining a class """

    def get(self):

        all_classes = DEFAULT_CLASS
        class_query = Class.query(Class.valid_class == True).order(-Class.creation_time)
        classes = class_query.fetch()

        current_user = users.get_current_user()

        student_query = Student.query(Student.user == current_user)
        student_ = student_query.fetch()

        if student_:
            current_student = student_[0]

        real_classes = []
        for class_ in classes:
            
            current_classes = current_student.classes
            if not isinstance(current_classes, list):
                current_classes = json.loads(current_classes)

            logging.info(class_.title)

            #if class_.title not in current_classes or class_.title is not None:
            #    real_classes.append(class_)

            if class_.title not in current_classes:
                logging.info('PARTAY!')
                if class_.title is not None:
                    real_classes.append(class_)

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            html_template = 'select_class.html'

        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
            html_template = 'login.html'

        template = JINJA_ENVIRONMENT.get_template('join_class.html')
        template_values = {
            'classes': real_classes,
            'url': url,
            'url_linktext': url_linktext,
        }

        self.response.write(template.render(template_values))


class QPage(webapp2.RequestHandler):
    """ Handles the displaying of the Q. """

    def get(self, queue):

        class_name = queue.split('+')[0]
        link_name = queue.split('+')[1]

        question_name = queue
        questions_query = Question.query(ancestor=question_key(queue)).order(-Question.tally)  # HERE ---------
        questions = questions_query.fetch()

        current_user = users.get_current_user()

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            is_current_user = True

        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
            is_current_user = False

        class_query = Class.query(Class.title == class_name)
        classes = class_query.fetch()

        if classes:
            current_class = classes[0]
            current_tas = current_class.tas

            current_students = current_class.students
            if not isinstance(current_students, list):
                current_students = json.loads(current_students)

            if current_user.user_id() in current_students:
                is_student = True

            else:
                is_student = True

            if not isinstance(current_tas, list):
                current_tas = json.loads(current_tas)

            if current_user.user_id() in current_tas:
                
                for question in questions:
                    question.removable = True

            else:
                for question in questions:
                    if not question.students:
                        question.students = []

                    if current_user.user_id() in question.students:
                        question.done = True

                    else:
                        question.done = False

                    if question.tally == 0:
                        question.answered = True
                        question.removable = True 

                    elif question.tally == 1 and question.author.user_id() == current_user.user_id():
                        question.removable = True

                    else:
                        question.removable = False

        else:
            is_student = False

        template = JINJA_ENVIRONMENT.get_template('index.html')
        template_values = {
                'url': url,
                'class_name': class_name, 
                'questions': questions,
                'question_name': question_name,
                'url_linktext': url_linktext,
                'removable': True,
                'name_tag': 'generic_tag',
                'question_time': DEFAULT_TIME,
                'current_user': is_student,
        }

        self.response.write(template.render(template_values))


class AltQPage(webapp2.RequestHandler):
    """ Handles the displaying of the Q. """

    def get(self, queue):

        class_name = queue.split('+')[0]
        link_name = queue.split('+')[1]

        question_name = queue
        questions_query = Question.query(ancestor=question_key(queue)).order(-Question.tally)  # HERE ---------
        questions = questions_query.fetch()

        current_user = users.get_current_user()

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            is_current_user = True

        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
            is_current_user = False

        class_query = Class.query(Class.title == class_name)
        classes = class_query.fetch()

        if classes:
            current_class = classes[0]
            current_tas = current_class.tas

            current_students = current_class.students
            if not isinstance(current_students, list):
                current_students = json.loads(current_students)

            if current_user.user_id() in current_students:
                is_student = True

            else:
                is_student = False

            if not isinstance(current_tas, list):
                current_tas = json.loads(current_tas)

            if current_user.user_id() in current_tas:
                
                for question in questions:
                    question.removable = True

            else:
                for question in questions:
                    if not question.students:
                        question.students = []

                    if current_user.user_id() in question.students:
                        question.done = True

                    else:
                        question.done = False

                    if question.tally == 0:
                        question.answered = True
                        question.removable = True 

                    elif question.tally == 1 and question.author.user_id() == current_user.user_id():
                        question.removable = True

                    else:
                        question.removable = False

        else:
            is_student = False

        template = JINJA_ENVIRONMENT.get_template('alt_index.html')
        template_values = {
                'url': url,
                'class_name': class_name, 
                'questions': questions,
                'question_name': question_name,
                'url_linktext': url_linktext,
                'removable': True,
                'name_tag': 'generic_tag',
                'question_time': DEFAULT_TIME,
                'current_user': is_student,
        }

        self.response.write(template.render(template_values))


class NewClass(webapp2.RequestHandler):
    """ Handles the creation of a new class """

    def get(self):

        class_name = DEFAULT_CLASS

        template = JINJA_ENVIRONMENT.get_template('new_class.html')
        template_values = {
            'class_name': class_name, 
        }

        self.response.write(template.render(template_values))


class NewQuestion(webapp2.RequestHandler):

    def get(self, question_name):

        template = JINJA_ENVIRONMENT.get_template('new_question.html')
        template_values = {
            'question_name': question_name,
        }

        self.response.write(template.render(template_values))


class NewOfficeHours(webapp2.RequestHandler):

    def get(self, class_name):

        template = JINJA_ENVIRONMENT.get_template('new_oh.html')
        template_values = {
            'class_name': class_name,
        }

        self.response.write(template.render(template_values))


class Map(webapp2.RequestHandler):

    def get(self):

        template = JINJA_ENVIRONMENT.get_template('map.html')
        template_values = {
            'class_name': 'maps',
        }  

        self.response.write(template.render(template_values))

class PostProblem(webapp2.RequestHandler):

    def post(self, arg):
        question_name = arg
        question = Question(parent=question_key(question_name))

        if users.get_current_user():
            question.author = users.get_current_user()

        question.title = self.request.get('title')
        question.content = self.request.get('content')
        question.q_id = self.get_question_id(question.author)
        question.answered = False
        question.done = True
        question.tally = 1
        question.students = [question.author.user_id()]
        question.put()

        query_params = {'question_name': question_name}
        self.redirect('/q/' + question_name)

    def get_question_id(self, author):
        return str(hash(author)) + str(datetime.now().microsecond)


class CreateClass(webapp2.RequestHandler):

    def post(self, arg):

        class_name = arg
        class_object = Class(parent=class_key(DEFAULT_CLASS))

        if users.get_current_user():
            class_object.creator = users.get_current_user()

        class_object.title = self.request.get('title')
        class_object.teacher = self.request.get('teacher')
        class_object.valid_class = True

        tas, students = [], []

        class_object.tas = []
        class_object.students = []

        class_object.put()

        self.redirect('/join')


class CreateOfficeHours(webapp2.RequestHandler):

    def post(self, class_name):

        office_hours = OfficeHours()

        if users.get_current_user():
            office_hours.creator = users.get_current_user()

        office_hours.first_name = self.request.get('first_name')
        office_hours.last_name = self.request.get('last_name')
        office_hours.location = self.request.get('location')
        office_hours.start_time = self.request.get('start_time')
        office_hours.end_time = self.request.get('end_time')
        office_hours.day = self.request.get('day')
        office_hours.class_name = class_name
        office_hours.put()

        self.redirect('/schedule/' + class_name)


class JoinQuestion(webapp2.RequestHandler):

    def post(self, arg):

        question_name = arg.split('|')[0]
        link_name = arg.split('|')[1]
        question_id = arg.split('|')[2]

        question = Question(parent=question_key(question_name))

        if users.get_current_user():
            joiner = users.get_current_user()

        questions_query = Question.query(Question.q_id == question_id)
        questions = questions_query.fetch()

        if questions:
            current_question = questions[0]
            other_students = current_question.students
            
            if joiner.user_id() in other_students: 
                current_question.done = None
                other_students.remove(joiner.user_id())
                current_question.tally -= 1
                current_question.students = other_students                

            else:
                other_students.append(joiner.user_id())
                current_question.students = other_students
                current_question.tally += 1
                current_question.done = True

            current_question.put()

        query_params = {'question_name': question_name}
        self.redirect('/q/' + question_name)


class JoinClassAsStudent(webapp2.RequestHandler):

    def post(self, arg):

        class_name = arg
        class_query = Class.query(Class.title == class_name)
        classes = class_query.fetch()
        current_user = users.get_current_user()

        if classes:
            current_class = classes[0]
            students_query = Student.query(Student.user == current_user)
            student = students_query.fetch()

            if not student:
                new_student = Student()
                new_student.user = current_user
                new_student.calsses = [current_class.title]
                new_student.put()

            else:
                current_student = student[0]
                if not current_student.classes:
                    current_student.classes = [current_class.title]

                else:
                    current_classes = current_student.classes
                    if not isinstance(current_classes, list):
                        current_classes = json.loads(current_classes)

                    if current_class.title not in current_classes:
                        current_classes.append(current_class.title)
                        current_student.classes = current_classes

                current_student.put()

            current_students = current_class.students 

            if not current_students:
                current_class.students = [current_user.user_id()]

            if not isinstance(current_students, list):
                current_students = json.loads(current_students)

            elif current_user.user_id() not in current_students:
                current_students.append(current_user.user_id())
                current_class.students = current_students

            current_class.put()

        self.redirect('/')


class JoinClassAsTA(webapp2.RequestHandler):

    def post(self, arg):

        class_name = arg
        class_query = Class.query(Class.title == class_name)
        classes = class_query.fetch()
        current_user = users.get_current_user()

        if classes:
            current_class = classes[0]
            students_query = Student.query(Student.user == current_user)
            student = students_query.fetch()

            if not student:
                new_student = Student()
                new_student.user = current_user
                new_student.calsses = [current_class.title]
                new_student.put()

            else:
                current_student = student[0]
                if not current_student.classes:
                    current_student.classes = [current_class.title]

                else:
                    current_classes = current_student.classes
                    if not isinstance(current_classes, list):
                        current_classes = json.loads(current_classes)

                    if current_class.title not in current_classes:
                        current_classes.append(current_class.title)
                        current_student.classes = current_classes

                current_student.put()

            current_tas = current_class.tas 

            if not current_tas:
                current_class.tas = [current_user.user_id()]

            elif not isinstance(current_tas, list):
                current_tas = json.loads(current_tas)

            if current_user.user_id() not in current_tas:
                current_tas.append(current_user.user_id())
                current_class.tas = current_tas

            current_class.put()

        self.redirect('/')


class Remove(webapp2.RequestHandler):

    def post(self, arg):

        question_name = arg.split('|')[0]
        question_id = arg.split('|')[1]

        questions_query = Question.query(ancestor=question_key(question_name)).order(-Question.date)
        questions = questions_query.fetch()

        for question in questions:

            if question.q_id == question_id:
                if question.answered == None:
                    question.answered = True

                else:
                    question.answered = True

                question.put()

        query_params = {'question_name': question_name}
        self.redirect('/q/' + question_name)


class RemoveClass(webapp2.RequestHandler):

    def post(self, class_title):

        current_user = users.get_current_user()
        student_query = Student.query(Student.user == current_user)
        current_student = student_query.fetch()

        if current_student:
            current_student = current_student[0]
            current_classes = current_student.classes

            if not isinstance(current_classes, list):
                current_classes = json.loads(current_classes)

            if class_title in current_classes:
                current_classes.remove(class_title)
                current_student.classes = current_classes
                current_student.put()

                class_query = Class.query(Class.title == class_title)
                class_ = class_query.fetch()
                if class_:
                    current_class = class_[0]

                    #if current_user.user_id() in current_class.students:
                    #       current_class.students.

        self.redirect('/')


class DeleteClass(webapp2.RequestHandler):

    def post(self, class_title):

        class_query = Class.query(Class.title == class_title)
        classes = class_query.fetch()

        if classes:
            class_ = classes[0]
            class_.valid_class = False  
            class_.put()

        else:

            logging.info('error deleting class')

        self.redirect('/join')

app = webapp2.WSGIApplication([
    (r'/', MyClassesPage),
    (r'/schedule/([^/]+)', ViewSchedulePage),
    (r'/join', JoinClassPage),
    (r'/q/([^/]+)', QPage),
    (r'/q/A+Phantom', QPage),
    (r'/q/B+Phantom', AltQPage),
    (r'/alt_q/([^/]+)', AltQPage),
    (r'/join_question/([^/]+)', JoinQuestion),
    (r'/join_class_as_student/([^/]+)', JoinClassAsStudent), 
    (r'/join_class_as_ta/([^/]+)', JoinClassAsTA),
    (r'/remove/([^/]+)', Remove),
    (r'/remove_class/([^/]+)', RemoveClass),
    (r'/delete_class/([^/]+)', DeleteClass),
    (r'/newQ/([^/]+)', NewQuestion),
    (r'/new_class', NewClass),
    (r'/new_oh/([^/]+)', NewOfficeHours),
    (r'/ask/([^/]+)', PostProblem),
    (r'/create_class/([^/]+)', CreateClass),
    (r'/create_oh/([^/]+)', CreateOfficeHours),
    (r'/map', Map),
], debug=True)
