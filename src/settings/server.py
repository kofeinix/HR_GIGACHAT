import logging
from src.settings.logger import set_logger
root_logger = logging.getLogger()
root_logger = set_logger(root_logger)

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from src.apps.docs.routers import swagger
from src.apps.neural.api_routers import neural_back
from starlette.staticfiles import StaticFiles
# from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware


app = FastAPI(docs_url=None, redoc_url=None)

origins = [
    'http://localhost',
    'http://localhost:2228',
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title='SRTe GPT',
        version='1.0.0.',
        description='SRTe GPT',
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


app.mount('/static', StaticFiles(packages=['src.apps.docs']), name="static")
app.include_router(neural_back)
app.include_router(swagger)
root_logger.info('Initialized server')
