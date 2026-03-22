import os
import re
from pathlib import Path
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import uuid
import time
from tqdm import tqdm

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-large"  # dim 1024
CHUNK_SIZE    = 960
CHUNK_OVERLAP = 160

KNOWLEDGE_DIR = Path("backend/data/knowledge")

client   = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)


def get_country_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    if "_all_sources" in stem:
        return stem.replace("_all_sources", "")
    return "unknown"


def create_or_reset_collection(collection_name: str, recreate: bool = False):
    exists = client.collection_exists(collection_name)

    if recreate and exists:
        client.delete_collection(collection_name)
        print(f" → Удалена коллекция: {collection_name}")
        time.sleep(1.2)
        exists = False

    if not exists:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
        )
        print(f" → Создана коллекция: {collection_name}")
    else:
        print(f" → Используется существующая коллекция: {collection_name}")


def split_by_sources(md_path: Path):
    if not md_path.exists():
        print(f"Файл не найден → пропуск: {md_path}")
        return []

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    first_source_pos = content.find('## Источник:')
    if first_source_pos != -1:
        content = content[first_source_pos:]

    sections = re.split(r'(?=^## Источник:)', content, flags=re.MULTILINE)

    all_chunks = []
    current_meta = {}

    for section in sections:
        section = section.strip()
        if not section:
            continue

        header_match = re.match(
            r'^## Источник:\s*(.+?)\n'
            r'source_url:\s*(.+?)\n'
            r'(?:country:\s*(.+?)\n)?'
            r'(?:date_fetched:\s*(.+?)\n)?',
            section,
            flags=re.MULTILINE | re.DOTALL
        )

        if header_match:
            source_name  = header_match.group(1).strip()
            source_url   = header_match.group(2).strip()
            country      = header_match.group(3).strip() if header_match.group(3) else None
            date_fetched = header_match.group(4).strip() if header_match.group(4) else datetime.now().strftime("%Y-%m-%d")

            current_meta = {
                "source_name": source_name,
                "source_url": source_url,
                "country": country or get_country_from_filename(md_path.name),
                "date_fetched": date_fetched,
                "file": md_path.name,
            }

            text_part = re.sub(
                r'^## Источник:.*?(?:\ncountry:.*?\n)?(?:date_fetched:.*?\n)?\n*',
                '', section, flags=re.DOTALL | re.MULTILINE
            ).strip()
        else:
            text_part = section.strip()

        if not text_part:
            continue

        start = 0
        while start < len(text_part):
            end = min(start + CHUNK_SIZE, len(text_part))
            chunk_text = text_part[start:end].strip()

            if len(chunk_text) < 80:
                start += CHUNK_SIZE - CHUNK_OVERLAP
                continue

            payload = {
                "text": chunk_text,
                **current_meta
            }

            all_chunks.append({
                "payload": payload,
                "text_for_embedding": chunk_text
            })

            start += CHUNK_SIZE - CHUNK_OVERLAP

    print(f" → Извлечено чанков: {len(all_chunks):,} из {md_path.name}")
    return all_chunks


def upload_chunks(chunks, collection_name, batch_size=48):
    if not chunks:
        return

    texts = [c["text_for_embedding"] for c in chunks]

    for i in tqdm(range(0, len(texts), batch_size), desc=f"Загрузка в {collection_name}"):
        batch_texts = texts[i:i + batch_size]
        batch_items = chunks[i:i + batch_size]

        vectors = embedder.encode(
            batch_texts,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        points = []
        for j, item in enumerate(batch_items):
            point_id = str(uuid.uuid4())
            points.append(PointStruct(
                id=point_id,
                vector=vectors[j].tolist(),
                payload=item["payload"]
            ))

        client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True
        )


def main(countries=None, recreate_collections=False):
    if countries is None:
        md_files = list(KNOWLEDGE_DIR.glob("*_all_sources.md"))
    else:
        md_files = [KNOWLEDGE_DIR / f"{c}_all_sources.md" for c in countries]
        md_files = [f for f in md_files if f.exists()]

    if not md_files:
        print("Не найдено ни одного файла *_all_sources.md")
        return

    print(f"Обнаружено файлов для обработки: {len(md_files)}")

    for md_path in md_files:
        country = get_country_from_filename(md_path.name)
        collection_name = f"travel_rules_{country}"

        print(f"\n{'═'*60}\nОбрабатываем страну: {country.upper()} → коллекция: {collection_name}")

        create_or_reset_collection(collection_name, recreate=recreate_collections)

        chunks = split_by_sources(md_path)
        if not chunks:
            continue

        upload_chunks(chunks, collection_name)


if __name__ == "__main__":
    main()