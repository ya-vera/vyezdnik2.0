from orchestrator import orchestrator

tests = [
     "Нужна ли виза в Таиланд?",
     "Как заполнить TDAC?",
     "Хочу в Таиланд с ребенком, нужна ли виза и какие анкеты заполнять?",
     "Напиши код на Python",
]

for question in tests:
    print(f"Q: {question}")
    print("Ответ:\n")

    try:
        response = orchestrator(question, country="thailand")
        print(response)
    except Exception as e:
        print(f"Ошибка: {e}")

    print("\n" + "="*50 + "\n")