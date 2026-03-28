"""Fieldlink entity resolver.

Resolves dot-notation entity IDs (SHAPE.ICOSA, EMOTION.FEAR, etc.) against
fieldlinked sibling repos, either from local clones or .fieldcache/.

Usage:
    resolver = FieldlinkResolver("path/to/.fieldlink.json")
    shape = resolver.resolve("SHAPE.ICOSA")
    bridge = resolver.resolve_bridge("SHAPE.ICOSA")
"""
from __future__ import annotations

import json
import pathlib
import subprocess
from typing import Any

# ---------------------------------------------------------------------------
# Namespace → fieldlink source mapping
# ---------------------------------------------------------------------------

# Which fieldlink source owns each namespace prefix.
# The resolver uses this to know where to look for an entity.
NAMESPACE_SOURCE = {
    "SHAPE": "rosetta",
    "EMOTION": "emotions",
    "DEFENSE": "defense",
    "AUDIT": "audit",
    "CONST": "rosetta",
    "SEED": "resilience",
    "RESILIENCE": "resilience",
    "SUBSTRATE": "resilience",
    "SHADOW": "shadow-hunting",
}

# Within a source, how to find the file for a given namespace.
# Returns (glob_pattern, id_field) — the resolver scans matching files for
# a JSON object whose id_field equals the requested entity ID.
NAMESPACE_LOOKUP = {
    "SHAPE": ("shapes/**/*.json", "id"),
}

# Friendly name → shape filename stem (for direct file lookup)
_SHAPE_FILE_MAP = {
    "SHAPE.TETRA": "tetrahedron",
    "SHAPE.CUBE": "cube",
    "SHAPE.OCTA": "octahedron",
    "SHAPE.DODECA": "dodecahedron",
    "SHAPE.ICOSA": "icosahedron",
}


class FieldlinkResolver:
    """Resolve entity IDs against fieldlinked repos."""

    def __init__(
        self,
        fieldlink_path: str | pathlib.Path,
        cache_dir: str | pathlib.Path | None = None,
        clone_base: str | pathlib.Path | None = None,
    ):
        fieldlink_path = pathlib.Path(fieldlink_path)
        self.root = fieldlink_path.parent
        raw = json.loads(fieldlink_path.read_text(encoding="utf-8"))
        self.config = raw["fieldlink"]
        self.sources: dict[str, dict] = {
            s["name"]: s for s in self.config["sources"]
        }

        # Where to find local clones: explicit clone_base, then .fieldcache
        self.cache_dir = pathlib.Path(
            cache_dir or self.root / self.config.get("cache_dir", ".fieldcache")
        )
        self.clone_base = pathlib.Path(clone_base) if clone_base else None

        # In-memory cache of resolved entities
        self._cache: dict[str, Any] = {}
        # Bridge data (loaded once)
        self._bridges: list[dict] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, entity_id: str) -> dict | None:
        """Resolve an entity ID to its full JSON definition.

        Example: resolve("SHAPE.ICOSA") → {id, name, faces, edges, ...}
        """
        if entity_id in self._cache:
            return self._cache[entity_id]

        namespace = entity_id.split(".")[0]
        source_name = NAMESPACE_SOURCE.get(namespace)
        if not source_name:
            return None

        source_root = self._find_source_root(source_name)
        if not source_root:
            return None

        result = self._lookup_entity(entity_id, namespace, source_root)
        if result:
            self._cache[entity_id] = result
        return result

    def resolve_bridge(self, shape_id: str) -> dict | None:
        """Resolve a shape's bridge data (sensors, defenses, protocols).

        Returns the bridge entry from rosetta-bridges.json for the given shape.
        """
        bridges = self._load_bridges()
        if not bridges:
            return None
        for entry in bridges:
            if entry.get("shape") == shape_id:
                return entry
        return None

    def resolve_all(self, entity_ids: list[str]) -> dict[str, dict | None]:
        """Resolve multiple entity IDs. Returns {id: data_or_None}."""
        return {eid: self.resolve(eid) for eid in entity_ids}

    def ensure_source(self, source_name: str) -> pathlib.Path | None:
        """Ensure a source repo is available locally. Clone if needed."""
        existing = self._find_source_root(source_name)
        if existing:
            return existing

        source = self.sources.get(source_name)
        if not source:
            return None

        dest = self.cache_dir / source_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        repo_url = source["repo"]
        ref = source.get("ref", "main")

        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", ref,
                 repo_url, str(dest)],
                capture_output=True, text=True, check=True, timeout=60,
            )
            return dest
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _find_source_root(self, source_name: str) -> pathlib.Path | None:
        """Find the local root directory for a fieldlink source."""
        # Check explicit clone base (e.g. /tmp/)
        if self.clone_base:
            for candidate_name in self._source_dir_names(source_name):
                p = self.clone_base / candidate_name
                if p.is_dir():
                    return p

        # Check .fieldcache/
        p = self.cache_dir / source_name
        if p.is_dir():
            return p

        return None

    def _source_dir_names(self, source_name: str) -> list[str]:
        """Possible directory names for a source (repo name variations)."""
        source = self.sources.get(source_name, {})
        repo_url = source.get("repo", "")
        repo_name = repo_url.rstrip("/").rsplit("/", 1)[-1] if repo_url else ""
        return [repo_name, source_name]

    def _lookup_entity(
        self, entity_id: str, namespace: str, source_root: pathlib.Path
    ) -> dict | None:
        """Find an entity's JSON data within a source repo."""
        # Fast path: direct file lookup for shapes
        if namespace == "SHAPE" and entity_id in _SHAPE_FILE_MAP:
            stem = _SHAPE_FILE_MAP[entity_id]
            for ext in (".json",):
                path = source_root / "shapes" / f"{stem}{ext}"
                if path.is_file():
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if data.get("id") == entity_id:
                        return data

        # Fallback: scan namespace lookup patterns
        lookup = NAMESPACE_LOOKUP.get(namespace)
        if lookup:
            pattern, id_field = lookup
            for path in source_root.glob(pattern):
                if not path.is_file():
                    continue
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if isinstance(data, dict) and data.get(id_field) == entity_id:
                    return data

        return None

    def _load_bridges(self) -> list[dict]:
        """Load rosetta-bridges.json (bridge map)."""
        if self._bridges is not None:
            return self._bridges

        rosetta_root = self._find_source_root("rosetta")
        if not rosetta_root:
            self._bridges = []
            return self._bridges

        bridge_path = rosetta_root / "bridges" / "rosetta-bridges.json"
        if not bridge_path.is_file():
            self._bridges = []
            return self._bridges

        data = json.loads(bridge_path.read_text(encoding="utf-8"))
        self._bridges = data.get("map", [])
        return self._bridges
