import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from subauth.rules import PathCheck
from subauth.data import Request

class TestPathRule(unittest.TestCase):
    def setUp(self):
        self.rule = PathCheck(["/app", "/api/*", "/foo/*/check", "*.js", "regex(/.*\\.html$)"])
        self.request = Request("GET", "example.com", "/test", {})

    def test_match_exact(self):
        self.request.urlpath = "/app"
        self.assertTrue(self.rule.matches(self.request))
        self.request.urlpath = "/app?hello=world"
        self.assertTrue(self.rule.matches(self.request))
    def test_match_wildcard(self):
        self.request.urlpath = "/api/v1/users"
        self.assertTrue(self.rule.matches(self.request))
        self.request.urlpath = "/api/v1/users/?hello=world"
        self.assertTrue(self.rule.matches(self.request))
        self.request.urlpath = "/app/test.js"
        self.assertTrue(self.rule.matches(self.request))
    def test_match_regex(self):
        self.request.urlpath = "/test.html"
        self.assertTrue(self.rule.matches(self.request))
        self.request.urlpath = "/test/test.html"
        self.assertTrue(self.rule.matches(self.request))
        self.request.urlpath = "/test/test.html?hello=world"
        self.assertTrue(self.rule.matches(self.request))
    def test_match_wildcard_in_midddle(self):
        self.request.urlpath = "/foo/test/check"
        self.assertTrue(self.rule.matches(self.request))

    def test_no_match_exact(self):
        self.request.urlpath = "/bar"
        self.assertFalse(self.rule.matches(self.request))
    def test_no_match_wildcard(self):
        self.request.urlpath = "/apix/v1/"
        self.assertFalse(self.rule.matches(self.request))
        self.request.urlpath = "/api"
        self.assertFalse(self.rule.matches(self.request))
    def test_no_match_regex(self):
        self.request.urlpath = "/test.htmlx"
        self.assertFalse(self.rule.matches(self.request))
        self.request.urlpath = "/test/test.htmlx"
        self.assertFalse(self.rule.matches(self.request))
        self.request.urlpath = "/test/test.htmlx?hello=world"
        self.assertFalse(self.rule.matches(self.request))
    def test_no_match_wildcard_in_midddle(self):
        self.request.urlpath = "/foo/test/dude/check"
        self.assertFalse(self.rule.matches(self.request))
