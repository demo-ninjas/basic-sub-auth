

class Request: 
    method:str
    host:str
    urlpath:str
    headers:dict[str,str]
    query_params:dict[str,str]
    cookies:dict[str,str]
    client_ip:str

    def __init__(self, method:str, host:str, path:str, headers:dict[str,str] = {}, query_params:dict[str,str] = None, cookies:dict[str,str] = None, client_ip:str = None):
        self.method = method
        self.host = host
        self.urlpath = path
        self.headers = headers
        self.query_params = query_params
        self.cookies = cookies
        self.client_ip = client_ip

    def header(self, key:str) -> str:
        """
        Get the value of a header.
        """
        return self.headers.get(key, None)
    
    def path(self, exclude_query:bool=True) -> str:
        """
        Get the path of the request.
        """
        if exclude_query:
            return self.urlpath.split("?")[0]
        return self.urlpath

    def query_param(self, key:str) -> str:
        """
        Get the value of a query parameter.
        """
        
        if not self.query_params:
            ## We need to parse the query params from the URL
            self.query_params = {}
            if "?" in self.urlpath:
                query = self.urlpath.split("?")[1]
                if query:
                    for param in query.split("&"):
                        key, value = param.split("=")
                        self.query_params[key.lower()] = value
            else:
                self.query_params = {}
        
        ## Check if the key is in the query params
        low_key = key.lower()
        if low_key in self.query_params:
            return self.query_params[low_key]
        
        return None

    
    def cookie(self, key:str) -> str:
        """
        Get the value of a cookie.
        """
        if not self.cookies:
            ## We need to parse the cookies from the headers
            self.cookies = {}
            if "Cookie" in self.headers or "cookie" in self.headers:
                cookies = self.headers.get("Cookie", self.headers.get("cookie", None))
                if cookies:
                    for cookie in cookies.split(";"):
                        key, value = cookie.split("=")
                        self.cookies[key.lower()] = value
            else:
                self.cookies = {}

        ## Check if the key is in the cookies   
        low_key = key.lower()
        if low_key in self.cookies:
            return self.cookies[low_key]
        return None

    @property
    def url(self) -> str:
        """
        Get the full URL of the request.
        """
        scheme = "https"
        if "x-forwarded-proto" in self.headers:
            scheme = self.headers["x-forwarded-proto"]
        elif "X-Forwarded-Proto" in self.headers:
            scheme = self.headers["X-Forwarded-Proto"]
        elif self.host in ["localhost", "127.0.0.1"] or self.host.startswith("localhost:") or self.host.startswith("127.0.0.1:"):
            scheme = "http"
        return f"{scheme}://{self.host}{self.urlpath}"