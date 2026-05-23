from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from backend.database import engine, Base
from backend.routers import accounts, trends, posts, influencers, costs
from backend.services import scheduler as sched


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    sched.start()
    yield
    sched.scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.include_router(accounts.router)
app.include_router(trends.router)
app.include_router(posts.router)
app.include_router(influencers.router)
app.include_router(costs.router)


@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()


app.mount("/static", StaticFiles(directory="static"), name="static")
