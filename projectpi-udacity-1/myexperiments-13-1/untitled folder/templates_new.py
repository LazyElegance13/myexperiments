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

DEBUG = os.environ['SERVER_SOFTWARE'].startswith('Development')

SECRET = "jamuura"
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

art_key = db.Key.from_path('ASCIIChan', 'arts')

def console(s):
    sys.stderr.write('%s\n' % repr(s))
form="""
<form method="post">
    What is your birthday?
    <br>
    <label>
        Month 
        <input type="text" name="month" value=%(month)s>
        </label>
    <label>
        Day 
        <input type="text" name="day" value=%(day)s></label>
    <label>Year <input type="text" name="year" value=%(year)s></label>  
    <div style="color: red">%(error)s</div>    
    <br>
    <br>    
    <input type="submit">
</form>
"""

months = ['January', 'February', 'March', 'April', 
             'May', 'June', 'July', 'August', 'September', 
             'October', 'November', 'December']
month_abbvs = dict((m[:3].lower(), m) for m in months)

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
        
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))
        
class MainPage(Handler):
    def get(self):
        items = self.request.get_all("food")
        self.render("shopping_list.html", items = items)        
  
def valid_month(month):
    if month:
        short_month = month[:3].lower() 
        return month_abbvs.get(short_month)

def valid_day(day):
    if day and day.isdigit():
        day = int(day)
        if day > 0 and day <= 31:
            return day

def valid_year(year):
    if year and year.isdigit():
        year = int(year)
        if year > 1900 and year < 2020:
            return year

class FormHandler(webapp2.RequestHandler):
    def write_form(self, error="", month="", day="", year="" ):
        self.response.out.write(form % {"error" : error, 
                                        "month": escape_html(month), 
                                        "day" : escape_html(day), 
                                        "year" : escape_html(year)})
    
    def get(self):
        self.write_form()
        
    def post(self):
        user_month = self.request.get('month')
        user_day = self.request.get('day')
        user_year = self.request.get('year')
        
        month = valid_month(user_month)
        day = valid_day(user_day)
        year = valid_year(user_year)
        
        if not (month and day and year):
            self.write_form("That doesn't look valid to me, friend.", user_month, user_day, user_year)
        else:            
            self.redirect("thanks")

class ThanksHandler(webapp2.RequestHandler):
    def get(self):
            self.response.write("That's a toltally valid day!")

def escape_html(s):
# Steve's second solution
    import cgi
    return cgi.escape(s, quote = True)

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
    
class SignupHandler(Handler):
    def get(self):
        self.render('signup.html')
    
    def post(self):
        username_cookie_str = self.request.cookies.get('username')
        if username_cookie_str:
            cookie_val= check_secure_val(visit_cookie_str)
            if cookie_val:
                self.redirect('/blog?username=' + username)
        else

            have_error =False
            username = self.request.get("username")
            password= self.request.get("password")
            verify = self.request.get("verify")
            email = self.request.get("email")
        
            params = dict(username = username, email = email)
            username = valid_username(username)

            if not valid_username(username):
                params['error_username'] = "That's not a valid username."
                have_error = True
        
            if not valid_password(password):
                params['error_password'] = "That's not a valid password."
                have_error = True
            elif password != verify:
                params['error_verify'] = "Your password's didn't match."
                have_error = True

            if not valid_email(email):
                params['error_email'] = "That's not a valid email."
                have_error = True
        
            if have_error:
                self.render('signup.html', **params)
            else:
                self.response.headers['Content-Type'] = 'text/plain'
                new_cookie_val = make_secure_val(str(username))
                self.response.headers.add_header('Set-Cookie', 'username=%s' % new_cookie_val)
                self.redirect('/welcome?username=' + username)

class Welcome(Handler):
    def get(self):
        username = self.request.get('username')
        if valid_username(username):
            self.render("welcome.html", username = username)
        else:
            self.redirect("signup")
    
class FizzHandler(Handler):
    def get(self):
        n = self.request.get('n', 0)
        n = n and int(n)              
        self.render("fizzbuzz.html", n=n)        

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

class Post(db.Model):
    title = db.StringProperty(required = True)
    bodytext = db.TextProperty(required = True)
    created =  db.DateTimeProperty(auto_now_add = True)


class BlogHandler(Handler):
    def get(self):
        posts = db.GqlQuery("SELECT * FROM Post ORDER by created DESC LIMIT 10")
        self.render('blog.html', posts=posts)
        
class NewBlogPost(Handler):
    def render_post(self, title="", bodytext="", error=""):
        self.render("newpost.html", title=title, bodytext=bodytext, error=error)    
     
    def get(self):
        self.render_post()
        
    def post(self):
        title = self.request.get("title")
        bodytext = self.request.get("bodytext")

        if title and bodytext:
            b = Post(title = title, bodytext = bodytext)
            b_key = b.put()
            self.redirect("/blog/%d"% b_key.id())
        else:
            error = "we need both a title and a body!"
            self.render_post(title, bodytext, error)

class Permalink(Handler):
    def get(self, post_id):
        s = Post.get_by_id(int(post_id))
        self.render('blogpost.html', posts=[s])

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


def make_salt():
    return "".join(random.choice(letters) for a in range(5))

def make_pw_hash(name, pw, salt=None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return "%s|%s" % (h, salt)

def valid_pw(name, pw, h):
    salt = h.split('|')[1]
    return h == make_pw_hash(name, pw, salt)
#    return h == make_pw_hash(name, pw, h[-5:])

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

app = webapp2.WSGIApplication([
                                ('/',                MainPage), 
                                ('/thanks',          ThanksHandler), 
                                ('/form',            FormHandler), 
                                ('/rot13',           RotHandler), 
                                ('/blog/signup',     SignupHandler),
                                ('/welcome',         Welcome),                               
                                ('/fizz',            FizzHandler), 
                                ('/ascii',           AsciiHandler), 
                                ('/blog',            BlogHandler),
                                ('/blog/(\d+)',      Permalink),
                                ('/cookie',          CookieCount),
                                ('/blog/newpost',    NewBlogPost)],
                        debug=True)
    
