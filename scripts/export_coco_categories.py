"""登録済みMySQLカテゴリをCOCOへ渡す。MySQL・COCOのIDは同一視しない。"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, select  # noqa: E402
from app.db.category_schema import (category_sources, source_categories, masters,
                                    food_categories, category_replacement_mappings)  # noqa: E402


def export_blueprint(connection, source_code, dataset_id, dataset_name='food_detection'):
    if type(dataset_id) is not int or dataset_id <= 0:
        raise ValueError('dataset-idは正の整数が必要です。')
    source = connection.execute(select(category_sources).where(
        category_sources.c.code == source_code, category_sources.c.deleted_at.is_(None))).mappings().one()
    sources = list(connection.execute(select(source_categories).where(
        source_categories.c.category_source_id == source['category_source_id'],
        source_categories.c.deleted_at.is_(None)).order_by(source_categories.c.external_category_id)).mappings())
    source_by_id = {row['source_category_id']: row for row in sources}
    foods = list(connection.execute(select(food_categories).where(food_categories.c.deleted_at.is_(None))).mappings())
    master_rows = {i: {row[f'category{i}_id']: row for row in connection.execute(
        select(masters[i]).where(masters[i].c.deleted_at.is_(None))).mappings()} for i in range(1, 7)}
    targets, food_by_id = {}, {}
    for food in foods:
        for i in range(1, 7):
            identifier = food[f'category{i}_id']
            if identifier is None and i == 6:
                continue
            if identifier not in master_rows[i]:
                raise ValueError('有効な分類が削除済みマスタを参照しています。')
            if i < 5:
                continue
            row = master_rows[i][identifier]
            key = f"{i}:{row['code']}"
            parent = f"5:{master_rows[5][food['category5_id']]['code']}" if i == 6 else None
            target = {'key': key, 'name': row['name'], 'description': row['description'] or '', 'parentKey': parent}
            if key in targets and targets[key] != target:
                raise ValueError('同一category6に複数の親があります。COCO向け分類を確定してください。')
            targets[key] = target
        food_by_id[food['food_category_id']] = food
    mappings = []
    for row in connection.execute(select(category_replacement_mappings).where(
            category_replacement_mappings.c.deleted_at.is_(None),
            category_replacement_mappings.c.source_category_id.in_(list(source_by_id)))).mappings():
        food = food_by_id.get(row['food_category_id'])
        level = row['target_level']
        if food is None or level not in (5, 6) or food[f'category{level}_id'] is None:
            raise ValueError('置換対応の分類または対象階層が無効です。')
        target = master_rows[level][food[f'category{level}_id']]
        mappings.append({'sourceExternalId': source_by_id[row['source_category_id']]['external_category_id'],
                         'targetKey': f"{level}:{target['code']}"})
    if not targets or not mappings:
        raise ValueError('新カテゴリまたは置換対応が空です。')
    data = {'schemaVersion': 1, 'taxonomy': 'check-annotator', 'datasetId': dataset_id, 'datasetName': dataset_name,
            'source': {'code': source['code'], 'version': source['version']},
            'sourceCategories': [{'externalId': row['external_category_id'], 'name': row['name']} for row in sources],
            'targetCategories': sorted(targets.values(), key=lambda row: row['key']),
            'mappings': sorted(mappings, key=lambda row: row['sourceExternalId'])}
    data['version'] = hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                               separators=(',', ':')).encode('utf-8')).hexdigest()
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-code', default='original-food-256-v1')
    parser.add_argument('--dataset-id', type=int, required=True)
    parser.add_argument('--dataset-name', default='food_detection')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from app.database import build_database_url, build_engine_options
    from sqlalchemy.engine import make_url
    url = make_url(build_database_url())
    if url.drivername != 'mysql+pymysql' or url.database != 'check_annotator':
        raise ValueError('MySQLのcheck_annotator DBを指定してください。')
    engine = create_engine(url, **build_engine_options(str(url)))
    try:
        # 一貫したスナップショットから読み出し、DBへの書き込みは行わない。
        with engine.connect().execution_options(isolation_level='REPEATABLE READ') as connection:
            with connection.begin():
                data = export_blueprint(connection, args.source_code, args.dataset_id, args.dataset_name)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        print(json.dumps({'sourceCategories': len(data['sourceCategories']), 'targetCategories': len(data['targetCategories']),
                          'mappings': len(data['mappings']), 'datasetId': data['datasetId']}, ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error) if isinstance(error, ValueError) else type(error).__name__, file=sys.stderr)
        sys.exit(1)
