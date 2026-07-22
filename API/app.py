from fastapi import FastAPI
from .routes import router
from .lifespan import lifespan

app = FastAPI(lifespan=lifespan)

app.include_router(router)