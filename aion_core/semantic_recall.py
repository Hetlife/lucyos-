"""Optional local semantic recall over a rebuildable sqlite-vec index.

Canonical memory remains in AION SQLite/FTS. This module creates a derived local
index only when explicitly requested and degrades cleanly when optional packages
or model files are unavailable.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from . import config, db, util

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


def dependency_status() -> dict:
    try:
        import sqlite_vec  # noqa: F401
        sqlite_ok = True
    except Exception:
        sqlite_ok = False
    try:
        import fastembed  # noqa: F401
        embed_ok = True
    except Exception:
        embed_ok = False
    return {"sqlite_vec": sqlite_ok, "fastembed": embed_ok, "ready": sqlite_ok and embed_ok}


def index_path() -> Path:
    p = config.home() / "state" / "derived" / "semantic_memory.sqlite3"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def model_cache() -> Path:
    p = config.home() / "state" / "models" / "fastembed"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _load_deps():
    import sqlite_vec
    from fastembed import TextEmbedding
    return sqlite_vec, TextEmbedding


def _embedder(model_name: str, cache_dir: Path, *, allow_download: bool):
    _, TextEmbedding = _load_deps()
    if not allow_download and not any(cache_dir.iterdir()):
        raise RuntimeError("FastEmbed model cache is empty; explicit prefetch/allow_download required")
    model = TextEmbedding(model_name=model_name, cache_dir=str(cache_dir))
    return lambda texts: list(model.embed(texts))


def rebuild(*, model_name: str = DEFAULT_MODEL, path: Path | None = None,
            cache_dir: Path | None = None, allow_download: bool = False,
            embed=None) -> dict:
    """Rebuild the derived memory vector index from canonical SQLite memory."""
    sqlite_vec, _ = _load_deps()
    rows = db.connect().execute(
        "SELECT memory_id, kind, title, body FROM memory ORDER BY rowid"
    ).fetchall()
    target = path or index_path()
    cache = cache_dir or model_cache()
    if embed is None:
        embed = _embedder(model_name, cache, allow_download=allow_download)
    texts = [f"{r['title']}\n{r['body']}" for r in rows]
    vectors = list(embed(texts)) if texts else []
    dimension = len(vectors[0]) if vectors else 0
    tmp = target.with_suffix(target.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    conn = sqlite3.connect(tmp)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("CREATE TABLE items(rowid INTEGER PRIMARY KEY, memory_id TEXT UNIQUE, kind TEXT, title TEXT, body_hash TEXT)")
    if dimension:
        conn.execute(f"CREATE VIRTUAL TABLE vectors USING vec0(embedding float[{dimension}])")
        for i, (row, vec) in enumerate(zip(rows, vectors), 1):
            body_hash = hashlib.sha256((row['body'] or '').encode()).hexdigest()
            conn.execute("INSERT INTO items(rowid,memory_id,kind,title,body_hash) VALUES(?,?,?,?,?)",
                         (i, row['memory_id'], row['kind'], row['title'], body_hash))
            conn.execute("INSERT INTO vectors(rowid,embedding) VALUES(?,?)",
                         (i, sqlite_vec.serialize_float32(vec)))
    conn.executemany("INSERT INTO metadata(key,value) VALUES(?,?)", [
        ("model", model_name), ("dimension", str(dimension)), ("built_at", util.now()),
        ("count", str(len(rows))), ("canonical", "AION memory SQLite")])
    conn.commit(); conn.close()
    tmp.replace(target)
    return {"ok": True, "count": len(rows), "dimension": dimension,
            "model": model_name, "path": str(target), "derived": True}


def search(query: str, *, limit: int = 5, path: Path | None = None,
           cache_dir: Path | None = None, allow_download: bool = False,
           embed=None) -> list[dict]:
    if not query.strip() or limit <= 0:
        return []
    sqlite_vec, _ = _load_deps()
    target = path or index_path()
    if not target.exists():
        raise RuntimeError("semantic index missing; rebuild it first")
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True); sqlite_vec.load(conn)
    meta = {r["key"]: r["value"] for r in conn.execute("SELECT key,value FROM metadata")}
    if not int(meta.get("dimension", "0")):
        conn.close(); return []
    if embed is None:
        embed = _embedder(meta.get("model", DEFAULT_MODEL), cache_dir or model_cache(),
                          allow_download=allow_download)
    vector = list(embed([query]))[0]
    rows = conn.execute(
        "SELECT i.memory_id,i.kind,i.title,v.distance FROM vectors v JOIN items i ON i.rowid=v.rowid "
        "WHERE v.embedding MATCH ? AND k=? ORDER BY v.distance",
        (sqlite_vec.serialize_float32(vector), int(limit))).fetchall()
    conn.close()
    return [dict(r) for r in rows]
