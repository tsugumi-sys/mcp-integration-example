from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import load_settings
from db import connect, init_db
from routes import admin, api, auth, chat, dummy_oauth, oauth


def create_app() -> FastAPI:
    load_dotenv()
    settings = load_settings()
    app = FastAPI(title="App Server")

    conn = connect(settings.database_path)
    init_db(conn)

    app.state.db = conn
    app.state.settings = settings

    app.include_router(dummy_oauth.router)
    app.include_router(admin.router)
    app.include_router(oauth.router)
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(api.router)

    app.mount("/static", StaticFiles(directory="static"), name="static")
    return app


app = create_app()


def main() -> None:
    settings = load_settings()
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
