from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

client = QdrantClient(host="localhost", port=6333)
embedder = SentenceTransformer("intfloat/multilingual-e5-large")

query_text = "TDAC для ребёнка как заполнить"
query_vector = embedder.encode(query_text).tolist()

print(f"Запрос: {query_text}")
print(f"Размер вектора: {len(query_vector)} (должен быть 1024)\n")

hits = client.query_points(
    collection_name="travel_rules_thailand",
    query=query_vector,
    limit=5,
    with_payload=True,
    query_filter=Filter(
        must=[FieldCondition(key="country", match=MatchValue(value="thailand"))]
    ),
)

print("Найденные чанки (score > 0.7):")
for i, point in enumerate(hits.points, 1):
    score = point.score
    if score < 0.7:
        continue
    print(f"\n{i}. Score: {score:.4f}")
    print(f"   Source: {point.payload.get('source_name', '—')}")
    print(f"   URL:    {point.payload.get('source_url', '—')}")
    print(f"   Текст:  {point.payload.get('text', '')[:300].replace('\n', ' ')} ...")