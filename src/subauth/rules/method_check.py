
from .rule import Rule
from ..data.request import Request

class MethodCheck(Rule):
    """"
    Check if the request method matches a given method.
    This rule can be used to allow or deny requests based on their method.
    Methods must be specified in full, no wildcards or regexes are allowed. eg. GET, POST, PUT, DELETE
    """
    methods: list[str]

    def __init__(self, methods: list[str], allow: bool = True):
        self.methods = [ method.upper() for method in methods ]
        super().__init__("MethodCheck", allow)

    def matches(self, req: Request) -> bool:
        req_method = req.method
        if not req_method:
            return False
        
        req_method = req_method.upper()
        for method in self.methods:
            if req_method == method:
                return True