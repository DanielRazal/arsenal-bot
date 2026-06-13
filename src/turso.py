"""Minimal synchronous Turso (libSQL) client over the HTTP /v2/pipeline API.

Why HTTP and not the libsql driver: the official libsql-experimental driver
ships no wheels for some platforms and needs a Rust toolchain to build. The
HTTP pipeline API needs nothing but httpx (already a dependency) and works
everywhere, which also lets us verify locally.

This exposes just the slice of the sqlite3 interface that src/db.py uses:
a connection with execute()/executescript()/commit()/close(), and cursors
whose rows support both named (row["col"]) and positional (row[0]) access plus
dict(row) — matching sqlite3.Row, so db.py needs no other changes.
"""
import logging

import httpx

log = logging.getLogger(__name__)


class _Row:
    """sqlite3.Row-like: supports row["col"], row[0], and dict(row)."""

    __slots__ = ("_cols", "_vals")

    def __init__(self, cols: list[str], vals: list) -> None:
        self._cols = cols
        self._vals = vals

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._vals[key]
        return self._vals[self._cols.index(key)]

    def keys(self):
        return self._cols


class _Cursor:
    def __init__(self, rows: list[_Row], rowcount: int) -> None:
        self._rows = rows
        self.rowcount = rowcount

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def __iter__(self):
        return iter(self._rows)


def _to_arg(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "integer", "value": str(int(value))}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    return {"type": "text", "value": str(value)}


def _from_cell(cell: dict):
    t = cell.get("type")
    v = cell.get("value")
    if t == "null":
        return None
    if t == "integer":
        return int(v)
    if t == "float":
        return float(v)
    return v  # text / blob handled as-is


def _split_statements(script: str) -> list[str]:
    out = []
    for chunk in script.split(";"):
        # Drop comment-only / blank fragments (the pipeline rejects empty SQL).
        body = "\n".join(
            ln for ln in chunk.splitlines() if ln.strip() and not ln.strip().startswith("--")
        ).strip()
        if body:
            out.append(body)
    return out


class TursoConnection:
    """Connection-shaped wrapper over Turso's HTTP pipeline (auto-commit)."""

    def __init__(self, url: str, auth_token: str) -> None:
        endpoint = url.replace("libsql://", "https://").rstrip("/")
        self._endpoint = endpoint + "/v2/pipeline"
        self._headers = {"Authorization": f"Bearer {auth_token}"}
        self.row_factory = None  # accepted for sqlite3 parity; ignored

    def _pipeline(self, statements: list[dict]) -> list[dict]:
        requests = [{"type": "execute", "stmt": s} for s in statements]
        requests.append({"type": "close"})
        resp = httpx.post(self._endpoint, headers=self._headers, json={"requests": requests}, timeout=20.0)
        resp.raise_for_status()
        results = resp.json()["results"]
        for r in results:
            if r.get("type") == "error":
                raise RuntimeError(f"Turso error: {r.get('error')}")
        return results

    def execute(self, sql: str, params=()) -> _Cursor:
        stmt = {"sql": sql}
        if params:
            stmt["args"] = [_to_arg(p) for p in params]
        result = self._pipeline([stmt])[0]["response"]["result"]
        cols = [c["name"] for c in result.get("cols", [])]
        rows = [_Row(cols, [_from_cell(c) for c in row]) for row in result.get("rows", [])]
        return _Cursor(rows, result.get("affected_row_count", 0) or 0)

    def executescript(self, script: str) -> None:
        stmts = [{"sql": s} for s in _split_statements(script)]
        if stmts:
            self._pipeline(stmts)

    def commit(self) -> None:  # pipeline auto-commits each call
        pass

    def close(self) -> None:
        pass
