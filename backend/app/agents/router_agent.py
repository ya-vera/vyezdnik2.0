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
    temperature=0.0
)

ROUTER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Ты — роутер запросов.

Определи тип запроса. Верни строго одно значение:

- LAW → если вопрос про правила въезда, визы, сроки, требования
- FORM → если про анкеты, документы, заполнение
- BOTH → если есть и правила, и документы
"""),
    ("human", "{question}")
])

chain = ROUTER_PROMPT | llm | StrOutputParser()


def detect_intent(question: str) -> str:
    return chain.invoke({"question": question}).strip().upper()
