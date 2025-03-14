from cachetools import TTLCache
from .data import Subscription
from .dataaccess import CosmosDBConnection

_SUBSCRIPTION_CACHE = TTLCache(maxsize=500, ttl=3600)  # 1 hour TTL
_ENTRA_UN_TO_ID_CACHE = TTLCache(maxsize=500, ttl=86400)  # 24 hours TTL
_COSMOS_DB_CONNECTION = None

def get_subscription(sub_id: str, entra_user:bool) -> Subscription:
    """
    Get a subscription from the cache or create a new one if it doesn't exist.
    """
    global _SUBSCRIPTION_CACHE
    global _ENTRA_UN_TO_ID_CACHE
    global _COSMOS_DB_CONNECTION
    lower_sub_id = sub_id.lower()
    if lower_sub_id in _SUBSCRIPTION_CACHE:
        return _SUBSCRIPTION_CACHE[lower_sub_id]
    
    if entra_user and lower_sub_id in _ENTRA_UN_TO_ID_CACHE:
        user_sub_id = _ENTRA_UN_TO_ID_CACHE[lower_sub_id]
        if user_sub_id in _SUBSCRIPTION_CACHE:
            return _SUBSCRIPTION_CACHE[user_sub_id]
        
    # Simulate fetching subscription data from a database or API
    if not _COSMOS_DB_CONNECTION:
        import os
        subscription_container_name = os.environ.get('COSMOS_SUBSCRIPTION_CONTAINER', "subscriptions")
        subscription_db_name = os.environ.get('COSMOS_SUBSCRIPTION_DB', "subscriptions")
        subscription_endpoint = os.environ.get('COSMOS_ENDPOINT', None)
        _COSMOS_DB_CONNECTION = CosmosDBConnection(subscription_container_name, subscription_db_name, subscription_endpoint)
    

    if entra_user:
        sub_data = _COSMOS_DB_CONNECTION.get_items_by_query(f"SELECT * FROM c WHERE c.entra_username = '{lower_sub_id}' AND c.is_entra_user = true")
    else:
        sub_data = _COSMOS_DB_CONNECTION.get_item(lower_sub_id)
    
    if not sub_data:
        raise ValueError(f"Subscription {sub_id} not found")
    sub = Subscription(sub_data)
    if not sub:
        raise ValueError(f"Subscription {sub_id} is invalid")
    if sub.is_expired():
        raise ValueError(f"Subscription {sub_id} is expired")
    
    if entra_user:
        _ENTRA_UN_TO_ID_CACHE[lower_sub_id] = sub.id
    _SUBSCRIPTION_CACHE[lower_sub_id] = sub
    return sub