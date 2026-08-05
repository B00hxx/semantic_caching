from fastapi import FastAPI
from .lifespan import lifespan
from .routes.chat import chat_router

app = FastAPI(lifespan=lifespan)

app.include_router(chat_router)