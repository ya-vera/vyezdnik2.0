backend/
├── data/
│   ├── knowledge/              # ← сюда Markdown с правилами (твой главный контент)
│   │   ├── thailand_all_sources.md          # ← главный файл на MVP
│   └── metadata/
│       └── countries.json       # ← точные ссылки и данные для Агента по документам
├── scripts/
│   └── ingest.py                # ← твой главный скрипт (я дам ниже)
        parsing.py
├── .env                         # ← для ключа OpenAI
