import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from langchain_community.vectorstores.chroma import Chroma

from agents.connectors.news_mcp_adapter import News


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        return float(str(value))
    except Exception:
        return default


class NewsRAG:
    """
    Minimal news RAG: ingest from MCP adapter, index in Chroma, query and link to markets.
    - Embeddings backend selected via env RAG_EMBEDDINGS (default: fake; 'openai' to enable OpenAI)
    - Persist directory configurable via env NEWS_RAG_DIR (default: ./local_news_db)
    """

    def __init__(self, persist_directory: Optional[str] = None) -> None:
        self.persist_directory = (
            persist_directory or os.getenv("NEWS_RAG_DIR", "/tmp/local_news_db")
        )
        # By default avoid disk writes (ephemeral, in-memory)
        self._persist_enabled = os.getenv("RAG_PERSIST", "false").lower() == "true"
        self.embedding_function = self._get_default_embeddings()
        self.news_client = News()

    def _get_default_embeddings(self) -> Any:
        choice = os.getenv("RAG_EMBEDDINGS", "fake").lower()
        if choice == "openai":
            try:
                from openai import OpenAI

                class OpenAIEmbeddingAdapter:
                    def __init__(self, model: str = "text-embedding-3-small") -> None:
                        self.client = OpenAI()
                        self.model = model

                    def embed_documents(self, texts: List[str]) -> List[List[float]]:
                        response = self.client.embeddings.create(
                            model=self.model, input=texts
                        )
                        return [d.embedding for d in response.data]

                    def embed_query(self, text: str) -> List[float]:
                        response = self.client.embeddings.create(
                            model=self.model, input=[text]
                        )
                        return response.data[0].embedding

                return OpenAIEmbeddingAdapter()
            except Exception:
                pass
        from langchain_community.embeddings import FakeEmbeddings
        return FakeEmbeddings(size=1536)

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _md5(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            v = value
            if v.endswith("Z"):
                v = v.replace("Z", "+00:00")
            return datetime.fromisoformat(v)
        except Exception:
            return None

    @staticmethod
    def _simple_chunks(text: str, chunk_size: int = 4000, overlap: int = 400) -> List[str]:
        if not text:
            return []
        chunks: List[str] = []
        start = 0
        n = len(text)
        while start < n:
            end = min(n, start + chunk_size)
            chunks.append(text[start:end])
            if end == n:
                break
            start = end - overlap
            if start < 0:
                start = 0
        return chunks

    def _ensure_dir(self, path: str) -> None:
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)

    def _get_chroma(self) -> Chroma:
        """Returns a Chroma vectorstore. If RAG_PERSIST is not enabled, use in-memory client (no writes)."""
        try:
            if not self._persist_enabled:
                # In-memory client with telemetry disabled
                from chromadb.config import Settings as _Settings  # type: ignore
                from chromadb import Client as _Client  # type: ignore
                client = _Client(_Settings(is_persistent=False, anonymized_telemetry=False))
                return Chroma(
                    client=client,
                    collection_name="news_inmemory",
                    embedding_function=self.embedding_function,
                )
        except Exception:
            # Fall back to default persistent behavior if in-memory client not available
            pass
        # Persistent vectorstore (may write to disk)
        return Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embedding_function,
        )

    def ingest_news(
        self,
        days: int = 14,
        max_items: int = 300,
        keywords_csv: str = "",
    ) -> int:
        """
        Fetch news from MCP adapter and index into Chroma as full-text chunks.
        Returns number of indexed chunks.
        """
        self._ensure_dir(self.persist_directory)

        # Collect articles from MCP (Verge News) and adapter fallback
        articles: List[Dict[str, Any]] = []
        # Prefer direct Verge News MCP
        try:
            from agents.connectors.verge_news_mcp import VergeNewsMCPSync
            verge = VergeNewsMCPSync()
            try:
                daily = verge.get_daily_news()
                if isinstance(daily, list):
                    articles.extend(daily)
            except Exception:
                pass
            for kw in [k.strip() for k in keywords_csv.split(",") if k.strip()]:
                try:
                    res = verge.search_news(kw, days_back=days)
                    if isinstance(res, list):
                        articles.extend(res)
                except Exception:
                    pass
        except Exception:
            # Fallback: use adapter generic interface if available
            try:
                daily = getattr(self.news_client, "get_daily_news", lambda: [])()
                if isinstance(daily, list):
                    articles.extend(daily)
            except Exception:
                pass
            for kw in [k.strip() for k in keywords_csv.split(",") if k.strip()]:
                try:
                    res = getattr(self.news_client, "get_articles_for_cli_keywords", lambda *_: [])(kw)
                    if isinstance(res, list):
                        # Convert Pydantic Articles to dicts if needed
                        items: List[Dict[str, Any]] = []
                        for it in res:
                            try:
                                items.append(it.dict())  # type: ignore[attr-defined]
                            except Exception:
                                items.append(it)
                        articles.extend(items)
                except Exception:
                    pass

        # Normalize and dedupe by url_hash
        seen: set[str] = set()
        normalized: List[Dict[str, Any]] = []
        now = self._now_utc()
        for a in articles:
            title = a.get("title") or ""
            desc = a.get("description") or ""
            content = a.get("content") or ""
            url = a.get("url") or ""
            if not url and not (title or desc or content):
                continue
            url_hash = self._md5(url or title + desc)
            if url_hash in seen:
                continue
            seen.add(url_hash)
            published_at = a.get("published_at") or a.get("publishedAt") or ""
            source = a.get("source") or ""
            if isinstance(source, dict):
                source = source.get("name") or source.get("id") or ""
            text = "\n\n".join([title, desc, content]).strip()
            normalized.append(
                {
                    "url": url,
                    "url_hash": url_hash,
                    "title": title,
                    "description": desc,
                    "content": content,
                    "published_at": published_at,
                    "source": source,
                    "fetched_at": now.isoformat(),
                    "text": text,
                }
            )

        # Limit items
        if len(normalized) > max_items:
            normalized = normalized[:max_items]

        # Index as chunks
        docs: List[Tuple[str, Dict[str, Any]]] = []
        for n in normalized:
            chunks = self._simple_chunks(n["text"])
            for idx, ch in enumerate(chunks):
                meta = {
                    "url": n["url"],
                    "url_hash": n["url_hash"],
                    "title": n["title"],
                    "published_at": n["published_at"],
                    "source": n["source"],
                    "chunk_index": idx,
                    "chunks_total": len(chunks),
                }
                docs.append((ch, meta))

        if not docs:
            return 0

        # Store via Chroma add_texts
        chroma = self._get_chroma()
        texts = [t for t, _ in docs]
        metadatas = [m for _, m in docs]
        chroma.add_texts(texts=texts, metadatas=metadatas)
        # Persist only if explicitly enabled
        try:
            if self._persist_enabled and hasattr(chroma, "persist"):
                chroma.persist()
        except Exception:
            pass
        return len(texts)

    def query_news(self, query: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        chroma = self._get_chroma()
        results = chroma.similarity_search_with_score(query=query, k=top_k)
        formatted: List[Tuple[Dict[str, Any], float]] = []
        for doc, score in results:
            meta = dict(doc.metadata or {})
            meta["snippet"] = (doc.page_content or "")[:240]
            formatted.append((meta, _safe_float(score, 0.0)))
        return formatted

    def link_news_to_markets(
        self,
        markets_persist_dir: str = "./local_db",
        top_k: int = 10,
        min_relevance: float = 0.6,
        half_life_days: float = 5.0,
        output_path: str = "./news_market_links.json",
    ) -> str:
        """
        For each news chunk, find top similar market docs and emit links JSON.
        Returns path to the JSON file.
        """
        # Prepare vectorstores
        news_vs = self._get_chroma()
        from langchain_community.vectorstores.chroma import Chroma as _Chroma
        markets_vs = _Chroma(
            persist_directory=markets_persist_dir, embedding_function=self.embedding_function
        )

        # Heuristic: iterate through news collection items via a keyword list
        # Chroma doesn't expose raw iteration; we query using a broad term and dedupe
        seeds = ["news", "market", "crypto", "election", "court", "ai", "stocks"]
        seen_hashes: set[str] = set()
        links: Dict[str, Dict[str, Any]] = {}
        now = self._now_utc()

        for seed in seeds:
            results = news_vs.similarity_search_with_score(query=seed, k=50)
            for doc, _ in results:
                url_hash = (doc.metadata or {}).get("url_hash")
                if not url_hash or url_hash in seen_hashes:
                    continue
                seen_hashes.add(url_hash)

                # Build query from news doc
                q = "\n\n".join([
                    (doc.metadata or {}).get("title", ""),
                    doc.page_content or "",
                ])[:2000]
                market_hits = markets_vs.similarity_search_with_score(q, k=top_k)

                # Compute time decay
                pub = (doc.metadata or {}).get("published_at")
                pub_dt = self._parse_dt(pub)
                age_days = 0.0
                if pub_dt is not None:
                    try:
                        age_days = max(
                            0.0,
                            (now - pub_dt.astimezone(timezone.utc)).total_seconds() / 86400.0,
                        )
                    except Exception:
                        age_days = 0.0
                decay = 1.0
                if half_life_days > 0:
                    import math

                    decay = math.exp(-age_days / half_life_days)

                linked: List[Dict[str, Any]] = []
                for mdoc, score in market_hits:
                    # Convert distance score (smaller is better in some backends) to similarity-like
                    sim = max(0.0, 1.0 - _safe_float(score, 0.0))
                    rel = 0.8 * sim + 0.2 * decay
                    if rel < min_relevance:
                        continue
                    linked.append(
                        {
                            "market_source": (mdoc.metadata or {}).get("source"),
                            "market_id": (mdoc.metadata or {}).get("id"),
                            "question": (mdoc.metadata or {}).get("question"),
                            "rel": rel,
                        }
                    )

                if not linked:
                    continue
                linked.sort(key=lambda x: x["rel"], reverse=True)
                links[url_hash] = {
                    "title": (doc.metadata or {}).get("title"),
                    "url": (doc.metadata or {}).get("url"),
                    "published_at": (doc.metadata or {}).get("published_at"),
                    "source": (doc.metadata or {}).get("source"),
                    "top_markets": linked,
                }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(links, f, ensure_ascii=False, indent=2)
        return output_path


