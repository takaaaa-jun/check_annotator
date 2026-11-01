import importlib.util
import json
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


exporter = load('coco_exporter', ROOT / 'scripts/export_coco_categories.py')
importer = load('coco_importer', ROOT / 'scripts/import_categories.py')


@pytest.fixture
def catalog_db():
    path = ROOT / 'data/categories/categories.json'
    if not path.exists():
        pytest.skip('External category data not installed')
    data = json.loads(path.read_text(encoding='utf-8'))
    engine = create_engine('sqlite://')
    importer.metadata.create_all(engine)
    with engine.begin() as connection:
        importer.import_data(connection, data)
    yield engine
    engine.dispose()


def test_export_uses_target_level_and_not_internal_ids(catalog_db):
    with catalog_db.connect() as connection:
        data = exporter.export_blueprint(connection, 'original-food-256-v1', 2)
    assert len(data['sourceCategories']) == 256
    assert len(data['mappings']) == 41
    targets = {row['key']: row for row in data['targetCategories']}
    names = {row['sourceExternalId']: targets[row['targetKey']]['name'] for row in data['mappings']}
    assert names[5] == 'カツ丼'
    assert names[6] == 'カレーライス'
    assert names[8] == 'チキンピラフ'
    assert names[19] == 'サンドウィッチ'
    assert names[20] == 'うどん'
    assert names[21] == '天ぷらうどん'
    udon_key = next(row['targetKey'] for row in data['mappings'] if row['sourceExternalId'] == 20)
    tempura_udon_key = next(row['targetKey'] for row in data['mappings'] if row['sourceExternalId'] == 21)
    assert udon_key.startswith('5:')
    assert tempura_udon_key.startswith('6:')
    assert targets[udon_key]['parentKey'] is None
    assert targets[tempura_udon_key]['parentKey'] == udon_key
    assert targets[udon_key]['description'] == '小麦粉と塩水を混ぜたものを薄く平らに伸ばし一定の厚さに切った料理'
    assert targets[tempura_udon_key]['description'] == 'てんぷらを載せたうどん'
    assert 38 not in names and 43 not in names
    assert len({row['key'] for row in data['targetCategories']}) == len(targets)
    assert all('id' not in row for row in data['targetCategories'])


def test_export_deterministic_and_description_changes_version(catalog_db):
    with catalog_db.begin() as connection:
        first = exporter.export_blueprint(connection, 'original-food-256-v1', 2)
        assert first == exporter.export_blueprint(connection, 'original-food-256-v1', 2)
        master = importer.masters[5]
        connection.execute(master.update().where(master.c.name == 'ご飯').values(description='new description'))
        changed = exporter.export_blueprint(connection, 'original-food-256-v1', 2)
        assert first['version'] != changed['version']


def test_export_refuses_deleted_target(catalog_db):
    from datetime import datetime
    with catalog_db.begin() as connection:
        master = importer.masters[5]
        connection.execute(master.update().where(master.c.name == 'ご飯').values(deleted_at=datetime.now()))
        with pytest.raises(ValueError, match='削除済み'):
            exporter.export_blueprint(connection, 'original-food-256-v1', 2)
