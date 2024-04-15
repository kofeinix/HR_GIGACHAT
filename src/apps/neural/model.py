import distutils.util
import uuid
import json
from fastapi import BackgroundTasks
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models.gigachat import GigaChat
from langchain_community.document_loaders.text import TextLoader
from langchain_community.embeddings.gigachat import GigaChatEmbeddings
from langchain.prompts import load_prompt
from langchain.globals import set_verbose, set_debug
from langchain_core.output_parsers import StrOutputParser
import logging
import configparser
import dateutil.parser as dparser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.sql.expression import func
from src.apps.neural.db_models import QA, Metric
from src.settings.database import get_session, get_or_create
from transformers import pipeline

config = configparser.ConfigParser()
config.read('config.ini')
set_verbose(config.getboolean('DEFAULT','DEBUG'))
set_debug(config.getboolean('DEFAULT','DEBUG'))
logger = logging.getLogger(__name__)

class EmbeddingsInput(GigaChatEmbeddings):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def __call__(self, input):
        return self.embed_documents(texts=input)

class CustomGigaChat:
    def __init__(self):
        # Авторизация в сервисе GigaChat
        logger.debug('Creating GigaChat connection...')
        self.gigachat = GigaChat(
                            # credentials=config['DEFAULT']['auth'],
                            # auth_url=config['DEFAULT']['auth_url'],
                            scope=config['DEFAULT']['scope'],
                            model=config['MODEL']['model'],
                            verify_ssl_certs=False,
                            use_api_for_tokens=True,
                            ca_bundle_file = 'certificates/root_pem.txt',
                            cert_file = 'certificates/chain_pem.txt',
                            key_file = 'certificates/00CA0001K817_U_TS_K817_CLUSTERDISCOVERY.key'
                                 )

        self.big_gigachat = GigaChat(credentials=config['DEFAULT']['auth'],
                            auth_url=config['DEFAULT']['auth_url'],
                            scope=config['DEFAULT']['scope'],
                            model=config['MODEL']['big_model'],
                            verify_ssl_certs=False,
                            use_api_for_tokens=True,
                            timeout=600)

        self.embeddings = EmbeddingsInput(credentials=config['DEFAULT']['auth'],
                auth_url=config['DEFAULT']['auth_url'],
                verify_ssl_certs=False,
                scope=config['DEFAULT']['scope'],)


