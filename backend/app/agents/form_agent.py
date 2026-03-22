import json
import os
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

METADATA_PATH = Path(__file__).resolve().parent.parent / "data" / "metadata" / "countries.json"

llm = ChatOpenAI(
    model="mistral-large-latest",
    api_key=os.getenv("MISTRAL_API_KEY"),
    base_url="https://api.mistral.ai/v1",
    temperature=0.0,
)

FORM_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Ты — строгий технический ассистент базы данных "Въездник". 
    Твоя задача: проверить, есть ли запрашиваемый документ в предоставленном JSON-списке.

    АЛГОРИТМ:
    1. Проанализируй запрос пользователя: что именно он ищет? (анкету, визу, страховку и т.д.)
    2. Сравни запрос с названиями (name) и описаниями (description) форм в JSON.
    3. ЕСЛИ ЕСТЬ СЕМАНТИЧЕСКОЕ СОВПАДЕНИЕ: Выдай информацию только по этой форме (Название, Описание, Ссылки).
    4. ЕСЛИ ЗАПРОС ОБЩИЙ (например, "какие документы?"): Выдай краткий список всех форм из JSON.
    5. ЕСЛИ СОВПАДЕНИЯ НЕТ (например, просят визу, а в JSON только анкета): Вежливо скажи, что в базе "Въездник" по стране {{country_name}} информация о "{{user_request}}" на данный момент отсутствует.
    
    СТРОГО ЗАПРЕЩЕНО:
    - Выдавать информацию об одном документе, если пользователь спрашивает про другой.
    - Использовать любые свои знания о правилах въезда. Только JSON!
    """),
    ("human", """ДАННЫЕ JSON:
    {{forms_data}}
    
    СТРАНА: {{country_name}}
    ЗАПРОС ПОЛЬЗОВАТЕЛЯ: "{{user_request}}"
    
    Твой ответ:""")
], template_format="jinja2") 

chain = FORM_PROMPT | llm | StrOutputParser()

def get_country_data(country_query: str):
    if not METADATA_PATH.exists(): return None
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    query = country_query.lower().strip()
    if query in data: return data[query]
    for key, info in data.items():
        if info.get("name", "").lower() == query: return info
    return None

def form_agent(country_query: str, user_request: str):
    country_data = get_country_data(country_query)
    if not country_data:
        return f"К сожалению, в моей базе пока нет информации о формах для страны: {country_query}."

    response = chain.invoke({
        "country_name": country_data.get("name", country_query),
        "forms_data": json.dumps(country_data.get("forms", []), indent=2, ensure_ascii=False),
        "user_request": user_request
    })
    
    return response