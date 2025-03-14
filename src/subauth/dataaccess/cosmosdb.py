import os
from azure.cosmos import CosmosClient, ContainerProxy, CosmosDict
from azure.cosmos.errors import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError
from azure.core.exceptions import ResourceNotFoundError
from azure.core.exceptions import HttpResponseError
from azure.core.exceptions import ClientAuthenticationError
from azure.core.exceptions import ServiceRequestError

CONTAINER_CONNECTIONS = {}
CACHE_CONTAINER_CONNECTIONS = os.environ.get('CACHE_COSMOS_CONTAINER_CONNECTIONS', "true").lower() == "true"

def _connect_to_cosmos_container(container:str, db:str = None, endpoint:str = None, create_if_not_exists:bool = True, partition_key:str = "/id") -> ContainerProxy:
    global CONTAINER_CONNECTIONS
    global CACHE_CONTAINER_CONNECTIONS
    
    if not endpoint:
        endpoint = os.environ.get('COSMOS_ENDPOINT', os.environ.get('COSMOS_ACCOUNT_HOST', os.environ.get('SUBSCRIPTIONS_COSMOS_ENDPOINT', None)))
    if not endpoint:
        raise ValueError("CosmosDB endpoint was not provided and default endpoint not found in environment [COSMOS_ENDPOINT]")

    if not db:
        db = os.environ.get('COSMOS_DB', None)
    if not db:
        raise ValueError("CosmosDB database was not provided and default database not found in environment [COSMOS_DB]")
    if not container:
        raise ValueError("CosmosDB container was not provided")


    cache_key = f"{endpoint}/{db}/{container}"
    if CACHE_CONTAINER_CONNECTIONS and cache_key in CONTAINER_CONNECTIONS:
        return CONTAINER_CONNECTIONS[cache_key]
    
    ## Determine if we are using a connection string, key or Managed Identity
    connection_string = os.environ.get('COSMOS_CONNECTION_STRING', None)
    key = os.environ.get('COSMOS_KEY', None)
    
    ## Load the Client
    client = None
    if connection_string is not None:
        client = CosmosClient.from_connection_string(connection_string)
    elif key is not None:
        client = CosmosClient(endpoint, {'masterKey': key})
    else:
        client = CosmosClient(endpoint, DefaultAzureCredential())

    ## Connect to the DB + Container
    ## Check if the database exists
    try:
        db_client = client.get_database_client(db)
        db_client.read()
    except ResourceNotFoundError:
        if create_if_not_exists:
            db_client = client.create_database(db)
        else:
            raise ValueError(f"Database {db} does not exist and create_if_not_exists is set to False")
    except HttpResponseError as e:
        if e.status_code == 403:
            raise ValueError(f"Failed to connect to CosmosDB database: {db}. Check your credentials.")
        else:
            raise e
    except ClientAuthenticationError as e:
        raise ValueError(f"Failed to authenticate with CosmosDB: {e}")
    except ServiceRequestError as e:
        raise ValueError(f"Failed to connect to CosmosDB: {e}")
    
    ## Check if the container exists
    try:
        connection = db_client.get_container_client(container)
        connection.read()
    except ResourceNotFoundError:
        if create_if_not_exists:
            connection = db_client.create_container(container, partition_key=partition_key)
        else:
            raise ValueError(f"Container {container} does not exist and create_if_not_exists is set to False")
    except HttpResponseError as e:
        if e.status_code == 403:
            raise ValueError(f"Failed to connect to CosmosDB container: {container}. Check your credentials.")
        else:
            raise e
    except ClientAuthenticationError as e:
        raise ValueError(f"Failed to authenticate with CosmosDB: {e}")
    except ServiceRequestError as e:
        raise ValueError(f"Failed to connect to CosmosDB: {e}")
    

    # db_client = client.get_database_client(db)
    # connection = db_client.get_container_client(container)

    ## Cache the Connection if needed
    if CACHE_CONTAINER_CONNECTIONS:
        CONTAINER_CONNECTIONS[cache_key] = connection

    return connection

class CosmosDBConnection:
    """
    A connection to a container in a CosmosDB database.
    """
    _endpoint: str
    _database: str
    _container: str
    _container_client: ContainerProxy

    def __init__(self, container_name: str, database_name: str = None, endpoint: str = None):
        """
        Initialize the CosmosDBDataAccess class with the given parameters.
        """
        self._endpoint = endpoint
        self._database = database_name
        self._container = container_name
        self._container_client = None
        self.connect()

    def connect(self):
        """
        Connect to the CosmosDB database.
        """
        if self._container_client is None:
            self._container_client = _connect_to_cosmos_container(self._container, self._database, self._endpoint)
        if not self._container_client:
            raise ValueError(f"Failed to connect to CosmosDB container: {self._container}")
        return self
    
    def disconnect(self):
        """
        Disconnect from the CosmosDB database.
        """     
        if self._container_client:
            self._container_client = None
        return self
    
    def get_item(self, id:str, partitionKey:str = None) -> CosmosDict|None:
        try:
            self.connect()  # Ensure the connection is established
            pk = partitionKey if partitionKey is not None else id
            return self._container_client.read_item(item=id, partition_key=pk)
        except CosmosResourceNotFoundError: 
            return None

    def get_item_list(self, id_list:list[str], partitionKey:str = None) -> list[CosmosDict]:
        try:
            self.connect() # Ensure the connection is established
            if partitionKey is None: 
                return list(self._container_client.query_items(
                    query="SELECT * FROM c WHERE ARRAY_CONTAINS(@items, c.id)",
                    enable_cross_partition_query=True, 
                    parameters=[ { "name":"@items", "value": id_list }, ]
                ))
            else: 
                return list(self._container_client.query_items(
                    query=f"SELECT * FROM c WHERE c.partitionKey=@partition_key AND ARRAY_CONTAINS(@items, c.id)",
                    parameters=[ { "name":"@partition_key", "value": partitionKey }, { "name":"@items", "value": id_list }, ],
                    enable_cross_partition_query=False
                ))
        except CosmosResourceNotFoundError: 
            return None


    def get_partition_items(self, partitionKey:str) -> list[CosmosDict]:
        self.connect()  # Ensure the connection is established
        return list(self._container_client.query_items(
            query="SELECT * FROM c WHERE c.partitionKey=@partition_key ORDER BY c._ts DESC",
            parameters=[
                { "name":"@partition_key", "value": partitionKey }
            ]
        ))

    def get_all_items(self, source:str = None) -> list[CosmosDict]:
        self.connect()  # Ensure the connection is established
        return list(self._container_client.query_items(
            query="SELECT * FROM c ORDER BY c._ts DESC",
            enable_cross_partition_query=True
        ))

    def get_items_by_query(self, query:str, source:str = None) -> list[CosmosDict]:
        self.connect() # Ensure the connection is established
        return list(self._container_client.query_items(query=query, enable_cross_partition_query=True))


    def upsert_item(self, item:dict, ttl:int = None, source:str = None):
        try:
            self.connect()  # Ensure the connection is established
            if ttl is not None: 
                if type(ttl) is str:
                    if ttl.isnumeric():
                        ttl = int(ttl)
                    elif source is None:
                        source = ttl
                        ttl = None 

                if ttl is not None: 
                    item = { "ttl":ttl, **item }

            self._container_client.upsert_item(body=item)
        except Exception as e: 
            print("failed to upsert this item:", item)
            raise e
        
    def delete_item(self, id:str, partitionKey:str = None):
        self.connect() # Ensure the connection is established
        self._container_client.delete_item(item=id, partition_key=partitionKey)

