from pathlib import Path
import sys
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.services.rag_service import rag_service

if __name__ == "__main__":
    count = rag_service.rebuild_index()
    print(f"Indexed {count} NeedYield resource documents in backend/chroma_db.")
