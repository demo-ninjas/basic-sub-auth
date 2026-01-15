from azurefunctions.extensions.http.fastapi import Request as FastApiRequest, Response as FastApiResponse

from .data import Subscription, Request
from .sub_factory import get_subscription

__GLOBAL_TOKEN_KEYS = None

def fastapi_req_to_request(req: FastApiRequest, override_path:str = None, disguised_hosts:bool = True) -> Request:
    """
    Convert an Azure Function request to a Request object.
    """
    if type(req) is Request:
        return req
    

    host = None
    if disguised_hosts:
        host = req.headers.get('x-host', None)
        if not host:
            host = req.headers.get('disguised-host', None)
    if not host:
        host = req.headers.get('Host', None)

    if not host:
        raise ValueError("Host header not found in request")
    
    path = override_path if override_path else req.url.path
    if path is None:
        path = req.url
    if not path:
        raise ValueError("Path not found in request")
    if path.startswith("http://") or path.startswith("https://"):
        path = path[path.find("/", 8):]

    headers = req.headers
    if not headers:
        headers = {}
    method = req.method
    if not method:
        method = "GET"
    query = req.query_params

    client_ip = None
    if 'x-client-ip' in headers and headers['x-client-ip'] != "ignore":
        client_ip = headers['x-client-ip']

    if client_ip is None and 'x-forwarded-for' in headers and headers['x-forwarded-for'] != "ignore":
        forwarded_ips = headers['x-forwarded-for']
        client_ip = forwarded_ips.split(",")[0].strip()
    
    if client_ip is None:
        client_ip = req.client.host if req.client else None

    # Create a Request object
    request = Request(method, host, path, headers, query, client_ip=client_ip)
    return request
    
def get_sub_from_function_req(req: FastApiRequest) -> Subscription:
    """
    Get a subscription for the given request.
    """
    request = fastapi_req_to_request(req)
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


def validate_function_request(req: FastApiRequest, override_path:str = None, redirect_on_fail:bool = False, default_fail_status:int = 401, redirect_url:str = None, allow_cors:bool = True, include_reason:bool = True, allow_disguised_host:bool = True) -> tuple[bool, Subscription, FastApiResponse]:
    """
    Validate the request
    """
    if req is None:
        return False, None, FastApiResponse("Invalid Request", status_code=400)
    
    ## Accept CORS preflight requests
    if allow_cors and req.method == "OPTIONS":
        response = FastApiResponse("OK", status_code=200)
        response.headers["Access-Control-Allow-Origin"] = req.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization, Subscription, X-Subscription"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"
        return True, None, response

    # Check for the subscription
    sub = get_sub_from_function_req(req)
    reason = None
    if sub is not None:
        # Check if the subscription is allowed to access the resource
        request = fastapi_req_to_request(req, override_path, allow_disguised_host)
        allowed, reason = sub.is_allowed(request)
        if allowed:
            # Check if the request has the subscription in the cookie
            if request.cookie("subscription") is None and sub.store_sub_in_browser():
                # Set the subscription in the cookie
                response = FastApiResponse("ADD_THESE_HEADERS_TO_RESPONSE", status_code=0)
                response.headers["Set-Cookie"] = f"subscription={sub.id}; Path=/; HttpOnly; SameSite=None; Secure"
                return True, sub, response
            return True, sub, None

    ## Subscription is not allowed to access the resource
    if redirect_on_fail:
        # Redirect to the auth URL (if entra is enabled)
        import os
        if os.environ.get("ENTRA_AUTHORITY") is None:
            # No entra authority, so we can't redirect
            response = FastApiResponse("Not Allowed", status_code=default_fail_status)
            if reason is not None and include_reason:
                response.headers["x-reason"] = reason
            return False, sub, response
        
        auth_url = generate_entra_auth_url(req, redirect_uri=redirect_url)
        response = FastApiResponse("Redirecting...", status_code=302)
        response.headers["Location"] = auth_url
        if reason is not None and include_reason:
            response.headers["x-reason"] = reason
        return False, sub, response
    else:
        response = FastApiResponse("Not Allowed", status_code=default_fail_status)
        if reason is not None and include_reason:
            response.headers["x-reason"] = reason
        return False, sub, response

    
