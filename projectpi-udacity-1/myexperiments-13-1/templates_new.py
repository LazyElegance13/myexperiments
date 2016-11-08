# -*- coding: utf-8 -*-
"""
    Created on Thu Nov  3 03:26:15 2016
    
    @author: Lucifer_Angel
    """
import re

import os
import jinja2
import webapp2
import hashlib
import hmac
import sys
#import urllib
import urllib2
from xml.dom import minidom
from string import letters
import random
import logging

from google.appengine.api import memcache
from google.appengine.ext import db

#
DEBUG = os.environ['SERVER_SOFTWARE'].startswith('Development')

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)



#
def console(s):
    sys.stderr.write('%s\n' % repr(s))

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)


#UTILITIES

#months = ['January', 'February', 'March', 'April',
#          'May', 'June', 'July', 'August', 'September',
#          'October', 'November', 'December']
#month_abbvs = dict((m[:3].lower(), m) for m in months)


#def valid_month(month):
#    if month:
#        short_month = month[:3].lower()
#        return month_abbvs.get(short_month)

#def valid_day(day):
#    if day and day.isdigit():
#        day = int(day)
#        if day > 0 and day <= 31:
#            return day

#def valid_year(year):
#    if year and year.isdigit():
#        year = int(year)
#        if year > 1900 and year < 2020:
#            return year

def escape_html(s):
    # Steve's second solution
    import cgi
    return cgi.escape(s, quote = True)

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    if USER_RE.match(username):
        return username

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    if PASS_RE.match(password):
        return password

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    if not email or EMAIL_RE.match(email):
        return True

SECRET = "ohcrap" # should ideally be stored in a separate imported file on the production server

def hash_str(s):
    return hmac.new(SECRET, s).hexdigest()

def make_secure_val(s):
    return "%s|%s" % (s, hash_str(s))

def check_secure_val(h):
    #my implementation
    #l =  h.find(",")
    #print h[0:l]
    # if hash_str(h[0:l]) == h[l+1:]:
    #    return h[0:l]
    # steve's implementation
    val = h.split('|')[0]
    if h == make_secure_val(val):
        return val

# BLOG
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    
    def render_str(self, template, **params):
        params['user'] = self.user
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))
    
    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))
    
    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)
    
    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))
    
    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')
    
    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)

##User Stuff
def make_salt(length = 5):
    return "".join(random.choice(letters) for x in range(length))

def make_pw_hash(name, pw, salt=None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return "%s,%s" % (salt, h)

def valid_pw(name, pw, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, pw, salt)
#    return h == make_pw_hash(name, pw, h[-5:])

def users_key(group='default'):
    return db.Key.from_path('users', group)

class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty()
    
    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())
    
    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u
    
    @classmethod
    def register(cls, name, pw, email = None):
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email)
    
    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u
##### Blog Stuff
def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)


class Post(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created =  db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)
    
    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("blogpost.html", p = self)

class BlogFront(Handler):
    def get(self):
        posts = greetings = Post.all().order('-created')
        #        posts = db.GqlQuery("SELECT * FROM Post ORDER by created DESC LIMIT 10")
        self.render('blog.html', posts = posts)

