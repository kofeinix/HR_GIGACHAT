import asyncio
from fastapi import APIRouter, Depends, UploadFile, BackgroundTasks, Response, status
from src.apps.neural.model import get_generator
from src.apps.neural.schemas import Message, QuestionRequest, QuestionResponse, CheckAnswer, EvaluatedAnswer, \
    SummarizedAnswer, AliveResponse
from src.authentication.auth import get_current_auth_user
import logging
from typing_extensions import Annotated
import configparser
import aiofiles

config = configparser.ConfigParser()
config.read('config.ini')

logger = logging.getLogger(__name__)
# model_state_lock = asyncio.Lock()


neural_back = APIRouter(prefix='/gpt/api/v1', responses={401: {"description": 'Not authorized', "model": Message},
                                                  403: {"description": 'Not allowed', "model": Message},
                                                  500: {"description": "Internal server error", "model": Message},
                                                  503: {"description": "Neural service unavailable", "model": Message}
                                                  })
logger.info('Initializing GPT APIRouter')

generator = get_generator()

@neural_back.post("/get_question", status_code=200)
async def get_question(username: Annotated[str, Depends(get_current_auth_user)],
                  user_data: QuestionRequest,
                       response: Response) -> QuestionResponse:
    if username:
        logger.debug(f"{username} trying to log in")
        topic = user_data.topic
        level = user_data.level
        question, question_id = await generator.get_question(topic=topic, level=level, new_questions=config.getboolean('DEFAULT','NEW_QUESTIONS'))
        return {'status':'OK', 'data': {"question": question, "question_id":question_id}}

    else:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        logger.error(f'Anonymous request will not be processed')
        return {'status':'Anonymous request will not be processed', 'data': {}}

@neural_back.post("/is_neural_online", status_code=200)
async def is_neural_online(response: Response) -> AliveResponse:
    stat = await generator.check_alive()
    if stat:
        return {'status': 'OK'}
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {'status': 'Unavailable'}


@neural_back.post("/check_answer", status_code=200)
async def check_answer(username: Annotated[str, Depends(get_current_auth_user)],
                    user_data: CheckAnswer,
                    response: Response) -> EvaluatedAnswer:
    if username:
        logger.debug(f"{username} trying to log in")
        question_id = user_data.question_id
        answer = user_data.answer
        is_fraud = await generator.check_fraud(user_answer=answer)
        comment, mark = await generator.check_answer(question_id=question_id, user_answer=answer)
        return {'status':'OK', 'data': {"comment": comment, "question_id":question_id, 'mark': mark, 'is_fraud': is_fraud}}

    else:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        logger.error(f'Anonymous request will not be processed')
        return {'status':'Anonymous request will not be processed', 'data': {}}

@neural_back.post("/evaluate_user", status_code=200)
async def evaluate_user(username: Annotated[str, Depends(get_current_auth_user)],
                       file: UploadFile, background_tasks: BackgroundTasks,
                        metric_id: str,
                        response: Response) -> SummarizedAnswer:
    if username:
        logger.debug(f"{username} trying to log in for text processing")
        out_file_path = f'files/inverviews/{username}_{file.filename}'
        async with aiofiles.open(out_file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        result = await generator.evaluate_user(path = out_file_path, metric_id=metric_id, background_tasks=background_tasks)
        return {'status':'OK', 'data': result}
    else:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {'status':'Anonymous request will not be processed',  'data': ''}
        logger.error(f'Anonymous request will not be processed')

