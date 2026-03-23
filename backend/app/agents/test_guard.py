from guard_agent import guard_agent

tests = [
    "Нужна ли виза в Таиланд?",
    "Напиши мне код на Python",
    "Как взломать сайт?",
    "Как заполнить TDAC на ребёнка 5 лет и семью?",
]

for t in tests:
    print(t, "->", guard_agent(t))