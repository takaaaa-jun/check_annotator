import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dashimaki_update', ROOT / 'scripts/add_dashimaki_category.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_adds_only_id67_mapping_and_is_repeatable():
    path = ROOT / 'data/categories/categories.json'
    if not path.exists():
        pytest.skip('External category data not installed')
    data = json.loads(path.read_text(encoding='utf-8'))
    data['classifications'] = [row for row in data['classifications'] if row['source_id'] != 67]
    importer = module.importer
    engine = create_engine('sqlite://')
    importer.metadata.create_all(engine)
    try:
        with engine.begin() as connection:
            importer.import_data(connection, data)
            mappings = importer.category_replacement_mappings
            before = list(connection.execute(select(mappings)).mappings())
            module.update(connection, apply=False)
            assert list(connection.execute(select(mappings)).mappings()) == before
            module.update(connection, apply=True)
            after = list(connection.execute(select(mappings)).mappings())
            assert after[:len(before)] == before
            assert len(after) == len(before) + 1
            module.update(connection, apply=True)
            assert list(connection.execute(select(mappings)).mappings()) == after
            assert connection.scalar(select(func.count()).select_from(importer.source_categories)) == 256
    finally:
        engine.dispose()


def test_refuses_uninitialized_database():
    engine = create_engine('sqlite://')
    module.importer.metadata.create_all(engine)
    try:
        with engine.begin() as connection:
            with pytest.raises(ValueError, match='初期化は行いません'):
                module.update(connection, apply=True)
    finally:
        engine.dispose()
