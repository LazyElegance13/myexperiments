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
import webapp2

form="""
<h2>Enter some text to ROT13:</h2>
<form method="post">
    <textarea name="text" style="height: 100px; width: 400px">%(text)s</textarea>
    <br>
    <input type="submit">
</form>
"""
def escape_html(s):
# Steve's second solution
    import cgi
    return cgi.escape(s, quote = True)

def rot_13(s):
    if s:
        result = ""
        for c in s:
            if c >= 'a' and c <= 'z':
                result += chr((ord(c) - ord('a') + 13)%26 - 1 + ord('a'))
            elif c >= 'A' and c <= 'Z':
                result += chr((ord(c) - ord('A') + 13)%26 - 1 + ord('A'))
            else:
                result += c
        return result

class MainHandler(webapp2.RequestHandler):
    def write_form(self, text=""):
        self.response.out.write(form % {"text": escape_html(text)})

    def get(self):
        self.write_form()
        
    def post(self):
        text = rot_13(self.request.get('text'))
        self.write_form(text)

       
app = webapp2.WSGIApplication([
    ('/rot_13', MainHandler)], debug=True)
