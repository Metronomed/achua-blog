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
import urllib

from google.appengine.ext import webapp
from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.datastore.datastore_query import Cursor

class BlogPost(ndb.Model):
	blog = ndb.StringProperty()
	title = ndb.StringProperty()
	modDate = ndb.DateTimeProperty(auto_now = True)
	createDate = ndb.DateTimeProperty(auto_now_add = True)
	owner = ndb.StringProperty()
	content = ndb.TextProperty()
	tags = ndb.StringProperty(repeated=True)
	
class Blog(ndb.Model):
	blogname = ndb.StringProperty()
	owner = ndb.StringProperty()
	#posts = ndb.StructuredProperty(BlogPost, repeated=True)

class MainHandler(webapp2.RequestHandler):
	def get(self):
		context = {	}
		if users.get_current_user():
			user = str(users.get_current_user())
			context['user'] =  user + ': '
			context['login_url'] = users.create_logout_url(self.request.uri)
			context['login_text'] = "Log Out"
			makeblog = '<a href = "/make-blog">make a new blog</a>.'
			context['view_text'] = "Welcome, " + str(users.get_current_user()) + '! Here are your blogs. Alternatively, ' + makeblog
			#link to blogs
			query = Blog.query(Blog.owner == user)
			bloglist = """\
			<ul>
			"""
			for b in query:
				bname = b.blogname
				bloglist += '<li><a href="/b/' +user + '/'+ bname + '/?cursor=0">' + bname + '</a><br>'
			context['blog_list'] = bloglist + """\
			</ul>
			"""
		else:
			context['user'] = "You're not logged in! "
			context['login_url'] = users.create_login_url(self.request.uri)
			context['login_text'] = "Log In"
			context['view_text'] = "You will need to log in to access your blogs."
		self.response.write(template.render(
			os.path.join(os.path.dirname(__file__), 
			'index.html'),
			context))

class MakeBlog(webapp2.RequestHandler):
	def get(self):
		context = {}
		if users.get_current_user():
			context['user'] = str(users.get_current_user()) + ': '
			context['login_url'] = users.create_logout_url(self.request.uri)
			context['login_text'] = "Log Out"
		else:
			context['user'] = "You're not logged in! Something's wrong. "
			context['login_url'] = users.create_login_url(self.request.uri)
			context['login_text'] = "Log In"
		self.response.write(template.render(
			os.path.join(os.path.dirname(__file__), 
			'create_blog.html'),
			context))
	def post(self):
		context = {}
		if users.get_current_user():
			context['user'] = str(users.get_current_user()) + ': '
			context['login_url'] = users.create_logout_url(self.request.uri)
			context['login_text'] = "Log Out"
		else:
			context['user'] = "You're not logged in! Something's wrong. "
			context['login_url'] = users.create_login_url(self.request.uri)
			context['login_text'] = "Log In"
		user = str(users.get_current_user())
		bname = cgi.escape(self.request.get('title'))
		context['bname'] = bname
		query = Blog.query(Blog.owner == user, Blog.blogname == bname)
		if query.count(limit=1):
			self.response.write(template.render(
			os.path.join(os.path.dirname(__file__), 
			'dupe_blog.html'),
			context))
		else:
			b = Blog()
			b.owner = user
			b.blogname = bname
			b.put()
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'create_blog_success.html'),
				context))

class ViewBlog(webapp2.RequestHandler):
	def get(self, oname, bname):
		context = {}
		if users.get_current_user():
			context['login_url'] = users.create_logout_url(self.request.uri)
			context['login_text'] = "Log Out"
			context['name'] = users.get_current_user()
		else:
			context['login_url'] = users.create_login_url(self.request.uri)
			context['login_text'] = "Log In"
			context['name'] = str(users.get_current_user())
		curs = Cursor(urlsafe=self.request.get('cursor'))
		owner = oname
		query = BlogPost.query(BlogPost.owner == oname, BlogPost.blog == bname)
		results, next_curs, more = query.order(-BlogPost.createDate).fetch_page(10, start_cursor = curs)
		tenposts = ''
		for p in results:
			tenposts += '<h2>' + p.title + """\
			</h2>\
			<p>Created on: """ + p.createDate.strftime('%Y/%m/%d %H:%M:%S')
			+ """\
			<p>Modified on: """ + p.modDate.strftime('%Y/%m/%d %H:%M:%S')
			+ """\
			<p>""" + p.content[0:min(500,p.content.length)] + """\
			\
			Tags:
			"""
		context['post_list'] = tenposts
		if more and next_curs:
			nextlink = '<a href="/b/'+oname+'/'+bname+'/?cursor='+ next_curs.urlsafe()+'">Previous posts</a>'
		self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'blog.html'),
				context))

