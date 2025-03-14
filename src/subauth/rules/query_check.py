
from re import Pattern, compile
from .rule import Rule
from ..data.request import Request

class QueryCheck(Rule):
    """
    Check if a query parameter is present in the request, and if it matches a given value.
    This rule can be used to allow or deny requests based on the presence and value of a query parameter.
    The query value can be a wildcard for entire query values, e.g. *, abc*, *abc
    The query value can be a regex, by wrapping the query value in "regex()", e.g. regex(abc.*)
    """

    query_param:str
    query_values:list[str]
    query_regexes:list[Pattern]

    def __init__(self, name: str, values:list[str], allow:bool = True):
        self.query_param = name
        self.query_values = []
        self.query_regexes = []
        for value in values:
            if value.startswith("regex(") and value.endswith(")"):
                self.query_regexes.append(compile(value[6:-1]))
            else:
                self.query_values.append(value)
        super().__init__("QueryCheck", allow)

        
    def matches(self, req:Request) -> bool:
        req_query_val = req.query_param(self.query_param)
        if not req_query_val:
            return False
        for query_value in self.query_values:
            if req_query_val == query_value:
                return True
            
            if query_value == '*': # Any value match
                return True

            if '*' in query_value:
                if query_value.startswith('*'):
                    if req_query_val.endswith(query_value[1:]):
                        return True
                elif query_value.endswith('*'):
                    if req_query_val.startswith(query_value[:-1]):
                        return True
                else:
                    arr = query_value.split('*')   ## We assume only one wildcard in this case
                    if len(arr) != 2:
                        return False  # Unsupported wildcard expression
                    return req_query_val.startswith(arr[0]) and req_query_val.endswith(arr[1])

        for query_regex in self.query_regexes:
            if query_regex.match(req_query_val):
                return True
        return False
    
