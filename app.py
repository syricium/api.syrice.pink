import multiprocessing
import os

import redis.asyncio as redis
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi_limiter import FastAPILimiter

from utils import Authorization

app = FastAPI()

app.debug = (
    True if not os.getenv("DEBUG") else False if os.getenv("DEBUG") == "false" else True
)

app.auth = Authorization(app.debug)

@app.on_event("startup")
async def startup():
    redis_instance = redis.Redis(
        host="localhost" if app.debug else "api_redis",
        encoding="utf-8",
        decode_responses=True,
    )
    await FastAPILimiter.init(redis_instance)
    
    await app.auth.initialize(app)


for route_name in os.listdir("routes"):
    if not route_name.endswith("py"):
        continue
    imp_name = "routes." + route_name.replace(".py", "")
    route = __import__(imp_name)
    imp = getattr(route, route_name.replace(".py", ""))

    if hasattr(imp, "router"):
        app.include_router(getattr(imp, "router"))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=app.debug)
