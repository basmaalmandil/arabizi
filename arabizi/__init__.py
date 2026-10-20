"""Arabizi: a small, statically typed Arabic-inspired programming language."""
from .compiler import compile_source
from .model import ArabiziError
from .vm import VM

__all__ = ["compile_source", "ArabiziError", "VM"]
__version__ = "0.1.0"