class Permalink(Handler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent = blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return
        
        self.render('permalink.html', post=post)


class NewBlogPost(Handler):
    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/login")

    def post(self):
        if not self.user:
            self.redirect("/blog")
        
        subject = self.request.get("subject")
        content = self.request.get("content")
        
        if subject and content:
            p = Post(parent = blog_key(), subject = subject, content = content)
            p.put()
            self.redirect("/blog/%s"% str(p.key().id()))
        else:
            error = "we need both a subject and content!"
            self.render("newpost.html", subject=subject, content=content, error=error)


class SignupHandler(Handler):
    def get(self):
        self.render('signup.html')
    
    def post(self):
        have_error =False
        self.username = self.request.get("username")
        self.password = self.request.get("password")
        self.verify = self.request.get("verify")
        self.email = self.request.get("email")
        
        params = dict(username = self.username,
                      email = self.email)
        if not valid_username(self.username):
            params['error_username'] = "That's not a valid username."
            have_error = True
        if not valid_password(self.password):
            params['error_password'] = "That's not a valid password."
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your password's didn't match."
            have_error = True
                                                  
        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True
                                                            
                                                              
        if have_error:
            self.render('signup.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class Register(SignupHandler):
    def done(self):
        # make sure the user doesn't already exist
        u = User.by_name(self.username)
        if u:
            msg = "That user already exits."
            self.render("signup.html", error_username = msg)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()
            
            self.login(u)
            self.redirect('/blog')

class Login(Handler):
    def get(self):
        self.render("login.html")
    
    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        
        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/blog')
        else:
            msg = 'Invalid login'
            self.render('login.html', error = msg)

class Logout(Handler):
    def get(self):
        self.logout()
        self.redirect('/blog')


#####################################################################
# FORM
#form="""
#<form method="post">
#    What is your birthday?
#    <br>
#    <label>
#       Month
#  <input type="text" name="month" value=%(month)s>
#        </label>
#<label>
# Day
#<input type="text" name="day" value=%(day)s></label>
#<label>Year <input type="text" name="year" value=%(year)s></label>
#<div style="color: red">%(error)s</div>
#<br>
#<br>
#<input type="submit">

#</form>
#"""
#class FormHandler(webapp2.RequestHandler):
#    def write_form(self, error="", month="", day="", year="" ):
#        self.response.out.write(form % {"error" : error,
#                                        "month": escape_html(month),
#                                        "day" : escape_html(day),
#                                        "year" : escape_html(year)})

#    def get(self):
#     self.write_form()

#def post(self):
#user_month = self.request.get('month')
#user_day = self.request.get('day')
#user_year = self.request.get('year')

#month = valid_month(user_month)
#day = valid_day(user_day)
#year = valid_year(user_year)

#if not (month and day and year):
#    self.write_form("That doesn't look valid to me, friend.", user_month, user_day, user_year)
#else:
#    self.redirect("thanks")

#class ThanksHandler(webapp2.RequestHandler):
#    def get(self):
#            self.response.write("That's a toltally valid day!")

# ROT13

class RotHandler(Handler):
    #    def write_form(self, text=""):
    #        self.response.out.write(rot % {"text": escape_html(text)})
    
    def get(self):
        self.render('rot13-form.html')
    
    def post(self):
        rot13 = ''
        text = self.request.get('text')
        if text:
            rot13 = text.encode('rot13')
        
        self.render('rot13-form.html', text = rot13)

# COOKIE

class CookieCount(Handler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        visits = 0
        visit_cookie_str = self.request.cookies.get('visits')
        if visit_cookie_str:
            cookie_val= check_secure_val(visit_cookie_str)
            if cookie_val:
                visits = int(cookie_val)
        # make sure visits is an int
        #if visits.isdigit():
        #    visits= int(visits) + 1
        #else:
        #    visits = 0
        visits += 1
        
        new_cookie_val = make_secure_val(str(visits))
        
        self.response.headers.add_header('Set-Cookie', 'visits=%s' % new_cookie_val)
        
        if visits > 1000:
            self.write("You are the best ever")
        else:
            self.write("You've been here %s times!" % visits)

# FIZZBUZZ

class FizzHandler(Handler):
    def get(self):
        n = self.request.get('n', 0)
        n = n and int(n)
        self.render("fizzbuzz.html", n=n)

# SHOPPING LIST
class MainPage(Handler):
    def get(self):
        items = self.request.get_all("food")
        self.render("shopping_list.html", items = items)


# ASCII CHAN

art_key = db.Key.from_path('ASCIIChan', 'arts')


class Art(db.Model):
    title = db.StringProperty(required = True)
    art = db.TextProperty(required = True)
    created =  db.DateTimeProperty(auto_now_add = True)
    coords = db.GeoPtProperty()

GMAP_URL ="https://maps.googleapis.com/maps/api/staticmap?&zoom=0&size=380x263&maptype=roadmap&"
#
#"http://maps.googleapis.com/maps/api/staticmap?size=380x263&;sensor=false&"
API_KEY = "&key=AIzaSyCQDJtZX1E0Nv50cXo3A0Rza7xnJtxprGQ"

IP_URL = "http://freegeoip.net/xml/"
def get_coords(ip):
    #ip = "4.2.2.2"
    #ip = "23.24.209.141"
    #ip = "12.215.42.19"
    url = IP_URL + ip
    #logging.info(url)
    content = None
    try:
        #    request = urllib.request.Request(url)
        #   response = urllib.request.urlopen(request)
        #  content = response.read()
        content = urllib2.urlopen(url).read()
    except urllib2.URLError:
        return

    if content:
        d = minidom.parseString(content)
        lon = d.getElementsByTagName("Longitude")
        lat = d.getElementsByTagName("Latitude")
        if lon and lat:
            lon, lat = lon[0].childNodes[0].nodeValue, lat[0].childNodes[0].nodeValue
            if lon and lat:
                return db.GeoPt(lat, lon)


def gmaps_img(points):
    markers = '&'.join('markers=%s,%s' % (p.lat, p.lon) for p in points)
    return GMAP_URL + markers + API_KEY

def top_arts(update = False):
    key = 'top'
    arts = memcache.get(key)
    if arts is None or update:
        logging.error("DB QUERY")
        arts= db.GqlQuery("SELECT * FROM Art ORDER BY created DESC ", art_key)
        
        arts = list(arts) # prevents running multiple queries
        memcache.set(key, arts)
    return arts

class AsciiHandler(Handler):
    def render_front(self, title="", art="", error=""):
        arts = top_arts()
        img_url = None
        points = []
        for a in arts:
            if a.coords:
                points.append(a.coords)
        #        points = filter(None,(a.coords for a in arts))
        
        
        if points:
            img_url = gmaps_img(points)
            #self.response.write(repr(points))
            self.render("front.html", title=title, art=art, error=error, arts=arts, img_url=img_url)
                    
    def get(self):
        #self.write(self.request.remote_addr)
        #self.write(repr(get_coords(self.request.remote_addr)))
        self.render_front()
                            
    def post(self):
        title = self.request.get("title")
        art = self.request.get("art")
            
        if title and art:
            a = Art(title = title, art = art)
            coords = get_coords(self.request.remote_addr)
            if coords:
                a.coords = coords
                                                            
                a.put()
                top_arts(True)
                self.redirect("/ascii")
        else:
            error = "we need both a title and some artwork!"
            self.render_front(title, art, error)
#####################################################################
class Welcome(Handler):
    def get(self):
        username = self.request.get('username')
        if valid_username(username):
            self.render('welcome.html', username = username)
        else:
            self.redirect("/signup")



app = webapp2.WSGIApplication([
                               ('/',                MainPage),
                               #('/thanks',         ThanksHandler),
                               #('/form',           FormHandler),
                               ('/rot13',           RotHandler),
                               ('/signup',          Register),
                               ('/welcome',         Welcome),
                               ('/fizz',            FizzHandler), 
                               ('/ascii',           AsciiHandler), 
                               ('/blog',            BlogFront),
                               ('/login',           Login),
                               ('/logout',          Logout),
                               ('/blog/([0-9]+)',   Permalink),
                               ('/cookie',          CookieCount),
                               ('/blog/newpost',    NewBlogPost)],
                              debug=True)

