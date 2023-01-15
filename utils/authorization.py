from typing import Optional
import asyncpg
from fastapi import FastAPI, Response, Request
from fastapi.security import OAuth2PasswordBearer
from passlib.hash import pbkdf2_sha256

from starlette.middleware.base import BaseHTTPMiddleware
from urllib.parse import urlparse
import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Authorization:
    def __init__(self, debug: bool = True, db_container_name: str = "api_db") -> None:
        self._db = None
        self._debug = debug
        self._db_c_n = db_container_name

    @property
    def db(self):
        if self._db is None:
            raise Exception("db is not yet initialized")

        return self._db

    @property
    def _host(self):
        return "127.0.0.1" if self._debug else self._db_c_n

    async def initialize(self, app: FastAPI) -> None:
        self._db = await asyncpg.create_pool(
            database=settings.db.name,
            host=self._host,
            port="5432",
            user=settings.db.user,
            password=settings.db.password,
        )
        
        with open("schema.sql") as fb:
            await self._db.execute(fb.read())
            
        app.add_middleware(BaseHTTPMiddleware, dispatch=self._middleware)
            
    async def _middleware(self, request: Request, call_next):
        path = urlparse(str(request.url)).path
        
        if path in settings.auth_routes:
            api_key: str = request.headers.get("Authorization")
            if not api_key or not await request.app.auth.check_api_key(api_key):
                return Response(
                    content="Forbidden",
                    status_code=403
                )
        
        response = await call_next(request)
        return response

    async def check_api_key(self, api_key: str) -> bool:
        query = await self._db.fetch("SELECT api_key FROM users")

        if not query:
            return False

        invalid = True
        for item in query:
            item = item["api_key"]
            if pbkdf2_sha256.verify(api_key, item):
                invalid = False
                break

        return not invalid

    async def fetch(self, *args, **kwargs):
        return await self._db.fetch(*args, **kwargs)

    async def fetchrow(self, *args, **kwargs):
        return await self._db.fetch(*args, **kwargs)

    async def fetchval(self, *args, **kwargs):
        return await self._db.fetch(*args, **kwargs)

    async def execute(self, *args, **kwargs):
        return await self._db.fetch(*args, **kwargs)

    async def get_user_by_key(self, key: str) -> Optional[str]:
        results = await self._db.fetch("SELECT * FROM users")
        for result in results:
            api_key = result["api_key"]
            username = result["username"]
            if pbkdf2_sha256.verify(key, api_key):
                return username