class MakePost(webapp2.RequestHandler):
	def get(self):
		context = {	}
		if users.get_current_user():
			context['login_url'] = users.create_logout_url(self.request.uri)
			context['login_text'] = "Log Out"
			context['name'] = users.get_current_user()
		else:
			context['login_url'] = users.create_login_url(self.request.uri)
			context['login_text'] = "Log In"
			context['name'] = str(users.get_current_user())
		self.response.write(template.render(
			os.path.join(os.path.dirname(__file__), 
			'create_post.html'),
			context))
	
	def post(self):
		context = {}
		context['author'] = str(users.get_current_user())
		context['title'] = cgi.escape(self.request.get('title'))
		
		text = cgi.escape(self.request.get('content'))
		text = re.sub(r'\b(https?://\S*\.(png|jpg|gif)\b)', '<img src="\g<0>">', text)
		#replaces hyperlink if not preceded with '="' (indicating image replaced)
		text = re.sub(r'\b(?<!=")(https?://\S*)\b', '<a href="\g<0>">\g<0></a>', text)
		text = text.replace('\n', '<br />')
		context['content'] = text
		
		#gets unique tags from tag string
		tagsplit = cgi.escape(self.request.get('tags')).split(',')
		tagsplit = list(set([item.lstrip().rstrip() for item in tagsplit]))
		tags = ", ".join(tagsplit)
		context['tags'] = tags
		
		t = datetime.datetime.now()
		context['time'] = t.strftime('%Y/%m/%d %H:%M:%S')
		b = BlogPost()
		b.owner = str(users.get_current_user())
		b.title = context['title']
		b.content = context['content']
		b.blog = "Bloggy"
		b.tags = tagsplit
		b.put()
		self.response.write(template.render(
			os.path.join(os.path.dirname(__file__), 
			'post_success.html'),
			context))

class UploadImg(webapp2.RequestHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/upload')
		context = { }
		context['name'] = users.get_current_user()
		context['upload_url'] = upload_url
		self.response.write(template.render(
			os.path.join(os.path.dirname(__file__), 
			'upload_image.html'),
			context))

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
	def post(self):
		upload_files = self.get_uploads('file')
		blob_info = upload_files[0]
		#user = cgi.escape(self.request.get('user'))
		imgtype = blob_info.filename[-4:]
		redirUrl = '/upload-success/'+str(blob_info.key())+imgtype
		self.redirect(redirUrl)

class UploadSuccess(webapp2.RequestHandler):
	def get(self, resource):
		context = { }
		context['name'] = str(users.get_current_user())
		context['plink'] = self.request.host_url+"/serve/"+resource
		self.response.write(template.render(
			os.path.join(os.path.dirname(__file__), 
			'up_image_success.html'),
			context))

class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
	def get(self, resource, ftype):
		resource = str(urllib.unquote(resource))
		resource = re.sub('\.(png|jpg|gif)$', '', resource)
		blob_info = blobstore.BlobInfo.get(resource)
		self.send_blob(blob_info)

app = webapp2.WSGIApplication([
    ('/', MainHandler), 
    ('/make-blog', MakeBlog),
    ('/make-post', MakePost),
    ('/upload-img', UploadImg),
    ('/upload-success/([^/]+)?', UploadSuccess),
    ('/upload', UploadHandler),
    ('/serve/([^/]+\.(png|jpg|gif))?', ServeHandler),
    ('/b/([^/]+)?/([^/]+)?/', ViewBlog)
], debug=True)
