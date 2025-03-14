from re import Pattern, compile

from .rule import Rule
from ..data.request import Request

class HostCheck(Rule):
    """
    Rule to allow/deny a subscription access to requests for a particular host(domain).

    This rule is used to allow/deny access to a subscription based on the host of the request.
    The rule matches the host of the request against a list of allowed/denied hosts.

    The host can be a wildcard for entire domain segments, e.g. *.example.com, app.*.example.com, example.com.*
    However, the wildcard cannot be used in the middle of a domain segment, e.g. app.ex*mple.com is not allowed.
    The host can be a regex, by wrapping the host in "regex()", e.g. regex(.*\.example\.com)
    """
    hosts: list[str]
    host_regexes: list[Pattern]

    def __init__(self, hosts: list[str], allow: bool = True):
        self.hosts = []
        self.host_regexes = []
        for host in hosts:
            if host.startswith("regex(") and host.endswith(")"):
                self.host_regexes.append(compile(host[6:-1]))
            else:
                self.hosts.append(host)

        super().__init__("HostCheck", allow)

    def matches(self, req:Request) -> bool:
        """
        Execute the rule.
        """
        if not req.host:
            return False
        
        lower_req_host = req.host.lower()
        for host in self.hosts:
            if lower_req_host == host.lower():
                return True
        
            if '*' in host:
                if host.startswith('*'):
                    if lower_req_host.endswith(host[1:]):
                        return True
                elif host.endswith('*'):
                    if lower_req_host.startswith(host[:-1]):
                        return True
                else:
                    arr = host.split('.')
                    req_arr = lower_req_host.split('.')
                    ismatch = True
                    for i in range(len(arr)):
                        if arr[i] == '*' or arr[i] == req_arr[i]:
                            continue
                        ismatch = False
                        break
                    if ismatch:
                        return True
        
        for host_regex in self.host_regexes:
            if host_regex.match(lower_req_host):
                return True
        
        return False