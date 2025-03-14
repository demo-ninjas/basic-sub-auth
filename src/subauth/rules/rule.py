from abc import abstractmethod, ABC
from ..data.request import Request

class Rule(ABC):
    name:str
    allow:bool  ## Otherwise deny
    

    def __init__(self, name: str, allow:bool = True):
        self.name = name
        self.allow = allow

    @abstractmethod
    def matches(self, req:Request) -> bool:
        pass

class AllowAll(Rule):
    """
    Allow all requests.
    """
    def __init__(self):
        super().__init__("AllowAll", True)
    
    def matches(self, req:Request) -> bool:
        return True
    
class DenyAll(Rule):
    """
    Deny all requests.
    """
    def __init__(self):
        super().__init__("DenyAll", False)
    
    def matches(self, req:Request) -> bool:
        return True