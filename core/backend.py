# backend/main.py
# -*- coding: utf-8 -*-

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import importlib
import pkgutil

from backend.core.settings import settings
from backend.core.database import engine, Base

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def discover_routers(pkg="backend.modules"):
    mod_pkg = importlib.import_module(pkg)
    for _, mod_name, _ in pkgutil.walk_packages(
        mod_pkg.__path__, mod_pkg.__name__ + "."
    ):
        if mod_name.endswith(".api"):
            mod = importlib.import_module(mod_name)
            router = getattr(mod, "router", None)
            if router:
                app.include_router(router)
                print(f"rota carregada: {mod_name}")


discover_routers()


@app.get("/", tags=["Health"])
def home():
    return {"message": "SmartTec API rodando"}


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
