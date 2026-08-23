"""Data package for CrimeGraph AI."""

from crimegraph.data.generator import generate_synthetic_investigation_data
from crimegraph.data.loader import load_dataset, save_dataset, get_default_dataset_path

__all__ = [
    "generate_synthetic_investigation_data",
    "load_dataset",
    "save_dataset",
    "get_default_dataset_path",
]
