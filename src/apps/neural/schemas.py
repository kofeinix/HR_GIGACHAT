import uuid
from typing import Dict, List, Tuple, Literal, Optional

from pydantic import BaseModel


class Message(BaseModel):
    datail: str


class QuestionRequest(BaseModel):
    level: str
    topic: str

class CheckAnswer(BaseModel):
    question_id: str
    answer: str

class QuestionResponseItem(BaseModel):
    question: str
    question_id: uuid.UUID
class QuestionResponse(BaseModel):
    status: str
    data: QuestionResponseItem

class EvaluatedAnswerItem(BaseModel):
    comment: str
    question_id: uuid.UUID
    mark: Optional[int]
    is_fraud: Optional[bool]
class EvaluatedAnswer(BaseModel):
    status: str
    data: EvaluatedAnswerItem

class SummarizedAnswer(BaseModel):
    status: str
    result: str

class AliveResponse(BaseModel):
    status: str