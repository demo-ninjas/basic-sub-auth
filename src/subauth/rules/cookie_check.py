from re import Pattern, compile
from .rule import Rule
from ..data.request import Request

class CookieCheck(Rule):
    """
    Check if a cookie is present in the request, and if it matches a given value.
    This rule can be used to allow or deny requests based on the presence and value of a cookie.
    The cookie value can be a wildcard for entire cookie values, e.g. *, abc*, *abc
    The cookie value can be a regex, by wrapping the cookie value in "regex()", e.g. regex(abc.*)
    """
    cookie_name:str
    cookie_values:list[str]
    cookie_regexes:list[Pattern]


    def __init__(self, name: str, values:list[str], allow:bool = True):
        self.cookie_name = name
        self.cookie_values = []
        self.cookie_regexes = []
        for value in values:
            if value.startswith("regex(") and value.endswith(")"):
                self.cookie_regexes.append(compile(value[6:-1]))
            else:
                self.cookie_values.append(value)
        super().__init__("CookieCheck", allow)
    
    def matches(self, req:Request) -> bool:
        req_cookie_val = req.cookie(self.cookie_name)
        if not req_cookie_val:
            return False
        
        
        for cookie_value in self.cookie_values:
            if req_cookie_val == cookie_value:
                return True
            
            if '*' in cookie_value:
                if cookie_value.startswith('*'):
                    if req_cookie_val.endswith(cookie_value[1:]):
                        return True
                elif cookie_value.endswith('*'):
                    if req_cookie_val.startswith(cookie_value[:-1]):
                        return True
                else:
                    arr = cookie_value.split('*')   ## We assume only one wildcard in this case
                    if len(arr) != 2:
                        return False  # Unsupported wildcard expression
                    return req_cookie_val.startswith(arr[0]) and req_cookie_val.endswith(arr[1])

        
        for cookie_regex in self.cookie_regexes:
            if cookie_regex.match(req_cookie_val):
                return True
            
        return False

