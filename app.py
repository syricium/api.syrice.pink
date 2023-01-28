import importlib
import multiprocessing
import os
import traceback

import redis.asyncio as redis
import uvicorn
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi_limiter import FastAPILimiter

from utils import Authorization

debug = (
    True if not os.getenv("DEBUG") else False if os.getenv("DEBUG") == "false" else True
)
app = FastAPI(
    debug=debug,
    title="api.syrice.pink",
    description="Utility API",
    docs_url="/"
)

app.debug = debug

app.auth = Authorization(app.debug)

@app.on_event("startup")
async def startup():
    redis_instance = redis.Redis(
        host="localhost",
        encoding="utf-8",
        decode_responses=True,
    )
    await FastAPILimiter.init(redis_instance)
    
    await app.auth.initialize(app)


rootdir = os.getcwd()
for root, _, files in os.walk(os.path.join(rootdir, "routes")):
    prefix = root[len(rootdir) + 1 :].replace("\\", "/").replace("/", ".")
    
    parent = prefix.split(".")[-1]  # get the parent of the file
    if parent == "__pycache__":  # ignore pycache folders
        continue
    
    for file in files:  # iterate through all files in a subdirectory
        if not file.endswith(".py"):
            continue
        fn = file[:-3]
        name = f"{prefix}.{fn}"
        
        try:
            imp = importlib.import_module(name)
        except Exception as exc:
            exc = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
        
            print(f"Error occured loading router {name}:\n{exc}")
        else:
            if hasattr(imp, "router"):
                router: APIRouter = getattr(imp, "router")
                prefix = name.replace(".", "/")
                if prefix.startswith("routes"):
                    prefix = prefix[len("routes"):]
                if prefix.endswith(f"/{fn}"):
                    
                    prefix = prefix[:-len(f"/{fn}")]
                try:
                    app.include_router(router, prefix=prefix)
                except Exception as exc:
                    exc = "".join(
                        traceback.format_exception(
                            type(exc), exc, exc.__traceback__
                        )
                    )
                
                    print(
                        f"Error occured loading router {name}:\n{exc}"
                    )
                else:
                    print(f"Succesfully loaded router {name}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=app.debug)
