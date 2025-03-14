from . import *

def create_rule(rule_type:str, rule_name:str, allow:bool, claims:dict[str,any]) -> Rule:
    """
    Get a rule by its name.
    """
    if rule_type == "cookie":
        vals = claims.get("values", claims.get("cookies", []))
        return CookieCheck(claims.get("name", rule_name), vals, allow)
    elif rule_type == "host":
        vals = claims.get("hosts", claims.get("values", []))
        allow_localhost = claims.get("allow_localhost", claims.get("allow_local", False))
        return HostCheck(vals, allow_localhost, allow)
    elif rule_type == "header":
        vals = claims.get("values", claims.get("headers", []))
        return HeaderCheck(claims.get("name", rule_name), vals, allow)
    elif rule_type == "query":
        vals = claims.get("values", claims.get("headers", []))
        return QueryCheck(claims.get("name", rule_name), vals, allow)
    elif rule_type == "path":
        vals = claims.get("values", claims.get("paths", []))
        return PathCheck(claims.get("name", rule_name), vals, allow)
    elif rule_type == "method":
        vals = claims.get("methods", claims.get("values", []))
        return MethodCheck(vals, allow)
    elif rule_type == "date":
        dt = claims.get("date", None)
        if not dt:
            raise ValueError("Date is required")
        op = claims.get("operator", None)
        if not op:
            raise ValueError("Operator is required")
        return DateCheck(dt, op, allow)
    elif rule_type == "allow-all":
        return AllowAll(allow)
    elif rule_type == "deny-all":
        return DenyAll(allow)
    else:
        raise ValueError(f"Invalid rule type: {rule_type}")