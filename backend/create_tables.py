"""Run once to create all tables from the current models: python create_tables.py
No migration history, no upgrade/downgrade -- just "make the DB match the models."
Fine while the schema is still taking shape; once it's stable, a real project
would introduce Alembic (or similar) so schema changes don't require dropping data.
"""
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401 -- import registers every table on Base.metadata

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tables created.")
