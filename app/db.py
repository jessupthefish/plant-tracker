from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(f"sqlite:///{settings.db_path}", connect_args={"check_same_thread": False})


def _ensure_column(conn, table: str, column: str, sql_type: str) -> None:
    existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
        conn.commit()


def init_db() -> None:
    import app.models  # noqa: F401  (register models with SQLModel metadata)

    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        _ensure_column(conn, "plants", "variety", "TEXT")


def get_session():
    with Session(engine) as session:
        yield session
