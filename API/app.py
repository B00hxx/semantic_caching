from fastapi import FastAPI
from .lifespan import lifespan
from .routes.chat import chat_router
from .routes.redaction_rules import upload_router

app = FastAPI(lifespan=lifespan)

app.include_router(chat_router)
app.include_router(upload_router)