class Generator:
    def __init__(self, gigachat, big_gigachat):
        self.gigachat = gigachat
        self.big_gigachat = big_gigachat
        self.check_answer_template = load_prompt('files/templates/check_answer.yaml')
        self.check_fraud_template = load_prompt('files/templates/check_fraud.yaml')
        self.generate_first_question_template = load_prompt('files/templates/generate_first_question.yaml')
        self.generate_answer_template = load_prompt('files/templates/generate_answer.yaml')
        self.generate_comment_template = load_prompt('files/templates/generate_comment.yaml')
        self.interview_map_prompt = load_prompt("files/templates/interview_map.yaml")
        self.interview_reduce_prompt = load_prompt("files/templates/interview_reduce.yaml")

        self.user_characteristic_map_prompt = load_prompt("files/templates/user_characteristic_prompt_map.yaml")
        self.user_characteristic_reduce_prompt = load_prompt("files/templates/user_characteristic_prompt_reduce.yaml")

    async def get_question(self, topic:str, level:str, new_questions:bool):
        session=get_session()
        if new_questions:
            logger.debug(f'start generation question for: {topic}, {level}')
            self.gigachat.temperature = 1.5
            generate_first_question_chain = (
                    {"topic": lambda x: topic,
                     'level': lambda x: level}
                    | self.generate_first_question_template
                    | self.gigachat
                    | StrOutputParser()
            )
            question = await generate_first_question_chain.ainvoke('')
            answer = await self.generate_answer(topic, question)
            print(answer)
            question_id = uuid.uuid4()
            session.add(QA(question=question, answer=answer, question_id=str(question_id), topic=topic, level=level))
            session.commit()
        else:
            logger.debug(f'selectiong random question in database: {topic}, {level}')
            data = session.query(QA).filter(QA.topic == topic, QA.level == level).order_by(func.random()).first()
            if not data:
                logger.error(f'There is no question for such topic {topic}, level {level}!')
                raise TypeError(f'There is no question for such topic {topic}, level {level}!')
            question_id = data.question_id
            question = data.question
        return question, question_id

    async def generate_answer(self, topic:str, question:str):
        logger.debug(f'start answering question for: {topic}, {question}')
        self.gigachat.temperature = 1.0
        generate_answer_chain = (
                {"topic": lambda x: topic,
                 'question': lambda x: question}
                | self.generate_answer_template
                | self.gigachat
                | StrOutputParser()
        )
        answer = await generate_answer_chain.ainvoke('')
        return answer

    async def check_alive(self):
        try:
            assert self.gigachat.get_num_tokens('asd') == 2
            return True
        except Exception as e:
            logger.error(f"alive check failed with {str(e)}")
            return False

    async def check_answer(self, question_id:uuid.uuid4(), user_answer:str) -> [str, int]:
        session = get_session()
        data = session.query(QA).get(question_id)
        self.gigachat.temperature = 1.0
        if not data:
            return None, None
        check_answer_chain = (
                {"question": lambda x: data.question,
                 "correct_answer": lambda x: data.answer,
                 "user_answer": RunnablePassthrough()}
                | self.check_answer_template
                | self.gigachat
                | StrOutputParser()
        )
        mark = await check_answer_chain.ainvoke(user_answer)
        try:
            mark = int(mark)
            comment = await self.generate_comment(question=data.question, answer=data.answer, user_answer=user_answer, mark=mark)
        except Exception as e:
            mark = None
            comment = 'Очень хорошо! Переходим к следующему вопросу!'
        return comment, mark

    async def generate_comment(self, question, answer, user_answer, mark):
        self.gigachat.temperature = 1.0
        generate_comment_chain = (
                {"question": lambda x: question,
                 "correct_answer": lambda x: answer,
                 "user_answer": lambda x: user_answer,
                 "mark": lambda x: mark}
                | self.generate_comment_template
                | self.gigachat
                | StrOutputParser()
        )
        comment = await generate_comment_chain.ainvoke('')
        return comment


    async def check_fraud(self, user_answer:str):
        self.gigachat.temperature = 1.0
        check_fraud_chain = (
                {"message": RunnablePassthrough()}
                | self.check_fraud_template
                | self.gigachat
                | StrOutputParser()
        )
        is_fraud = check_fraud_chain.invoke(user_answer)
        try:
            is_fraud = bool(distutils.util.strtobool(is_fraud))
        except:
            is_fraud = None
        return is_fraud

    async def evaluate_user(self, path, metric_id, background_tasks: BackgroundTasks):
        session = get_session()
        loader = TextLoader(path, encoding='utf-8')
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=5000,
            chunk_overlap=500,
            length_function=len,
            is_separator_regex=False,
        )
        documents = text_splitter.split_documents(documents)
        print(f"Количество частей интервью: {len(documents)}")
        metric = get_or_create(session, Metric, metric_id=metric_id)
        metric.status = 'in_progress'
        session.commit()
        background_tasks.add_task(self.evaluation_pipeline, documents = documents, path = path, metric_id = metric_id)
        #self.evaluation_pipeline(documents = documents, path = path, metric_id = metric_id)
        return 'in process'

    def evaluation_pipeline(self, documents, path, metric_id):
        self.summarize_interview_background(documents = documents, metric_id = metric_id)
        self.user_characteristic(documents = documents, metric_id = metric_id)
        self.detect_mood(path = path, metric_id = metric_id)

    def summarize_interview_background(self, documents, metric_id):
        chain = load_summarize_chain(self.big_gigachat,
                                     chain_type="map_reduce",
                                     map_prompt=self.interview_map_prompt,
                                     combine_prompt=self.interview_reduce_prompt,
                                     verbose=False)
        res = chain.invoke({"input_documents": documents})
        session = get_session()
        metric = session.query(Metric).get(metric_id)
        metric.status = 'summary_processed'
        metric.summarization = res['output_text']
        session.commit()
        logger.info(res['output_text'])

    def user_characteristic(self, documents, metric_id):
        chain = load_summarize_chain(self.big_gigachat,
                                     chain_type="map_reduce",
                                     map_prompt=self.user_characteristic_map_prompt,
                                     combine_prompt=self.user_characteristic_reduce_prompt,
                                     verbose=False)
        res = chain.invoke({"input_documents": documents})
        session = get_session()
        metric = session.query(Metric).get(metric_id)
        metric.status = 'characteristic processed! '
        metric.characteristic = res['output_text']
        session.commit()
        logger.info(res['output_text'])


    def detect_mood(self, path, metric_id):
        mood_model = MoodModel()
        moods=[]
        loader = TextLoader(path, encoding='utf-8')
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )
        documents = text_splitter.split_documents(documents)
        for document in documents:
            try:
                ts = dparser.parse(document.page_content[:19]).strftime("%Y-%m-%d, %H:%M:%S")
            except:
                ts = ''
            res = mood_model.predict(document.page_content)
            res['ts'] = ts
            moods.append(res)

        session = get_session()
        metric = session.query(Metric).get(metric_id)
        metric.status = 'mood processed! '
        metric.mood = json.dumps(moods)
        session.commit()
        print(moods)



def get_generator():
    GC = CustomGigaChat()
    gigachat = GC.gigachat
    big_gigachat = GC.big_gigachat
    generator = Generator(gigachat, big_gigachat)
    return generator

class MoodModel():
    def __init__(self):
        self.pipe = pipeline("text-classification", model="files/hf_models/rubert-tiny2-cedr-emotion-detection")
    def predict(self, text):
        data = self.pipe(text, return_all_scores=True)[0]
        classificated_dict = {}
        for emotion in data:
            classificated_dict[emotion["label"]]=emotion["score"]
        return classificated_dict
