from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
    model="mistral-large-latest",
    api_key=os.getenv("MISTRAL_API_KEY"),
    base_url="https://api.mistral.ai/v1",
    temperature=0.0,
)

CENSOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Ты — агент проверки качества.

Проверь ответ:
- соответствует ли он вопросу
- нет ли выдуманных фактов
- есть ли дисклеймер

Ответь:
APPROVE или REJECT
"""),
    ("human", "Вопрос:\n{question}\n\nОтвет:\n{answer}")
])

chain = CENSOR_PROMPT | llm | StrOutputParser()

def censor(question: str, answer: str) -> bool:
    result = chain.invoke({
        "question": question,
        "answer": answer
    }).strip().upper()

    return result == "APPROVE"