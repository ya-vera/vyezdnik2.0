from router_agent import detect_intent

tests = [
    
    "Нужна ли виза в Таиланд?",
    "Как заполнить анкету TDAC?",
    "Какие документы нужны и как заполнить форму?",
]

for question in tests:
    intent = detect_intent(question)
    print(f"Q: {question}")
    print(f"→ Intent: {intent}\n")
    
