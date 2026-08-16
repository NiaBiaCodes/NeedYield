import json
import math
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from langchain_core.documents import Document

from app.models.rag import RagQuery, RagRecommendation, RagResponse, RagSource
from app.services.embedding_service import embedding_service
from app.services.location_service import location_service

NYC_DATA_URL = "https://data.cityofnewyork.us/d/r3dx-pew9"
PRODUCE = {"tomato": "tomatoes", "tomatoes": "tomatoes", "cucumber": "cucumbers", "cucumbers": "cucumbers", "zucchini": "zucchini", "kale": "kale", "spinach": "spinach", "pepper": "peppers", "peppers": "peppers", "carrot": "carrots", "carrots": "carrots", "herb": "herbs", "herbs": "herbs", "vegetable": "vegetables", "vegetables": "vegetables"}


class RagService:
    def __init__(self) -> None:
        self.path = Path(__file__).resolve().parents[2] / "chroma_db"
        self.collection_name = "needyield_resources"

    def documents(self) -> list[Document]:
        documents = []
        for item in location_service.all():
            inventory = ", ".join(f"{name}: {quantity}" for name, quantity in item.inventory.items() if quantity > 0) or "none currently"
            content = (
                f"{item.name} is a {'demo ' if item.demo else ''}food resource in {item.neighborhood}, {item.borough}. "
                f"It is located at {item.address}. Pickup hours are {item.opening_time} to {item.closing_time}. "
                f"It accepts {', '.join(item.accepted_categories)}. Saturday pickup is {'available' if item.accepts_saturday else 'not available'}. "
                f"Current produce inventory includes {inventory}. Community context is informed by {item.community_need_source}."
            )
            documents.append(Document(page_content=content, metadata={
                "resource_id": item.id, "name": item.name, "borough": item.borough, "neighborhood": item.neighborhood,
                "latitude": item.latitude, "longitude": item.longitude, "opening_time": item.opening_time,
                "closing_time": item.closing_time, "source": "NeedYield demo resource + NYC Open Data community context",
                "source_url": NYC_DATA_URL, "verified_partner": item.verified_partner, "demo": item.demo,
            }))
        return documents

    def rebuild_index(self) -> int:
        import chromadb
        documents = self.documents()
        client = chromadb.PersistentClient(path=str(self.path))
        try: client.delete_collection(self.collection_name)
        except Exception: pass
        embeddings = embedding_service.embed_documents([item.page_content for item in documents])
        collection = client.create_collection(self.collection_name, metadata={"embedding_provider": embedding_service.provider, "embedding_dimension": embedding_service.dimension})
        collection.add(ids=[item.metadata["resource_id"] for item in documents], documents=[item.page_content for item in documents], metadatas=[item.metadata for item in documents], embeddings=embeddings)
        return len(documents)

    def _retrieve(self, query: str, count: int = 4) -> tuple[list[Document], str]:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(self.path))
            try: collection = client.get_collection(self.collection_name)
            except Exception:
                self.rebuild_index(); collection = client.get_collection(self.collection_name)
            query_embedding = embedding_service.embed_query(query)
            try:
                result = collection.query(query_embeddings=[query_embedding], n_results=count, include=["documents", "metadatas"])
            except Exception:
                self.rebuild_index(); collection = client.get_collection(self.collection_name)
                result = collection.query(query_embeddings=[embedding_service.embed_query(query)], n_results=count, include=["documents", "metadatas"])
            docs = [Document(page_content=text, metadata=metadata) for text, metadata in zip(result["documents"][0], result["metadatas"][0])]
            return docs, embedding_service.provider
        except Exception:
            return self.documents()[:count], "structured-fallback"

    @staticmethod
    def _distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius = 3958.8; p1, p2 = math.radians(lat1), math.radians(lat2); dp = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _minutes(value: str) -> int:
        parsed = datetime.strptime(value, "%I:%M %p"); return parsed.hour * 60 + parsed.minute

    def _recommendations(self, payload: RagQuery, docs: list[Document]) -> list[RagRecommendation]:
        query = payload.query.lower(); requested = {canonical for token, canonical in PRODUCE.items() if re.search(rf"\b{re.escape(token)}\b", query)}
        wants_vegetables = "vegetables" in requested; requested.discard("vegetables")
        after_five = bool(re.search(r"after (5|five)|later|after work|evening", query)); saturday = "saturday" in query
        ranked = []
        for order, doc in enumerate(docs):
            location = location_service.get(doc.metadata["resource_id"])
            if not location or not location.verified_partner or not location.participating: continue
            available = {name: qty for name, qty in location.inventory.items() if qty > 0 and (not requested or name in requested)}
            if requested and not available: continue
            if wants_vegetables and not available: available = {name: qty for name, qty in location.inventory.items() if qty > 0}
            if not available: continue
            if after_five and self._minutes(location.closing_time) <= 17 * 60: continue
            if saturday and not location.accepts_saturday: continue
            distance = self._distance(payload.latitude, payload.longitude, location.latitude, location.longitude) if payload.latitude is not None and payload.longitude is not None else None
            reasons = [f"{', '.join(name.title() for name in available)} currently available", f"Open until {location.closing_time}"]
            if saturday: reasons.append("Saturday pickup is available")
            if distance is not None: reasons.append(f"Approximately {distance:.1f} miles away")
            score = order + (distance or 0) * .15 - min(sum(available.values()), 50) * .01
            ranked.append((score, RagRecommendation(resource_id=location.id, name=location.name, address=location.address, neighborhood=location.neighborhood, borough=location.borough, hours=f"{location.opening_time}–{location.closing_time}", available_inventory=available, distance_miles=round(distance, 1) if distance is not None else None, reasons=reasons)))
        return [item for _, item in sorted(ranked, key=lambda row: row[0])[:3]]

    def _generate(self, query: str, recommendations: list[RagRecommendation], docs: list[Document]) -> tuple[str, str]:
        if not recommendations:
            return "I couldn't find a current inventory match for that request. Try another food or browse Find Food for all available demo inventory.", "deterministic-fallback"
        context = "\n".join(doc.page_content for doc in docs)
        structured = json.dumps([item.model_dump() for item in recommendations])
        if os.getenv("GEMINI_API_KEY"):
            try:
                from google import genai
                client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
                response = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"), contents=f"Answer the resident's question using only the retrieved context and verified current options. Clearly label demo locations. Be concise, use plain text without Markdown, and never invent inventory, hours, or distance.\nQuestion: {query}\nRetrieved context:\n{context}\nVerified options:\n{structured}")
                if response.text: return response.text.strip(), "gemini-grounded"
            except Exception: pass
        best = recommendations[0]
        return f"Your best current option is {best.name}, a demo location in {best.neighborhood}. " + " ".join(best.reasons) + ". You can reserve available produce on Find Food.", "deterministic-grounded"

    def query(self, payload: RagQuery) -> RagResponse:
        docs, retrieval_mode = self._retrieve(payload.query)
        recommendations = self._recommendations(payload, docs)
        answer, generation_mode = self._generate(payload.query, recommendations, docs)
        sources = [RagSource(resource_id=doc.metadata["resource_id"], name=doc.metadata["name"], source=doc.metadata["source"], source_url=doc.metadata.get("source_url")) for doc in docs]
        return RagResponse(answer=answer, recommendations=recommendations, sources=sources, retrieved_count=len(docs), retrieval_mode=retrieval_mode, generation_mode=generation_mode, fallback=retrieval_mode == "structured-fallback" or generation_mode != "gemini-grounded")


rag_service = RagService()
