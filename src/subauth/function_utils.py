import azure.functions as func
from .data import Subscription, Request
from .sub_factory import get_subscription

__GLOBAL_TOKEN_KEYS = None

def function_req_to_request(req: func.HttpRequest) -> Request:
    """
    Convert an Azure Function request to a Request object.
    """
    host = req.headers.get('Host', None)
    if not host:
        raise ValueError("Host header not found in request")
    path = req.url
    if not path:
        raise ValueError("Path not found in request")
    headers = req.headers
    if not headers:
        headers = {}
    method = req.method
    if not method:
        method = "GET"
    query = req.params
    
    # Create a Request object
    request = Request(method, host, path, headers, query)
    return request
    
def get_sub_from_function_req(req: func.HttpRequest) -> Subscription:
    """
    Get a subscription for the given request.
    """
    request = function_req_to_request(req)
    sub_id = request.header("subscription")
    if not sub_id:
        sub_id = request.query_param("subscription")
    if not sub_id:
        sub_id = request.cookie("subscription")
    if not sub_id:
        sub_id = request.cookie("subscription")
    if not sub_id:
        sub_id = request.header("x-subscription")
    if not sub_id:
        sub_id = request.cookie("x-subscription")

    subscription = None
    if sub_id:
        if sub_id.startswith("Bearer "):
            sub_id = sub_id[7:]
        if sub_id.startswith("BEARER "):
            sub_id = sub_id[7:]
        subscription = get_subscription(sub_id, False)

    if not subscription:
        user = get_entra_user_for_request(req)
        if user is not None:
            sub_id = user.get("preferred_username", user.get("upn", None))
            if sub_id is not None:
                sub_id = sub_id.strip()
                subscription = get_subscription(sub_id, True)
                if subscription is not None:
                    subscription.is_entra_user = True
                    subscription.entra_user_claims = user
    
    return subscription


def validate_function_request(req: func.HttpRequest, redirect_on_fail:bool = False, default_fail_status:int = 401, redirect_url:str = None, allow_cors:bool = True) -> tuple[bool, Subscription, func.HttpResponse]:
    """
    Validate the request
    """
    if req is None:
        return False, None, func.HttpResponse("Invalid Request", status_code=400)
    
    ## Accept CORS preflight requests
    if allow_cors and req.method == "OPTIONS":
        response = func.HttpResponse("OK", status_code=200)
        response.headers["Access-Control-Allow-Origin"] = req.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization, Subscription, X-Subscription"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"
        return True, None, response

    # Check for the subscription
    sub = get_sub_from_function_req(req)
    if sub is not None:
        # Check if the subscription is allowed to access the resource
        request = function_req_to_request(req)
        if sub.is_allowed(request):
            # Check if the request has the subscription in the cookie
            if request.cookie("subscription") is None:
                # Set the subscription in the cookie
                response = func.HttpResponse("ADD_THESE_HEADERS_TO_RESPONSE", status_code=0)
                response.headers["Set-Cookie"] = f"subscription={sub.id}; Path=/; HttpOnly; SameSite=None; Secure"
                return True, sub, response
            return True, sub, None

    ## Subscription is not allowed to access the resource
    if redirect_on_fail:
        # Redirect to the auth URL
        auth_url = generate_entra_auth_url(req, redirect_uri=redirect_url)
        response = func.HttpResponse("Redirecting...", status_code=302)
        response.headers["Location"] = auth_url
        return False, sub, response
    else:
        return False, sub, func.HttpResponse("Not Allowed", status_code=default_fail_status)

    
