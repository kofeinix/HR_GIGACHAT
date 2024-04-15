import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, func, CHAR
from sqlalchemy.orm import relationship
from src.settings.database import Base


class QA(Base):
    __tablename__ = "QA"

    question_id = Column(CHAR(32), primary_key=True, default=uuid.uuid4)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    level = Column(String, nullable=False)
    created_ts = Column(DateTime, default=func.current_timestamp())
    updated_ts = Column(DateTime,
                    default=func.current_timestamp(),
                    onupdate=func.current_timestamp())


class Metric(Base):
    __tablename__ = "Metric"

    metric_id = Column(CHAR(32), primary_key=True, default=uuid.uuid4)
    status = Column(String, nullable=True)
    mood = Column(String, nullable=True)
    summarization = Column(String, nullable=True)
    characteristic = Column(String, nullable=True)
    recommendation = Column(String, nullable=True)
    created_ts = Column(DateTime, default=func.current_timestamp())
    updated_ts = Column(DateTime,
                    default=func.current_timestamp(),
                    onupdate=func.current_timestamp())

class User(Base):
    __tablename__ = "User"

    user_id = Column(CHAR(32), primary_key=True, default=uuid.uuid4)
    user_name = Column(String, nullable=True)
    resume = Column(String, nullable=True)
    vacancies = relationship("Vacancy", secondary="User_x_Vacancy")


class Vacancy(Base):
    __tablename__ = "Vacancy"

    vacancy_id = Column(CHAR(32), primary_key=True, default=uuid.uuid4)
    vacancy_description = Column(String, nullable=False)
    attributes = Column(String, nullable=False)
    level = Column(String, nullable=False)
    users = relationship("User", secondary="User_x_Vacancy")

class User_x_Vacancy(Base):
    __tablename__ = "User_x_Vacancy"
    user_id = Column(Integer, ForeignKey('User.user_id'), primary_key=True)
    vacancy_id = Column(Integer, ForeignKey('Vacancy.vacancy_id'), primary_key=True)
    metric_id = Column(Integer, ForeignKey('Metric.metric_id'), nullable=True, default=uuid.uuid4)
    metric = relationship("Metric", uselist=False, backref="User_x_Vacancy")
    is_allowed = Column(Boolean, nullable=True, default=False)

