
from re import Pattern, compile
from .rule import Rule
from ..data.request import Request

class HeaderCheck(Rule):
    """
    Check if a header is present in the request, and if it matches a given value.
    This rule can be used to allow or deny requests based on the presence and value of a header.
    The query value can be a wildcard for entire query values, e.g. *, abc*, *abc
    The query value can be a regex, by wrapping the query value in "regex()", e.g. regex(abc.*)
    """

    header_name:str
    header_values:list[str]
    header_regexes:list[Pattern]

    def __init__(self, name: str, values:list[str], allow:bool = True):
        self.header_name = name
        self.header_values = []
        self.header_regexes = []
        for value in values:
            if value.startswith("regex(") and value.endswith(")"):
                self.header_regexes.append(compile(value[6:-1]))
            else:
                self.header_values.append(value)
        super().__init__("QueryCheck", allow)

        
    def matches(self, req:Request) -> bool:
        req_header_val = req.header(self.header_name)
        if not req_header_val:
            return False
        for header_value in self.header_values:
            if req_header_val == header_value:
                return True
            
            if header_value == '*': # Any value match
                return True
            
            if '*' in header_value:
                if header_value.startswith('*'):
                    if req_header_val.endswith(header_value[1:]):
                        return True
                elif header_value.endswith('*'):
                    if req_header_val.startswith(header_value[:-1]):
                        return True
                else:
                    arr = header_value.split('*')   ## We assume only one wildcard in this case
                    if len(arr) != 2:
                        return False  # Unsupported wildcard expression
                    return req_header_val.startswith(arr[0]) and req_header_val.endswith(arr[1])
                    
        for header_regex in self.header_regexes:
            if header_regex.match(req_header_val):
                return True
        return False
    