def get_entra_user_for_request(req: FastApiRequest) -> dict[str, any]:
    global __GLOBAL_TOKEN_KEYS
    from jose import jwt
    import os

    ## Check that ENTRA_AUTHORITY is set
    if os.environ.get("ENTRA_AUTHORITY") is None:
        return None
    if os.environ.get("ENTRA_CLIENT_ID") is None:
        return None

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
    
    request = fastapi_req_to_request(req)

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



def generate_entra_auth_url(req: FastApiRequest, redirect_uri:str = None) -> str:
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


    url = redirect_uri
    if url is None or len(url) == 0:
        url = req.url.path
        if req.url.query and req.url.query != "":
            if req.url.query.startswith("?"):
                url += req.url.query
            else:
                url += "?" + req.url.query

    if '$host' in url:
        host =  req.headers.get("x-host", req.headers.get('disguised-host', req.headers.get('Host', "not-set")))
        url = url.replace("$host", host)
    
    # Use the original path if it's set
    if req.headers.get("x-original-path", None) is not None:
        url = req.headers.get("x-original-path", None)
    elif os.environ.get("ENTRA_STATE_STRIP_API_APP_PATH", "true").lower() == "true":
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


def handle_entra_auth_callback(req: FastApiRequest, default_redirect_url:str = None) -> FastApiResponse:
    import os
    import base64
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

    app = msal.ClientApplication(
        app_name=os.environ.get("ENTRA_APP_NAME"),
        client_id=os.environ.get("ENTRA_CLIENT_ID"),
        client_credential=os.environ.get("ENTRA_CLIENT_SECRET"),
        authority=os.environ.get("ENTRA_AUTHORITY")
        )


    request = fastapi_req_to_request(req)
    code = request.query_param("code")
    if code is None or len(code) == 0:
        code  = request.header("code")
    if code is None or len(code) == 0:
        return FastApiResponse(
            content="Bad Request",
            status_code=400
        )
    

    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=_get_auth_scopes(),
        redirect_uri=_get_auth_redirect_url(req),
    )


    if "error" in result:
        print("Error acquiring token: ", result.get("error"), result.get("error_description"))
        return FastApiResponse(
            content="Not Allowed",
            status_code=401
        )
    
    
    id_token = result.get("id_token", None)
    if id_token is None:
        return FastApiResponse(
            content="Not Allowed",
            status_code=401
        )


    send_to_url = request.query_param("state")
    if send_to_url is None or len(send_to_url) == 0:
        send_to_url = request.header("state")
    if send_to_url is None or len(send_to_url) == 0:
        send_to_url = request.query_param("session_state")
    if send_to_url is None or len(send_to_url) == 0:
        send_to_url = request.header("session_state")
    
    if send_to_url is not None:
        send_to_url = base64.urlsafe_b64decode((send_to_url+"==").encode("utf-8")).decode("utf-8")

    if send_to_url is None or send_to_url == '/' or len(send_to_url) == 0:
        send_to_url = default_redirect_url if default_redirect_url is not None else os.environ.get("DEFAULT_REDIRECT_URL", "/")

    max_age = int(os.environ.get("ENTRA_ID_TOKEN_MAX_AGE_SECONDS", "28800")) # 8 hours default
    same_site = os.environ.get("ENTRA_ID_TOKEN_SAME_SITE", "None")
    is_secure = f'Secure; SameSite={same_site};' if req.url.scheme.startswith("https") else ''
    headers = {
        "Set-Cookie": f"Authorization={id_token}; {is_secure} Path=/; Max-Age={max_age};", # HttpOnly;
        "Location": send_to_url
    }
    return FastApiResponse(
        status_code=302,
        headers=headers
    )

def _get_auth_scopes() -> list[str]:
    import os
    return os.environ.get("ENTRA_SCOPES", "User.Read").split(",")

def _get_auth_redirect_url(req:FastApiRequest) -> str:
    import os
    
    redirect_url = os.environ.get("ENTRA_REDIRECT_URI")
    if redirect_url is None or len(redirect_url) == 0:
        redirect_url = req.url.scheme + "://" + req.url.hostname + ":" + str(req.url.port) + "/api/auth-callback"
    if '$host' in redirect_url:
        host =  req.headers.get("x-host", req.headers.get('disguised-host', req.headers.get('Host', "not-set")))
        redirect_url = redirect_url.replace("$host", host)
    return redirect_url

