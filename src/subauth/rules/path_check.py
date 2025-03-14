
from re import Pattern, compile
from .rule import Rule
from ..data.request import Request

class PathCheck(Rule):
    """
    Check if the request path matches a given path.
    This rule can be used to allow or deny requests based on their path.
    The path can be a wildcard for entire path segments, e.g. /api/*, /app/*/v1, /app/v1/*
    The path can be a regex, by wrapping the path in "regex()", e.g. regex(\/api\/v1\/users\/\d+)
    """
    paths: list[str]
    path_regexes: list[Pattern]

    def __init__(self, paths: list[str], allow: bool = True):
        self.paths = []
        self.path_regexes = []
        for path in paths:
            if path.startswith("regex(") and path.endswith(")"):
                self.path_regexes.append(compile(path[6:-1]))
            else:
                self.paths.append(path)
        super().__init__("PathCheck", allow)

    def matches(self, req:Request) -> bool:
        """
        Execute the rule.
        """
        if not req.urlpath:
            return False    
        
        lower_req_path = req.path().lower()
        for path in self.paths:
            if lower_req_path == path.lower():
                return True
            
            if '*' in path:
                if path.startswith('*'):
                    if lower_req_path.endswith(path[1:]):
                        return True
                elif path.endswith('*'):
                    if lower_req_path.startswith(path[:-1]):
                        return True
                else:
                    arr = path.split('/')
                    req_arr = lower_req_path.split('/')
                    ismatch = True
                    for i in range(len(arr)):
                        if arr[i] == '*' or arr[i] == req_arr[i]:
                            continue
                        ismatch = False
                        break
                    if ismatch:
                        return True
        
        for path_regex in self.path_regexes:
            if path_regex.match(lower_req_path):
                return True
        
        return False