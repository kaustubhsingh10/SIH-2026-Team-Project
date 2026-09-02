"""Dataset loader and serializer for CrimeGraph AI."""

from pathlib import Path
from typing import Optional, Union
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.data.generator import generate_synthetic_investigation_data


def get_default_dataset_path() -> Path:
    """Returns default path to data/synthetic_data.json relative to repository root."""
    # Find root by ascending from current file
    cur = Path(__file__).resolve().parent
    for _ in range(4):
        if (cur / "PROJECT_SPEC.md").exists() or (cur / ".git").exists():
            return cur / "data" / "synthetic_data.json"
        cur = cur.parent
    return Path("data") / "synthetic_data.json"


def load_dataset(filepath: Optional[Union[str, Path]] = None, allow_generate: bool = True) -> KnowledgeGraphStore:
    """Loads knowledge graph from a JSON file. If file does not exist, raises FileNotFoundError in production or generates synthetic data in dev."""
    import os
    path = Path(filepath) if filepath else get_default_dataset_path()

    if not path.exists():
        env = os.getenv("CRIMEGRAPH_ENV", os.getenv("NODE_ENV", "development")).lower()
        if env == "production" or not allow_generate:
            raise FileNotFoundError(f"Canonical dataset file not found at {path}. Automatic generation disabled in production environment.")
        store = generate_synthetic_investigation_data()
        save_dataset(store, path)
        return store

    return KnowledgeGraphStore.from_json(path)


def save_dataset(store: KnowledgeGraphStore, filepath: Optional[Union[str, Path]] = None) -> Path:
    """Saves the knowledge graph store to JSON."""
    path = Path(filepath) if filepath else get_default_dataset_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    store.to_json(path)
    return path
