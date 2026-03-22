from form_agent import form_agent

print("--- ТЕСТ 1: Конкретный запрос про анкету ---")
print(form_agent("Таиланд", "мне нужна ссылка на цифровую анкету TDAC"))

print("\n--- ТЕСТ 2: Общий запрос ---")
print(form_agent("thailand", "какие документы надо заполнять?"))

print("\n--- ТЕСТ 3: Запрос того, чего нет в JSON ---")
print(form_agent("Таиланд", "дай ссылку на визу кочевника"))