def get_entra_user_for_request(req: func.HttpRequest) -> dict[str, any]:
    global __GLOBAL_TOKEN_KEYS
    from jose import jwt
    import os

    ## Check that ENTRA_AUTHORITY is set
    if os.environ.get("ENTRA_AUTHORITY") is None:
        raise RuntimeError("ENTRA_AUTHORITY is not set in the environment variables")
    if os.environ.get("ENTRA_CLIENT_ID") is None:
        raise RuntimeError("ENTRA_CLIENT_ID is not set in the environment variables")

    if __GLOBAL_TOKEN_KEYS is None:
        import requests

        ## Go and retrieve the JWKS Keys
        try:
            resp = requests.get(os.environ.get("ENTRA_AUTHORITY") + "/discovery/v2.0/keys")
            jwks = resp.json()
            keys = jwks.get("keys", [])
            key_map = {}
            for key in keys:
                key_map[key["kid"]] = key
            __GLOBAL_TOKEN_KEYS = key_map
        except Exception:
            raise RuntimeError("Unable to load the Keys for validating the auth token")
        

    if __GLOBAL_TOKEN_KEYS is None:
        raise RuntimeError("Unable to retrieve the Keys to validate the auth token")
    
    request = function_req_to_request(req)

    id_token = None
    # Grab token from Cookie or Header
    if id_token is None or len(id_token) == 0:
        id_token = request.cookie("authorization")
    if id_token is None or len(id_token) == 0:
        id_token = request.header("authorization")
    if id_token is None or len(id_token) == 0:
        id_token = request.query_param("authorization")
    if id_token is None or len(id_token) == 0:
        id_token = request.header("token")
    if id_token is None or len(id_token) == 0:
        id_token = request.cookie("token")
    if id_token is None or len(id_token) == 0:
        id_token = request.query_param("token")
    
    if id_token is None: 
        return None
    
    if id_token.startswith("BEARER "):
        id_token = id_token.replace("BEARER ", "")
    if id_token.startswith("Bearer "):
        id_token = id_token.replace("Bearer ", "")
    
    try:
        unverified_header = jwt.get_unverified_header(id_token)
        rsa_key = __GLOBAL_TOKEN_KEYS.get(unverified_header["kid"], None)
        if rsa_key is None:
            return None

        payload = jwt.decode(
            id_token,
            rsa_key,
            algorithms=["RS256"],
            audience=os.environ.get("ENTRA_CLIENT_ID"),
            issuer=os.environ.get("ENTRA_AUTHORITY") + "/v2.0"
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTClaimsError:
        return None
    except Exception:
        return None



def generate_entra_auth_url(req: func.HttpRequest, redirect_uri:str = None) -> str:
    import base64
    import os
    import msal
    
    ## Check that ENTRA_AUTHORITY is set
    if os.environ.get("ENTRA_AUTHORITY") is None:
        raise RuntimeError("ENTRA_AUTHORITY is not set in the environment variables")
    if os.environ.get("ENTRA_CLIENT_ID") is None:
        raise RuntimeError("ENTRA_CLIENT_ID is not set in the environment variables")
    if os.environ.get("ENTRA_CLIENT_SECRET") is None:
        raise RuntimeError("ENTRA_CLIENT_SECRET is not set in the environment variables")
    if os.environ.get("ENTRA_APP_NAME") is None:
        raise RuntimeError("ENTRA_APP_NAME is not set in the environment variables")
    if os.environ.get("ENTRA_SCOPES") is None:
        raise RuntimeError("ENTRA_SCOPES is not set in the environment variables")

    app = msal.ClientApplication(
        app_name=os.environ.get("ENTRA_APP_NAME"),
        client_id=os.environ.get("ENTRA_CLIENT_ID"),
        client_credential=os.environ.get("ENTRA_CLIENT_SECRET"),
        authority=os.environ.get("ENTRA_AUTHORITY")
    )


    ## Get the path portion of the req.url
    colon_idx = req.url.find(":")
    if colon_idx == -1: colon_idx = -3

    url = redirect_uri
    if url is None or len(url) == 0:
        url = req.url[req.url.find('/', colon_idx + 3):]

    if '$host' in url:
        host =  req.headers.get("x-host", req.headers.get('disguised-host', req.headers.get('Host', "not-set")))
        url = url.replace("$host", host)
    
    if os.environ.get("ENTRA_STATE_STRIP_API_APP_PATH", "true").lower() == "true":
        ## Strip the /api/app/ path from the URL (this is to handle the internal mapping happing on the edge proxy)
        if url.startswith("/api/app/"): url = url[8:]
    
    path_prefix = os.environ.get("ENTRA_STATE_REDIRECT_PATH_PREFIX", None)
    if path_prefix is not None:
        if not path_prefix.endswith("/"): path_prefix += "/"
        if url.startswith("/"): url = url[1:]
        if url.startswith("api/"): url = url[4:] ## Remove the api/ prefix if it's there
        url = path_prefix + url

    state = base64.urlsafe_b64encode(url.encode()).decode()
    auth_url = app.get_authorization_request_url(
        scopes=_get_auth_scopes(),
        redirect_uri=_get_auth_redirect_url(req),
        state=state
        )
    
    return auth_url

def _get_auth_scopes() -> list[str]:
    import os
    return os.environ.get("ENTRA_SCOPES", "User.Read").split(",")

def _get_auth_redirect_url(req:func.HttpRequest) -> str:
    import os
    
    redirect_url = os.environ.get("ENTRA_REDIRECT_URI")
    if redirect_url is None or len(redirect_url) == 0:
        redirect_url = req.url[:req.url.find("/", 8)] + "/api/auth-callback"
    if '$host' in redirect_url:
        host =  req.headers.get("x-host", req.headers.get('disguised-host', req.headers.get('Host', "not-set")))
        redirect_url = redirect_url.replace("$host", host)
    return redirect_url

