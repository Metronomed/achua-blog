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
from google.appengine.api import search

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
	tags = ndb.StringProperty(repeated=True)
	#posts = ndb.StructuredProperty(BlogPost, repeated=True)

class MainHandler(webapp2.RequestHandler):
	def get(self):
		context = {	}
		if users.get_current_user():
			user = str(users.get_current_user())
			context['user'] =  user + ': '
			context['login_url'] = users.create_logout_url(self.request.uri)
			context['login_text'] = "Log Out"
			makeblog = '<a href = "/make-blog">make a new blog</a>. '
			context['view_text'] = "Welcome, " + str(users.get_current_user()) + '! Here are your blogs. Alternatively, ' + makeblog + 'Or, <a href = "/upload-img/">upload an image to use</a>.'
			#link to blogs
			query = Blog.query(Blog.owner == user)
			bloglist = """\
			<ul>
			"""
			for b in query:
				bname = b.blogname
				bloglist += '<li><a href="/b/' +user + '/'+ bname + '/?cursor='  + "00".encode('base64') + '">' + bname + '</a><br>'
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
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'create_blog.html'),
				context))
		else:
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'wrong_person.html'),
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
			context['name'] = str(users.get_current_user()) + ': '
		else:
			context['login_url'] = users.create_login_url(self.request.uri)
			context['login_text'] = "Log In"
			context['name'] = ''
		cursorstring = self.request.get('cursor')
		curs = Cursor(urlsafe=cursorstring)
		owner = oname
		query = BlogPost.query(BlogPost.owner == oname, BlogPost.blog == bname)
		results, next_curs, more = query.order(-BlogPost.createDate).fetch_page(10, start_cursor = curs)
		tenposts = ''
		for p in results:
			posttags = []
			for tag in p.tags:
				posttags.append(tagLink(oname, bname, tag) + "00".encode('base64') + '">' + tag + '</a>')
			tagcode = ', '.join(posttags)
			postkey = p.key.urlsafe()
			tenposts += '<h2><a href = "/p/' + postkey + '">'+ p.title + '</a></h2><p>Created on: ' + p.createDate.strftime('%Y/%m/%d %H:%M:%S') + ' Last modified on: ' + p.modDate.strftime('%Y/%m/%d %H:%M:%S')+ '<p>' + renderContent(p.content[0:min(500,p.content.__len__())]) + '<p>Tags: ' + tagcode
		context['post_list'] = tenposts
		nextlink = ''
		if more and next_curs:
			nextlink = '<a href="/b/'+oname+'/'+bname+'/?cursor='+ next_curs.urlsafe()+'">Previous posts</a>'
		context['nextlink'] = nextlink
		context['title'] = bname
		options = ""
		if oname == str(users.get_current_user()):
			options += '<a href = "/make-post/'+bname+'">Add a new post</a> '
			options += '<a href = "/upload-img/">Upload an image</a> '
			options += '<a href = "/">Return to Home</a> '
		options += "Create an RSS Feed"
		context['options'] = options
		
		tag_list = ''
		q = Blog.query(Blog.blogname == bname, Blog.owner == oname)
		for p in q:
			alltags = p.tags
			for tag in alltags:
				tag_list += tagLink(oname, bname, tag) + "00".encode('base64') + '">' + tag + '</a><br>'
		context['tag_list'] = tag_list
		self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'blog.html'),
				context))

class MakePost(webapp2.RequestHandler):
	def get(self, blog):
		context = {	}
		user = str(users.get_current_user())
		q = Blog.query(Blog.blogname == blog, Blog.owner == user)
		if q.count(limit=1):
			#okay to make
			if users.get_current_user():
				context['login_url'] = users.create_logout_url(self.request.uri)
				context['login_text'] = "Log Out"
				context['name'] = users.get_current_user()
			else:
				context['login_url'] = users.create_login_url(self.request.uri)
				context['login_text'] = "Log In"
				context['name'] = str(users.get_current_user())
			context['blog'] = blog
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'create_post.html'),
				context))
		else:
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'wrong_person.html'),
				context))
			
