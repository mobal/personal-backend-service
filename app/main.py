from fastapi import FastAPI
from mangum import Mangum
from app.api.v1.router import router as api_v1_router

app = FastAPI()
app.include_router(api_v1_router, prefix='/api/v1')


@app.get('/')
async def index():
    return 'hello, world!'


handler = Mangum(app)
