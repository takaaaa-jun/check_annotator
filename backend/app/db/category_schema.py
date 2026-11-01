"""カテゴリ専用スキーマ。既存6テーブルの初期化とは独立して追加する。"""
from sqlalchemy import (
    CheckConstraint, Column, Computed, DateTime, ForeignKey, Integer,
    MetaData, String, Table, Text, UniqueConstraint,
)
from sqlalchemy.dialects.mysql import INTEGER

metadata = MetaData()
uint = Integer().with_variant(INTEGER(unsigned=True), "mysql")
options = dict(mysql_engine="InnoDB", mysql_charset="utf8mb4",
               mysql_collate="utf8mb4_unicode_ci")


def audit():
    return [Column("created_at", DateTime, nullable=False),
            Column("updated_at", DateTime, nullable=False),
            Column("deleted_at", DateTime)]


def pk(name):
    return Column(name, uint, primary_key=True, autoincrement=True)


def ref(name, target, nullable=False):
    return Column(name, uint, ForeignKey(target, ondelete="RESTRICT",
                                       onupdate="RESTRICT"), nullable=nullable)


masters = {}
for level in range(1, 7):
    masters[level] = Table(
        f"category{level}_master", metadata, pk(f"category{level}_id"),
        Column("code", String(100), nullable=False, unique=True),
        Column("name", String(100), nullable=False), Column("description", Text),
        Column("sort_order", uint, nullable=False, server_default="0"),
        *audit(), **options,
    )

food_categories = Table(
    "food_categories", metadata, pk("food_category_id"),
    Column("code", String(100), nullable=False, unique=True),
    *[ref(f"category{i}_id", f"category{i}_master.category{i}_id", i == 6)
      for i in range(1, 7)],
    Column("category6_key", uint, Computed("COALESCE(category6_id, 0)", persisted=True)),
    UniqueConstraint(*[f"category{i}_id" for i in range(1, 6)], "category6_key",
                     name="uq_food_category_path"),
    *audit(), **options,
)
category_sources = Table(
    "category_sources", metadata, pk("category_source_id"),
    Column("code", String(100), nullable=False, unique=True),
    Column("name", String(100), nullable=False),
    Column("version", String(50), nullable=False), *audit(), **options,
)
source_categories = Table(
    "source_categories", metadata, pk("source_category_id"),
    ref("category_source_id", "category_sources.category_source_id"),
    Column("external_category_id", uint, nullable=False),
    Column("name", String(100), nullable=False),
    UniqueConstraint("category_source_id", "external_category_id",
                     name="uq_source_external_category"),
    *audit(), **options,
)
category_replacement_mappings = Table(
    "category_replacement_mappings", metadata, pk("mapping_id"),
    ref("source_category_id", "source_categories.source_category_id"),
    ref("food_category_id", "food_categories.food_category_id"),
    Column("target_level", uint, nullable=False),
    CheckConstraint("target_level IN (5, 6)", name="ck_mapping_target_level"),
    Column("active_source_key", uint,
           Computed("CASE WHEN deleted_at IS NULL THEN source_category_id ELSE NULL END",
                    persisted=True)),
    UniqueConstraint("active_source_key", name="uq_active_source_mapping"),
    *audit(), **options,
)
