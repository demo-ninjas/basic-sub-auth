from ..data.request import Request
from . import Rule
from datetime import datetime

class DateCheck(Rule): 
    """
    Check if the current date matches the given date operator and value.
    This rule can be used to allow or deny requests based on the date.
    The date format is YYYY-MM-DD or YYYY-MM-DD HH:MM:SS.

    The date operator can be one of the following:
    - "==": Equal to
    - "!=": Not equal to
    - "<": Less than
    - "<=": Less than or equal to
    - ">": Greater than
    - ">=": Greater than or equal to

    """
    operator:str
    date:datetime

    def __init__(self, date: str, operator: str, allow:bool = True):
        self.operator = operator
        self.date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S" if " " in date else "%Y-%m-%d")
        super().__init__("DateCheck", allow)
    
    def matches(self, req:Request) -> bool:
        """
        Execute the rule.
        """
        now = datetime.now()
        if self.operator == "==":
            return now == self.date
        elif self.operator == "!=":
            return now != self.date
        elif self.operator == "<":
            return now < self.date
        elif self.operator == "<=":
            return now <= self.date
        elif self.operator == ">":
            return now > self.date
        elif self.operator == ">=":
            return now >= self.date
        else:
            raise ValueError(f"Invalid operator: {self.operator}")