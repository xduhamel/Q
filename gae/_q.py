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
import cgi

from random import randint
from datetime import datetime, timedelta

import wsgiref.handlers
import logging

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import images 


from google.appengine.ext.webapp.util import run_wsgi_app

JINJA_ENVIRONMENT = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
        extensions=['jinja2.ext.autoescape'],
        autoescape=True)

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
    contacts = ndb.JsonProperty('contacts')
    pic_id = ndb.StringProperty()
    is_pic = ndb.BooleanProperty('is_pic')
    ask_time = ndb.StringProperty('ask_time')


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
    identifier = ndb.IntegerProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    first_name = ndb.StringProperty('first_name')
    last_name = ndb.StringProperty('last_name')
    start_time = ndb.StringProperty('start_time')
    end_time = ndb.StringProperty('end_time')
    day = ndb.StringProperty('day')
    class_name = ndb.StringProperty('class_name')
    attending_count = ndb.IntegerProperty('count')
    ended = ndb.BooleanProperty('ended')
    active = ndb.BooleanProperty('acitve')
    scheduled = ndb.BooleanProperty('scheduled')
    start_date_time = ndb.DateTimeProperty('start_date_time')
    end_date_time = ndb.DateTimeProperty('end_date_time')


class Student(ndb.Model):
    """ Models an individual student entry """

    user = ndb.UserProperty()
    classes = ndb.JsonProperty('class_list')
    prof_pic = ndb.BlobProperty()


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

        oh_query = OfficeHours.query(OfficeHours.class_name == class_name).order(+OfficeHours.start_date_time)
        office_hours = oh_query.fetch()

        if office_hours:
            for oh in office_hours:
                
                # hack to account for utc time difference
                now = datetime.now() - timedelta(hours=7)
                
                if oh.end_date_time < now:
                    oh.ended = True
                    oh.active = False
                    oh.scheduled = False

                elif oh.start_date_time < now and now < oh.end_date_time:
                    oh.ended = False
                    oh.active = True
                    oh.scheduled = False

                else:
                    oh.ended = False
                    oh.active = False 
                    oh.scheduled = True
        
        if not office_hours:
            no_office_hours = True
        
        else:
            no_office_hours = False

        if len(class_name) > 10:
            nick_name = class_name[0:10] + '...'
        else:
            nick_name = class_name 

        template = JINJA_ENVIRONMENT.get_template('join_oh.html')

        template_values = {
            'no_oh': no_office_hours,
            'nick_name': nick_name,
            'class_name': class_name,
            'office_hours': office_hours,
            'url_linktext': url_linktext,
            'is_ta': is_ta,
            'url': url
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
                current_student = Student()
                current_student.user = current_user
                current_student.classes = []
                current_student.prof_pic = None
                current_student.put()

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

        upload_url = blobstore.create_upload_url('/upload')

        self.response.write(template.render(template_values))
        # self.response.out.write('<form action="%s" method="POST" enctype="multipart/form-data">' % upload_url)
        # self.response.out.write("""Upload File: <input type="file" name="file"><br> <input type="submit"
        # name="submit" value="Submit"> </form></body></html>""")

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
            if current_classes is None:
                current_classes = []

            elif not isinstance(current_classes, list):
                current_classes = json.loads(current_classes)



            #if class_.title not in current_classes or class_.title is not None:
            #    real_classes.append(class_)

            if class_.title not in current_classes:
                if len(class_.title) is not 0:
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
        _id = int(link_name)

        question_name = queue
        questions_query = Question.query(ancestor=question_key(queue)).order(-Question.tally)
        questions = questions_query.fetch()
        current_user = users.get_current_user()

        oh_query = OfficeHours.query(OfficeHours.identifier == _id)
        oh = oh_query.fetch()
        if oh:
            current_office_hours = oh[0]
            current_office_hours.attending_count += 1
            current_office_hours.put()

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
                    if question.tally == 0:
                        question.answered = True
                        question.removable = True  
                is_ta = False

            else:
                is_ta = True
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
                'link_name': link_name,
                'is_student': is_ta,
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

    def get(self, arg):

        question_name = arg.split('|')[0]
        link_name = arg.split('|')[1]
        upload_url = blobstore.create_upload_url('/ask/%s' % question_name)

        template = JINJA_ENVIRONMENT.get_template('new_question.html')
        template_values = {
            'upload_url': upload_url, 
            'question_name': question_name,
            'link_name': link_name,
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


class ViewQuestionMembers(webapp2.RequestHandler):

    def get(self, q_id):

        question_query = Question.query(Question.q_id == q_id)
        question = question_query.fetch()

        if question:
            current_question = question[0]
            contacts = current_question.contacts

            template = JINJA_ENVIRONMENT.get_template('question_members.html')
            
            template_values = {
                'contacts': contacts,
            }

            self.response.write(template.render(template_values))


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
        office_hours.identifier = datetime.now().microsecond
        office_hours.attending_count = 0
        office_hours.ended = False
        office_hours.active = False
        office_hours.scheduled = True

        convert_start = office_hours.day + ' ' + office_hours.start_time
        convert_end = office_hours.day + ' ' + office_hours.end_time

        office_hours.start_date_time = datetime.strptime(convert_start, '%Y-%m-%d %H:%M')
        office_hours.end_date_time = datetime.strptime(convert_end, '%Y-%m-%d %H:%M')

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
                # REMOVE EMAIL FROM CONTACTS  

                if not current_question.contacts:
                    current_question.contacts = []

                elif joiner.email() in current_question.contacts:
                    current_contacts = current_question.contacts
                    current_contacts.remove(joiner.email())
                    current_question.contacts = current_contacts           

            else:
                other_students.append(joiner.user_id())
                current_question.students = other_students
                current_question.tally += 1
                current_question.done = True

                if not current_question.contacts:
                    current_question.contacts = [joiner.email()]

                else:
                    current_contacts = current_question.contacts
                    current_contacts.append(joiner.email())
                    current_question.contacts = current_contacts

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
                    if current_user.user_id() in current_class.tas:
                        new_ta_list = current_class.tas
                        new_ta_list.remove(current_user.user_id())
                        current_class.tas = new_ta_list
                        current_class.put()

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


class PostProblem(blobstore_handlers.BlobstoreUploadHandler):

    def post(self, arg):
        question_name = arg
        question = Question(parent=question_key(question_name))

        if users.get_current_user():
            question.author = users.get_current_user()
        
        upload_files = self.get_uploads('file')
        if upload_files:
            blob_info = upload_files[0]
            if blob_info:
                question.pic_id = str(blob_info.key())
                question.is_pic = True
        else:
            question.pic_id = None
            question.is_pic = False

        question.title = self.request.get('title')
        question.content = self.request.get('content')
        question.q_id = self.get_question_id(question.author)
        question.answered = False
        question.done = True
        question.tally = 1
        question.students = [question.author.user_id()]
        question.contacts = [question.author.email()]
        question.ask_time = datetime.strftime(datetime.now() - timedelta(hours=7), "%a, %b, %d %X")
        question.put()

        query_params = {'question_name': question_name}
        self.redirect('/q/' + question_name)

    def get_question_id(self, author):
        return str(hash(author)) + str(datetime.now().microsecond)

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):

    def post(self):
        upload_files = self.get_uploads('file')
        blob_info = upload_files[0]
        self.redirect('/blob/%s' % blob_info.key())

class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, resource):
        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        #logging.ino(blob_info)
        self.send_blob(blob_info)


class Blob(webapp2.RequestHandler):

    def get(self, blob_key):

        template = JINJA_ENVIRONMENT.get_template('blob.html')
        template_values = {
            'blob_key': blob_key,
        }

        self.response.write(template.render(template_values))


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
    (r'/question_members/([^/]+)', ViewQuestionMembers),
    (r'/_ah/upload', UploadHandler),
    (r'/q/serve/([^/]+)?', ServeHandler),
    (r'/blob/([^/]+)', Blob)
], debug=True)
