# D:\FYP\FORGE-1\agents\database_generator\__init__.py
"""The Database Agent (D-242, D-245): code only. compile -> seed -> gate -> provision."""
from agents.database_generator.compile import compile_schema
from agents.database_generator.seed import seed_rows, seed_sql

__all__ = ["compile_schema", "seed_rows", "seed_sql"]
