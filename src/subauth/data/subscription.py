from datetime import datetime

from .request import Request
from ..rules import Rule, create_rule


class Subscription:
    id:str
    name:str
    description:str
    expiry:int
    rules:list[Rule]

    def __init__(self, data:dict):
        self.id = data.get("id", None)
        if not self.id:
            raise ValueError("Subscription ID is required")
        self.name = data.get("name", None)
        if not self.name:
            raise ValueError("Subscription name is required")
        self.description = data.get("description", None)
        self.expiry = data.get("expiry", -1)
        self.rules = []
        for rule_def in data.get("rules", []):
            rule_name = rule_def.get("name", None)
            if not rule_name:
                raise ValueError("Invalid rule definition: name is required")
            rule_type = rule_def.get("type", None)
            if not rule_type:
                raise ValueError("Invalid rule definition: type is required")
            rule_allow = rule_def.get("allow", True)
            rule = create_rule(rule_type, rule_name, rule_allow, rule_def)
            if not rule:
                raise ValueError(f"Invalid rule definition: {rule_def}")
            self.rules.append(rule)
        if not self.rules:
            raise ValueError("At least one rule is required")

    def is_expired(self) -> bool:
        """
        Check if the subscription is expired.
        """
        if self.expiry == -1:
            return False
        return datetime.now().timestamp() > self.expiry

    def expiry_date(self) -> str:
        """
        Get the expiry date of the subscription.
        """
        if self.expiry == -1:
            return "Never"
        return datetime.fromtimestamp(self.expiry).strftime('%Y-%m-%d %H:%M:%S')
    
    def is_allowed(self, req:Request) -> bool:
        if self.is_expired():
            return False
        
        if self.rules is None or len(self.rules) == 0:
            return False    ## Not allowed to have a sub with no rules defined
        
        for rule in self.rules:
            matches = rule.matches(req)
            if rule.allow and not matches:
                return False
            elif not rule.allow and matches:
                return False
            
        # If all allowed rules are matched, and no denied rules are matched, return True
        return True
            
            
    def __repr__(self):
        return f"Subscription(id={self.id}, name={self.name}, description={self.description}, expiry={self.expiry_date()}, rules={self.rules})"
    def __str__(self):
        return f"Subscription(id={self.id}, name={self.name}, description={self.description}, expiry={self.expiry_date()}, rules={self.rules})"
    
    def __eq__(self, other):
        if not isinstance(other, Subscription):
            return False
        return self.id == other.id
    
    def __ne__(self, other):
        return not self.__eq__(other)
