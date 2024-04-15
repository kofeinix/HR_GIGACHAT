from fastapi import APIRouter, Depends
from fastapi.openapi.docs import (
    get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html)
import os
import logging
logger = logging.getLogger(__name__)

swagger = APIRouter()

@swagger.get("/docs", include_in_schema=False)
async def my_get_swagger_ui_html():
    logger.info('SWAGGER page opened')
    return get_swagger_ui_html(
        openapi_url='/openapi.json',
        title='PULSE HR GPT',
        oauth2_redirect_url='/docs/oauth2-redirect',
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.ico",
    )
