from . import *

def create_rule(rule_type:str, rule_name:str, allow:bool, claims:dict[str,any]) -> Rule:
    """
    Get a rule by its name.
    """
    if rule_type == "cookie":
        vals = claims.get("values", claims.get("cookies", []))
        cookie_name = claims.get("cookie", claims.get("cookie_name", rule_name))
        return CookieCheck(cookie_name, vals, allow)
    elif rule_type == "host":
        vals = claims.get("hosts", claims.get("values", []))
        allow_localhost = claims.get("allow_localhost", claims.get("allow_local", False))
        return HostCheck(vals, allow_localhost, allow)
    elif rule_type == "header":
        vals = claims.get("values", claims.get("header_vals", []))
        header_name = claims.get("header", claims.get("header_name", rule_name))
        return HeaderCheck(header_name, vals, allow)
    elif rule_type == "query":
        vals = claims.get("values", claims.get("query_vals", []))
        query_param = claims.get("param", claims.get("query", rule_name))
        return QueryCheck(query_param, vals, allow)
    elif rule_type == "path":
        vals = claims.get("values", claims.get("paths", []))
        return PathCheck(vals, allow)
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
        if op not in ["<", "<=", ">", ">=", "==", "!="]:
            if op == "lt" or op == "before":
                op = "<"
            elif op == "le" or op == "until":
                op = "<="
            elif op == "gt" or op == "after":
                op = ">"
            elif op == "ge" or op == "from":
                op = ">="
            elif op == "eq" or op == "equals" or op == "=":
                op = "=="
            elif op == "ne" or op == "not-equals" or op == "!":
                op = "!="
            else:
                raise ValueError(f"Invalid operator: {op}")
        return DateCheck(dt, op, allow)
    elif rule_type == "allow-all":
        return AllowAll(allow)
    elif rule_type == "deny-all":
        return DenyAll(allow)
    else:
        raise ValueError(f"Invalid rule type: {rule_type}")