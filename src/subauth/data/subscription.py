from datetime import datetime

from .request import Request
from ..rules import Rule, create_rule


class Subscription:
    id:str
    name:str
    description:str
    expiry:int
    rules:list[Rule]
    is_entra_user:bool = False
    entra_username:str = None
    entra_user_claims:dict = None

    def __init__(self, data:dict):
        self.id = data.get("id", None)
        if not self.id:
            raise ValueError("Subscription ID is required")
        self.name = data.get("name", None)
        if not self.name:
            raise ValueError("Subscription name is required")
        self.description = data.get("description", None)
        expiry_val = data.get("expiry", None)
        if expiry_val is not None and isinstance(expiry_val, str):
            try:
                expiry_date = datetime.strptime(expiry_val, '%Y-%m-%d')
                self.expiry = int(expiry_date.timestamp())
            except ValueError:
                raise ValueError("Invalid expiry date format, should be YYYY-MM-DD")
        elif isinstance(expiry_val, int):
            self.expiry = expiry_val
        else:
            raise ValueError("Invalid expiry date format, should be either a YYYY-MM-DD or timestamp")
        
        self.is_entra_user = data.get("is_entra_user", False)
        self.entra_username = data.get("entra_username", None)
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
        if self.expiry == -1:       ## -1 == Never Expire
            return False
        if self.expiry == -2:       ## -2 == Always Expire (technically, this isn't needed, as the below will always be true if this is negative, but it's here for clarity)
            return True
        
        return datetime.now().timestamp() > self.expiry

    def expiry_date(self) -> str:
        """
        Get the expiry date of the subscription.
        """
        if self.expiry == -1:
            return "Never"
        return datetime.fromtimestamp(self.expiry).strftime('%Y-%m-%d %H:%M:%S')
    
    def is_allowed(self, req:Request) -> tuple[bool, str]:
        if self.is_expired():
            return False, "Subscription has expired"
        
        if self.rules is None or len(self.rules) == 0:
            return False, "Subscription has no rules"    ## Not allowed to have a sub with no rules defined
        
        for rule in self.rules:
            matches = rule.matches(req)
            if rule.allow and not matches:
                return False, f"Request does not match ALLOW rule {rule.name}"
            elif not rule.allow and matches:
                return False, f"Request matches DENY rule {rule.name}"
            
        # If all allowed rules are matched, and no denied rules are matched, return True
        return True, "OK"
            
            
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
