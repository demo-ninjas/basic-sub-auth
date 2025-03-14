import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from subauth.rules import HostCheck
from subauth.data import Request

class TestHostRule(unittest.TestCase):
    def setUp(self):
        self.rule = HostCheck(["foo.org", "*.example.com", "app.*.bar.com", "regex((.+\\.)?example[\\d]\\.com)"])
        self.request = Request("GET", "example.com", "/test", {})

    def test_match_exact(self):
        self.request.host = "foo.org"
        self.assertTrue(self.rule.matches(self.request))
    def test_match_wildcard(self):
        self.request.host = "test.example.com"
        self.assertTrue(self.rule.matches(self.request))
        self.request.host = "app.test.example.com"
        self.assertTrue(self.rule.matches(self.request))
    def test_match_regex(self):
        self.request.host = "example1.com"
        self.assertTrue(self.rule.matches(self.request))
        self.request.host = "test.example2.com"
        self.assertTrue(self.rule.matches(self.request))
    def test_match_wildcard_in_midddle(self):
        self.request.host = "app.test.bar.com"
        self.assertTrue(self.rule.matches(self.request))

    def test_no_match_exact(self):
        self.request.host = "bar.org"
        self.assertFalse(self.rule.matches(self.request))
    def test_no_match_wildcard(self):
        self.request.host = "app.x.test.bar.com"
        self.assertFalse(self.rule.matches(self.request))
    def test_no_match_regex(self):
        self.request.host = "examplex.com"
        self.assertFalse(self.rule.matches(self.request))
        self.request.host = "test.examplex.com"
        self.assertFalse(self.rule.matches(self.request))
        self.request.host = "test.example12.com"
        self.assertFalse(self.rule.matches(self.request))
