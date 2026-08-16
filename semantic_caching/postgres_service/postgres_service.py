import asyncpg
from ..cache_entry.cache_entry_persistent import CacheEntryForPersistence

class PostgresService:
    def __init__(self, host : str,
                 port : int,
                 database : str,
                 user : str,
                 password : str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool = None
    
    async def initialize(self):
        self.pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
        )