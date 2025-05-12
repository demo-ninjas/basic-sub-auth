import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from subauth.rules import ClientIPCheck
from subauth.data import Request

class TestClientIPRule(unittest.TestCase):
    def setUp(self):
        self.rule = ClientIPCheck(["10.0.0.0/16", "172.16.1.0/24", "192.168.10.50/28", "201.202.203.204/32"])
        self.request = Request("GET", "example.com", "/test", {})

    def test_match_exact(self):
        self.request.client_ip = "201.202.203.204"
        self.assertTrue(self.rule.matches(self.request))
    
    def test_match_16(self):
        self.request.client_ip = "10.0.5.10"
        self.assertTrue(self.rule.matches(self.request))
        self.request.client_ip = "10.1.5.10"
        self.assertFalse(self.rule.matches(self.request))
        
    def test_match_24(self):
        self.request.client_ip = "172.16.1.50"
        self.assertTrue(self.rule.matches(self.request))
        self.request.client_ip = "172.16.2.50"
        self.assertFalse(self.rule.matches(self.request))
        
    def test_match_28(self):
        self.request.client_ip = "192.168.10.60"
        self.assertTrue(self.rule.matches(self.request))
        self.request.client_ip = "192.168.10.70"
        self.assertFalse(self.rule.matches(self.request))
        
    
    