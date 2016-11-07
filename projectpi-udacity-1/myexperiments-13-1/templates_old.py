# -*- coding: utf-8 -*-
"""
Created on Thu Nov  3 06:37:40 2016

@author: Lucifer_Angel
"""
import webapp2

form_html="""
<form>
  <h2>Add a food</h2>
  <input type="text" name="food">
  %s
  <button>add</button>
</form>
"""

hidden_html = """
<input type="hidden" name="food" value="%s">
"""

item_html = "<li>%s</li>"

shopping_list_html="""
<br><br><br>
<h2>Shopping list</h2>
<ul>%s</ul>
"""


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

class MainPage(Handler):
    def get(self):
        output = form_html
        output_hidden = ""
        
        items = self.request.get_all('food')
        
        if items:
            output_items = ""
            for item in items:
                output_hidden += hidden_html % item
                output_items += item_html % item
            
            output_shopping = shopping_list_html % output_items
            output += output_shopping
        
        output = output % output_hidden
        self.write(output)


app = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)