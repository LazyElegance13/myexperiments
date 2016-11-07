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
import webapp2

home="""
<body="get">
    <h1>My Experiments</h1>
    <br>
    <input type="submit" label="form" value="Form">
    <br>
    <br>
    <input type="submit" label="rot13" value="ROT13">
    <br>
    <br>
    <input type="submit" label="Coming Soon" value="Coming Soon">
</body>
"""

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

rot="""
<h2>Enter some text to ROT13:</h2>
<form method="post">
    <textarea name="text" style="height: 100px; width: 400px">%(text)s</textarea>
    <br>
    <input type="submit">
</form>
"""
months = ['January', 'February', 'March', 'April', 
             'May', 'June', 'July', 'August', 'September', 
             'October', 'November', 'December']
month_abbvs = dict((m[:3].lower(), m) for m in months)

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
def escape_html(s):
# Steve's second solution
    import cgi
    return cgi.escape(s, quote = True)

def rot_13(s):
    if s:
        result = ""
        for c in s:
            if c >= 'a' and c <= 'z':
                result += chr((ord(c) - ord('a') + 13)%26 + ord('a'))
            elif c >= 'A' and c <= 'Z':
                result += chr((ord(c) - ord('A') + 13)%26 + ord('A'))
            else:
                result += c
        return result
# my solution:
#    rep_dict = {'>' : '&gt;', '<' : '&lt;', '"' : '&quot;', '&' : '&amp;'}    
#    result = ""
#    if s:
#        for char in s:
#            if char in rep_dict:
#                result += rep_dict[char]
#            else:
#                result += char
#    return result
# Steve's first solution:
#    for (i, o) in (('&', '&amp;'), 
#                   ('>' , '&gt;'), 
#                   ('<' , '&lt;'), 
#                   ('"','&quot;')):
#        s = s.replace(i,o)
#    return s 
           
class MainHandler(webapp2.RequestHandler):
    def write_form(self):
        self.response.out.write(home)
    def get(self):
        self.write_form()
        
    def post(self):
        value = self.request.get('value')
        
        if value == '1':
            self.redirect("form")
        elif value == '2':            
            self.redirect("rot13")
        else:            
            self.write_form()

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
#class TestHandler(webapp2.RequestHandler):
 #   def post(self):
        #self.response.headers['Content-Type'] = 'text/plain'
        #self.response.out.write(self.request)

  #      q = self.request.get("q")
   #     self.response.write(q)
class ThanksHandler(webapp2.RequestHandler):
    def get(self):
            self.response.write("That's a toltally valid day!")

class RotHandler(webapp2.RequestHandler):
    def write_form(self, text=""):
        self.response.out.write(rot % {"text": escape_html(text)})

    def get(self):
        self.write_form()
        
    def post(self):
        text = rot_13(self.request.get('text'))
        self.write_form(text)
                                        
       
app = webapp2.WSGIApplication([
    ('/', MainHandler), ('/thanks', ThanksHandler), ('/form', FormHandler), ('/rot13',RotHandler) ], debug=True)