class CreatedPost(webapp2.RequestHandler):	
	def post(self):
		if users.get_current_user():
			b = BlogPost()
			b.put()
			context = {}
			user = str(users.get_current_user())
			context['author'] = user
			context['title'] = cgi.escape(self.request.get('title'))
		
			origtext = cgi.escape(self.request.get('content'))
			context['content'] = renderContent(origtext)
		
			#gets unique tags from tag string
			tagsplit = cgi.escape(self.request.get('tags')).split(',')
			tagsplit = list(set([item.lstrip().rstrip() for item in tagsplit]))
			tagsplit.sort()
			tags = ", ".join(tagsplit)
			context['tags'] = tags
			blog = cgi.escape(self.request.get('blog'))
			context['blog'] = blog
		
			b.owner = user
			b.title = context['title']
			b.content = origtext
			b.blog = blog
			b.tags = tagsplit
			postkey = b.put()
			context['mtime'] = b.modDate
			context['ctime'] = b.createDate
			context['editlink'] = '/edit-post/'+postkey.urlsafe()
			context['bloglink'] = '/b/'+b.owner + '/'+b.blog + '/?cursor='  + "00".encode('base64')
		
			q = Blog.query(Blog.blogname == blog, Blog.owner == user)
			for p in q:
				bkey = p.key
				theblog = bkey.get()
				newtags = theblog.tags
				newtags += tagsplit
				newtags = list(set(newtags))
				newtags.sort()
				theblog.tags = newtags
				theblog.put()
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'post_success.html'),
				context))
		else:
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'wrong_person.html'),
				context))

class ViewPost(webapp2.RequestHandler):
	def get(self, postkey):
		safekey = ndb.Key(urlsafe=postkey)
		post = safekey.get()
		context = {}
		context['author'] = post.owner
		text = post.content
		context['content'] = renderContent(text)
		context['title'] = post.title
		context['ctime'] = post.createDate
		context['mtime'] = post.modDate
		tags = post.tags
		context['tags'] = ', '.join(tags) 
		edit = ''
		if post.owner == str(users.get_current_user()):
			edit += '<a href ="/edit-post/'+safekey.urlsafe()+'">Edit your post</a>'
		context['edit'] = edit	
		self.response.write(template.render(
			os.path.join(os.path.dirname(__file__), 
			'post.html'),
			context))
		
class EditPost(webapp2.RequestHandler):
	def get(self, postkey):
		safekey = ndb.Key(urlsafe=postkey)
		post = safekey.get()
		context = {}
		if post.owner != str(users.get_current_user()):
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'wrong_person.html'),
				context))
		else:
			context['name'] = post.owner
			context['posttitle'] = post.title
			context['posttext'] = post.content
			context['blog'] = post.blog
			context['posttags'] = ', '.join(post.tags)
			context['postkey'] = safekey.urlsafe()
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'edit_post.html'),
				context))
		
class EditedPost(webapp2.RequestHandler):
	def post(self):
		if users.get_current_user():
			context = {}
			context['author'] = str(users.get_current_user())
			context['title'] = cgi.escape(self.request.get('title'))
		
			origtext = cgi.escape(self.request.get('content'))
			context['content'] = renderContent(origtext)
		
			#gets unique tags from tag string
			tagsplit = cgi.escape(self.request.get('tags')).split(',')
			tagsplit = list(set([item.lstrip().rstrip() for item in tagsplit]))
			tagsplit.sort()
			tags = ", ".join(tagsplit)
			context['tags'] = tags
		
			postkey = self.request.get('postkey')
			safekey = ndb.Key(urlsafe=postkey)
			bpost = safekey.get()
			bpost.title = context['title']
			bpost.content = origtext
			bpost.tags = tagsplit
			bpost.put()
			context['blog'] = bpost.blog
			context['mtime'] = bpost.modDate
			context['ctime'] = bpost.createDate
			context['editlink'] = '/edit-post/'+safekey.urlsafe()
			context['bloglink'] = '/b/'+bpost.owner + '/'+bpost.blog + '/?cursor='  + "00".encode('base64')
		
			blogtags = compileTags(context['author'], context['blog'])
			query = Blog.query(Blog.blogname == bpost.blog, Blog.owner == str(users.get_current_user()))
			for p in query:
				bkey = p.key
				theblog = bkey.get()
				theblog.tags = blogtags
				theblog.put()
		
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'post_success.html'),
				context))
		else:
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'wrong_person.html'),
				context))

