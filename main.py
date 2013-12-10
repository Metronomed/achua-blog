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
import cgi
import webapp2
import datetime
import re
from google.appengine.ext import ndb
from google.appengine.api import users
from google.appengine.ext.webapp import template

class BlogPost(ndb.Model):
	title = ndb.StringProperty()
	modDate = ndb.DateTimeProperty(auto_now = True)
	createDate = ndb.DateTimeProperty()
	user = ndb.StringProperty()
	content = ndb.StringProperty()


class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write('Hello world!')

class MakePost(webapp2.RequestHandler):
	def get(self):
		context = {
			
		}
		context['author'] = users.get_current_user()
		
		self.response.write(template.render(
			os.path.join(os.path.dirname(__file__), 
			'create_post.html'),
			context))
	
	def post(self):
		context = {}
		context['author'] = users.get_current_user()
		context['title'] = cgi.escape(self.request.get('title'))
		text = cgi.escape(self.request.get('content'))
		splittext = text.split(text)
		text = re.sub(r'(\bhttps?://\S*\b)', '<a href="\g<0>">\g<0></a>', text)
		text = text.replace('\n', '<br />')
		context['content'] = text
		
		t = datetime.datetime.now()
		context['time'] = t.strftime('%Y/%m/%d %H:%M:%S')
		self.response.write(template.render(
			os.path.join(os.path.dirname(__file__), 
			'post_success.html'),
			context))

app = webapp2.WSGIApplication([
    ('/', MainHandler), 
    ('/make-post', MakePost)
], debug=True)
