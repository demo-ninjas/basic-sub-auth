from ipaddress import ip_network, ip_address, IPv4Network
from .rule import Rule
from ..data.request import Request

class ClientIPCheck(Rule):
    """"
    Check if the the client IP address is in the allowed list (of CIDRs).
    This rule can be used to allow or deny requests based on their client ID address.    
    """
    allowed_cidrs: list[IPv4Network]

    def __init__(self, cidrs: list[str], allow: bool = True):
        self.allowed_cidrs = [ ip_network(cidr, strict=False) for cidr in cidrs]
        super().__init__("ClientIPCheck", allow)

    def matches(self, req: Request) -> bool:
        """
        Check if the client IP address is in the allowed list (of CIDRs).
        """
        if req.client_ip is None:
            return False
        
        client_ip = ip_address(req.client_ip)
        for cidr in self.allowed_cidrs:
            if client_ip in cidr:
                return True

        return False