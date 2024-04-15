import logging
logger = logging.getLogger(__name__)

from fastapi import Request, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing_extensions import Annotated
from starlette import status

security = HTTPBasic()

async def get_current_auth_user(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    logger.info('Authenticating user')
    if credentials:
        logger.debug(f'Checking {credentials.username} credentials')
        return await token_cheker(credentials.username, credentials.password)
    else:
        logger.error('401 UNATHORIZED')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect username or password',
                            headers={'WWW-Authenticate': 'Basic'}, )

async def token_cheker(username, password):
    return username
