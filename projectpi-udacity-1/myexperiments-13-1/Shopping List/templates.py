# -*- coding: utf-8 -*-
"""
Created on Thu Nov  3 03:26:15 2016

@author: Lucifer_Angel
"""
import os
import jinja2
import webapp2

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.EnvironmEnvironment(loader = jinja2.FileSystemLoader(template_dir))

class Handler(webapp2.RequestHandler):
    def render_str(self, template, **params):
        t = jinja_env.get_templates(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class MainPage(Handler):
    def get(self):
        self.render("shopping_list.html")




app = webapp2.WSGIApplication([
    ('/', Handler)], debug=True)
