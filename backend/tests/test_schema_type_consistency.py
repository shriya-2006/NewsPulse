"""
Regression test for a real bug: database/schema.sql declares every
primary key as BIGINT UNSIGNED, but the ORM's shared BigIntPK type used
to compile to plain (signed) BIGINT on MySQL. This went unnoticed for
a long time because every table that already existed in a real
database was created by running schema.sql directly (both sides
UNSIGNED, consistent) — it only surfaced as a real, reproducible crash
the first time a brand new ORM-only table (cached_search_articles) was
added after the database already existed: MySQL 8.0.19+ rejects
creating a foreign key whose referencing column's signedness doesn't
match the referenced column's (error 3780).

This test compiles the actual DDL SQLAlchemy would send to a MySQL
server (without needing a real one) and asserts every id/foreign-key
column is BIGINT UNSIGNED — so if this type declaration ever
regresses back to plain (signed) BigInteger for any table, this test
fails immediately instead of only surfacing as a startup crash against
a real, already-populated MySQL database.
"""

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app import models  # noqa: F401  (registers every model on Base.metadata)
from app.db.database import Base

# Every table that has an `id` primary key or a BigInt-typed foreign key.
_TABLES_WITH_BIGINT_COLUMNS = {
    "users": ["id"],
    "password_reset_tokens": ["id", "user_id"],
    "newspapers": ["id"],
    "newspaper_editions": ["id", "newspaper_id"],
    "search_history": ["id", "user_id"],
    "custom_tags": ["id", "user_id"],
    "reports": ["id", "user_id"],
    "articles": ["id"],
    "report_articles": ["report_id", "article_id"],
    "cached_searches": ["id"],
    "cached_search_articles": ["cached_search_id", "article_id"],
}


def test_every_bigint_column_is_unsigned_on_mysql():
    for table_name, column_names in _TABLES_WITH_BIGINT_COLUMNS.items():
        table = Base.metadata.tables[table_name]
        ddl = str(CreateTable(table).compile(dialect=mysql.dialect()))

        for column_name in column_names:
            # Look for e.g. "    user_id BIGINT UNSIGNED" — a signed
            # regression would show "BIGINT NOT NULL" or "BIGINT," with
            # no UNSIGNED keyword directly after it.
            found = False
            for line in ddl.splitlines():
                stripped = line.strip()
                if stripped.startswith(column_name + " ") or stripped.startswith(column_name + "\t"):
                    assert "UNSIGNED" in stripped, (
                        f"{table_name}.{column_name} is not UNSIGNED on MySQL: {stripped!r}\n"
                        "This is exactly the class of bug that caused a real startup "
                        "crash (MySQL error 3780) — see this test's module docstring."
                    )
                    found = True
                    break
            assert found, f"Could not find column {column_name!r} in compiled DDL for {table_name!r}"


def test_new_fk_tables_are_type_compatible_with_pre_existing_tables():
    """
    More direct simulation of the actual bug: confirms a *referencing*
    column's compiled type text is identical to the *referenced*
    column's, for every foreign key added by this project — this is
    exactly the comparison MySQL itself makes (and rejects on mismatch).
    """
    from sqlalchemy.dialects import mysql as mysql_dialect

    def compiled_type(table_name: str, column_name: str) -> str:
        column = Base.metadata.tables[table_name].columns[column_name]
        return column.type.compile(dialect=mysql_dialect.dialect())

    fk_pairs = [
        ("password_reset_tokens", "user_id", "users", "id"),
        ("search_history", "user_id", "users", "id"),
        ("custom_tags", "user_id", "users", "id"),
        ("reports", "user_id", "users", "id"),
        ("report_articles", "article_id", "articles", "id"),
        ("newspaper_editions", "newspaper_id", "newspapers", "id"),
        ("cached_search_articles", "article_id", "articles", "id"),
        ("cached_search_articles", "cached_search_id", "cached_searches", "id"),
    ]

    for ref_table, ref_col, target_table, target_col in fk_pairs:
        referencing_type = compiled_type(ref_table, ref_col)
        referenced_type = compiled_type(target_table, target_col)
        assert referencing_type == referenced_type, (
            f"{ref_table}.{ref_col} ({referencing_type}) does not match "
            f"{target_table}.{target_col} ({referenced_type}) — MySQL will "
            f"reject this foreign key with error 3780."
        )
