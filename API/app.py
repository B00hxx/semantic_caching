from fastapi import FastAPI
from .lifespan import lifespan
from .routes.chat import router as chat_router
from .routes.redaction_rules import router as upload_router
from .routes.stats import router as stats_router
from .routes.delete import router as delete_router
from .routes.auth import router as auth_router
from .routes.top_k_entries import router as postgres_router
from .routes.get_all_hot_entries import router as hot_entries_router

app = FastAPI(lifespan=lifespan)

app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(stats_router)
app.include_router(delete_router)
app.include_router(auth_router)
app.include_router(postgres_router)
app.include_router(hot_entries_router)
