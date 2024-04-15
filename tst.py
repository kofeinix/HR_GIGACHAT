from langchain.chat_models.gigachat import GigaChat

from langchain.globals import set_verbose, set_debug
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import load_prompt

set_debug(True)
set_verbose(True)

import configparser
from langchain_core.runnables import RunnablePassthrough


config = configparser.ConfigParser()
config.read('config.ini')
# Авторизация в сервисе GigaChat
gigachat = GigaChat(credentials=config['DEFAULT']['auth'],
                auth_url=config['DEFAULT']['auth_url'],
                scope=config['DEFAULT']['scope'],
                model = config['MODEL']['model'],
                verify_ssl_certs=False,
                use_api_for_tokens=True,
                )


gigachat.get_num_tokens('asd')
check_answer = load_prompt('files/templates/check_answer.yaml')
check_answer_chain = (
        {"question": lambda x: "Для чего используется функция init?",
         "correct_answer": lambda x: "Функция init является конструктором класса, и она вызывается автоматически при создании нового экземпляра класса. Эта функция используется для инициализации атрибутов, которые будут принадлежать объектам, создаваемым с помощью класса. Внутри функции init определяются атрибуты объекта, которые будут доступны через ссылку на экземпляр, на который ссылается переменная self",
         "user_answer": RunnablePassthrough()}
        | check_answer
        | gigachat
        | StrOutputParser()
)
check_answer_chain.invoke('выполняется при создании экземпляра класса')


check_fraud = load_prompt('files/templates/check_fraud.yaml')
check_fraud_chain = (
        {"message": RunnablePassthrough()}
        | check_fraud
        | gigachat
        | StrOutputParser()
)
check_fraud_chain.invoke('asd')

generate_first_question = load_prompt('files/templates/generate_first_question.yaml')
generate_first_question_chain = (
        {"topic": lambda x: 'sql',
         'level': lambda x: "простой"}
        | generate_first_question
        | gigachat
        | StrOutputParser()
)
generate_first_question_chain.invoke('')


generate_second_question = load_prompt('files/templates/generate_second_question.yaml')
generate_second_question_chain = (
        {'context': lambda x: "Bot: Что такое свойство ACID в базе данных?. User: Atomicity, Consistency, Isolation, Durability."}
        | generate_second_question
        | gigachat
        | StrOutputParser()
)
generate_second_question_chain.invoke('')

answer_second_question = load_prompt('files/templates/answer_second_question.yaml')
answer_second_question_chain = (
        {'context': lambda x: "Bot: Что такое свойство ACID в базе данных?. User: Atomicity, Consistency, Isolation, Durability.",
         'question': lambda x: "Bot: Какое значение имеет свойство ACID в базе данных и как оно влияет на работу системы?"}
        | answer_second_question
        | gigachat
        | StrOutputParser()
)
answer_second_question_chain.invoke('')

from transformers import pipeline
pipe = pipeline("text-classification", model="files/hf_models/rubert-tiny2-cedr-emotion-detection")

from transformers import AutoTokenizer, AutoModelForSequenceClassification

tokenizer = AutoTokenizer.from_pretrained("files/hf_models/rubert-tiny2-cedr-emotion-detection")
model = AutoModelForSequenceClassification.from_pretrained("files/hf_models/rubert-tiny2-cedr-emotion-detection")

text = "я тебя люблю"
input = tokenizer.encode(text, return_tensors = "pt")
output = model(input)
classificated = output.logits.softmax(-1)[0].tolist()
id2label= {
    0: "no_emotion",
    1: "joy",
    2: "sadness",
    3: "surprise",
    4: "fear",
    5: "anger"
}
classificated_dict = {}
for key, value in id2label.items():
    classificated_dict[value] = classificated[key]
#pipe("я тебя люблю")
import dateutil.parser as dparser
dparser.parse('2024-04-13 11:03:30 - Таня HR (распознано): Ну а как же тогда вы?', fuzzy=True)