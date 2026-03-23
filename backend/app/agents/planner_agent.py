from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
    model="mistral-large-latest",
    api_key=os.getenv("MISTRAL_API_KEY"),
    base_url="https://api.mistral.ai/v1",
    temperature=0.0,
)

PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Ты — планировщик мультиагентной системы "Въездник".

Твоя задача:
1. Понять, что хочет пользователь
2. Выбрать нужных агентов
3. Вернуть план выполнения

Доступные агенты:
- lawyer → правила въезда, визы, сроки, требования
- form → анкеты, документы, заполнение

ЛОГИКА:
- Если только правила → один шаг lawyer
- Если только документы → один шаг form
- Если и то и другое → сначала lawyer, потом form

ВАЖНО:
- Не добавляй лишние шаги
- Минимизируй количество вызовов

Верни строго JSON:

{
  "steps": [
    {"agent": "lawyer", "reason": "..."}
  ]
}
"""),
    ("human", "{question}")
])

chain = PLANNER_PROMPT | llm | JsonOutputParser()

def plan(question: str):
    try:
        return chain.invoke({"question": question})
    except:
        return {"steps": [{"agent": "lawyer", "reason": "fallback"}]}