class UploadImg(webapp2.RequestHandler):
	def get(self):
		if users.get_current_user():
			upload_url = blobstore.create_upload_url('/upload')
			context = { }
			context['name'] = users.get_current_user()
			context['upload_url'] = upload_url
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'upload_image.html'),
				context))
		else:
			self.response.write(template.render(
				os.path.join(os.path.dirname(__file__), 
				'wrong_person.html'),
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

class TagSearch(webapp2.RequestHandler):
	def get(self, owner, blog, tag):
		context = {}
		if users.get_current_user():
			context['login_url'] = users.create_logout_url(self.request.uri)
			context['login_text'] = "Log Out"
			context['name'] = str(users.get_current_user()) + ': '
		else:
			context['login_url'] = users.create_login_url(self.request.uri)
			context['login_text'] = "Log In"
			context['name'] = ''
		context['tag'] = tag
		cursorstring = self.request.get('cursor')
		curs = Cursor(urlsafe=cursorstring)
		query1 = BlogPost.query(BlogPost.owner == owner, BlogPost.blog == blog, BlogPost.tags == tag)
		results1, next_curs, more = query1.order(-BlogPost.createDate).fetch_page(10, start_cursor = curs)
		tenposts = ''
		for p in results1:
			posttags = []
			for tag in p.tags:
				posttags.append(tagLink(owner, blog, tag) + "00".encode('base64') + '">' + tag + '</a>')
			tagcode = ', '.join(posttags)
			postkey = p.key.urlsafe()
			tenposts += '<h2><a href = "/p/' + postkey + '">'+ p.title + '</a></h2><p>Created on: ' + p.createDate.strftime('%Y/%m/%d %H:%M:%S') + ' Last modified on: ' + p.modDate.strftime('%Y/%m/%d %H:%M:%S')+ '<p>' + renderContent(p.content[0:min(500,p.content.__len__())]) + '<p>Tags: ' + tagcode
		context['post_list'] = tenposts
		nextlink = ''
		if more and next_curs:
			nextlink = tagLink(owner, blog, tag) +  next_curs.urlsafe()+'">Previous posts</a>'
 		context['nextlink'] = nextlink
		self.response.write(template.render(
			os.path.join(os.path.dirname(__file__), 
			'tagsearch.html'),
			context))

class RSS(webapp2.RequestHandler):
	def get(self, owner, blog):
		self.response.write("hello world")

def tagLink(owner, blog, tag):
	return '<a href="/t/'+owner+'/'+blog+'/'+tag+'/?cursor='

def renderContent(text):
	text = re.sub(r'\b(https?://\S*\.(png|jpg|gif)\b)', '<img src="\g<0>">', text)
	#replaces hyperlink if not preceded with '="' (indicating image replaced)
	text = re.sub(r'\b(?<!=")(https?://\S*)\b', '<a href="\g<0>">\g<0></a>', text)
	text = text.replace('\n', '<br>')
	return text
	
def compileTags(owner, blog):
	query = BlogPost.query(BlogPost.owner == owner, BlogPost.blog == blog)
	taglist = []
	for p in query:
		taglist += p.tags
	taglist = list(set(taglist))
	taglist.sort()
	return taglist

app = webapp2.WSGIApplication([
    ('/', MainHandler), 
    ('/make-blog', MakeBlog),
    ('/make-post/([^/]+)?', MakePost),
    ('/created-post', CreatedPost),
    ('/upload-img/', UploadImg),
    ('/upload-success/([^/]+)?', UploadSuccess),
    ('/upload', UploadHandler),
    ('/serve/([^/]+\.(png|jpg|gif))?', ServeHandler),
    ('/b/([^/]+)?/([^/]+)?/', ViewBlog),
    ('/p/([^/]+)?', ViewPost),
    ('/edited-post/', EditedPost),
    ('/edit-post/([^/]+)?', EditPost),
    ('/t/([^/]+)?/([^/]+)?/([^/]+)?/', TagSearch),
    ('/rss/([^/]+)?/([^/]+)?', RSS)
], debug=True)