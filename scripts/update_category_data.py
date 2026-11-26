"""Excelカテゴリを既存分類へ統合する。既定は検証のみ、適用前にファイル/DBを保存。"""
import argparse
import csv
from datetime import datetime, UTC
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import select, text
from app.db.category_schema import metadata, masters, food_categories, category_sources, source_categories, category_replacement_mappings
spec = importlib.util.spec_from_file_location('category_import', ROOT / 'scripts/import_categories.py')
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


def read_excel(path):
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as archive:
        shared = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            shared = [''.join(t.text or '' for t in item.findall('m:t', ns) + item.findall('m:r/m:t', ns))
                      for item in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('m:si', ns)]
        rows = []
        for row in ET.fromstring(archive.read('xl/worksheets/sheet1.xml')).findall('.//m:sheetData/m:row', ns):
            cells = {}
            for cell in row:
                column = ''.join(c for c in cell.attrib['r'] if c.isalpha())
                if cell.get('t') == 's':
                    value = shared[int(cell.findtext('m:v', '', ns))]
                elif cell.get('t') == 'inlineStr':
                    value = ''.join(t.text or '' for t in cell.findall('m:is/m:t', ns) + cell.findall('m:is/m:r/m:t', ns))
                else:
                    value = cell.findtext('m:v', '', ns)
                cells[column] = value.strip()
            if row.attrib['r'] == '1':
                if [cells.get(c) for c in ('C', 'D', 'E', 'F', 'G', 'I')] != [f'category{i}' for i in range(1, 7)]:
                    raise ValueError('Excel列が想定と異なります。')
                continue
            if not cells.get('A') and not cells.get('B'):
                continue
            if bool(cells.get('A')) == bool(cells.get('B')):
                raise ValueError('元IDはA/Bの一方だけに指定してください。')
            item = {'source_id': int(cells.get('A') or cells['B']), 'target_level': 5 if cells.get('A') else 6}
            item.update({f'category{i}': cells.get(c, '') for i, c in enumerate(('C','D','E','F','G','I'), 1)})
            item.update(category5_description=cells.get('H', ''), category6_description=cells.get('J', ''))
            rows.append(item)
    # 同一category5は説明を共有する。利用者の54番の汎用説明を35番にも採用。
    general = next((r for r in rows if r['source_id'] == 54 and r['category5'] == 'てんぷら'), None)
    if general:
        for row in rows:
            if row['category5'] == 'てんぷら':
                row['category5_description'] = general['category5_description']
    return rows


def merge_bundle(old, rows):
    data = json.loads(json.dumps(old))
    ids = [r['source_id'] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError('Excelの元IDが重複しています。')
    # Excelにない既存カテゴリ（67番だし巻き卵等）は保持。
    data['classifications'] = rows + [r for r in old['classifications'] if r['source_id'] not in ids]
    importer.validate(data)
    return data


def backup_files(directory, excel):
    directory.mkdir(parents=True, exist_ok=False)
    for name in ('classifications.tsv', 'categories.json', 'categories.json.sha256', 'source_names.txt'):
        shutil.copy2(ROOT / 'data/categories' / name, directory / name)
    shutil.copy2(excel, directory / excel.name)
    (directory / 'sha256.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.iterdir() if p.is_file()}, indent=2), encoding='utf-8')


def write_bundle(data):
    directory = ROOT / 'data/categories'
    with (directory / 'classifications.tsv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data['classifications'][0]), delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(data['classifications'])
    output = directory / 'categories.json'
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    (directory / 'categories.json.sha256').write_text(hashlib.sha256(output.read_bytes()).hexdigest() + '  categories.json\n', encoding='ascii', newline='\n')


def migrate(connection, old, new):
    """単一トランザクション内。変更前の対応を論理削除し、履歴と旧分類を保持。"""
    now = datetime.now(UTC).replace(tzinfo=None)
    original = {r['source_id']: r for r in old['classifications']}
    desired = {r['source_id']: r for r in new['classifications']}
    source = connection.execute(select(category_sources).where(category_sources.c.code == new['source']['code'])).mappings().one()
    foods = {r['food_category_id']: r for r in connection.execute(select(food_categories)).mappings()}
    master_rows = {i: {r[f'category{i}_id']: r for r in connection.execute(select(masters[i])).mappings()} for i in range(1, 7)}
    sources = {r['source_category_id']: r for r in connection.execute(select(source_categories).where(
        source_categories.c.category_source_id == source['category_source_id'])).mappings()}
    retired_foods = set()
    for mapping in connection.execute(select(category_replacement_mappings).where(category_replacement_mappings.c.deleted_at.is_(None))).mappings():
        if mapping['source_category_id'] not in sources:
            continue
        sid = sources[mapping['source_category_id']]['external_category_id']
        if sid not in desired:
            continue
        food = foods[mapping['food_category_id']]
        actual = {f'category{i}': master_rows[i][food[f'category{i}_id']]['name'] if food[f'category{i}_id'] else '' for i in range(1, 7)}
        actual['target_level'] = mapping['target_level']
        target = desired[sid]
        if all(actual[k] == target[k] for k in actual):
            continue
        if sid not in original or any(actual[k] != original[sid][k] for k in actual):
            raise ValueError(f'元ID{sid}のDBが変更前/変更後データと一致しません。')
        connection.execute(category_replacement_mappings.update().where(category_replacement_mappings.c.mapping_id == mapping['mapping_id']).values(deleted_at=now, updated_at=now))
        retired_foods.add(food['food_category_id'])
    for i in (5, 6):
        old_descriptions = {r[f'category{i}']: r[f'category{i}_description'] or None for r in old['classifications'] if r[f'category{i}']}
        descriptions = {r[f'category{i}']: r[f'category{i}_description'] or None for r in new['classifications'] if r[f'category{i}']}
        for row in master_rows[i].values():
            if row['name'] not in descriptions or row['description'] == descriptions[row['name']]:
                continue
            if row['description'] != old_descriptions.get(row['name']):
                raise ValueError(f'category{i}の説明が変更前と一致しません。')
            connection.execute(masters[i].update().where(masters[i].c[f'category{i}_id'] == row[f'category{i}_id']).values(description=descriptions[row['name']], updated_at=now))
    importer.import_data(connection, new)
    for identifier in retired_foods:
        used = connection.execute(select(category_replacement_mappings.c.mapping_id).where(
            category_replacement_mappings.c.food_category_id == identifier, category_replacement_mappings.c.deleted_at.is_(None))).first()
        if used is None:
            connection.execute(food_categories.update().where(food_categories.c.food_category_id == identifier).values(deleted_at=now, updated_at=now))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--excel', type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='ローカル定義をバックアップ後に更新')
    parser.add_argument('--apply-db', action='store_true', help='カテゴリ10テーブルをバックアップ後にDB更新（--apply必須）')
    args = parser.parse_args()
    if args.apply_db and not args.apply:
        parser.error('--apply-dbには--applyが必要です。')
    old = json.loads((ROOT / 'data/categories/categories.json').read_text(encoding='utf-8'))
    data = merge_bundle(old, read_excel(args.excel))
    print(json.dumps(importer.validate(data), ensure_ascii=False))
    if not args.apply:
        print('検証のみ。ファイル・DBは変更していません。')
        return
    directory = ROOT / 'backups' / ('categories-' + datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ'))
    backup_files(directory, args.excel)
    print('Backup:', directory)
    if args.apply_db:
        from app.database import build_database_url, build_engine_options
        from sqlalchemy import create_engine
        from sqlalchemy.engine import make_url
        url = make_url(build_database_url())
        if url.drivername != 'mysql+pymysql' or url.database != 'check_annotator':
            raise ValueError('接続先はmysql+pymysql / check_annotatorに限定します。')
        engine = create_engine(url, **build_engine_options(str(url)))
        try:
            with engine.connect() as connection:
                if connection.execute(text("SELECT GET_LOCK('check_annotator.categories', 0)")).scalar_one() != 1:
                    raise ValueError('カテゴリ更新ロックを取得できません。')
                connection.commit()
                try:
                    with connection.begin():
                        snapshot = {table.name: [dict(r) for r in connection.execute(select(table).with_for_update()).mappings()] for table in metadata.sorted_tables}
                        backup = directory / 'database.json'
                        backup.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, default=lambda v: v.isoformat()), encoding='utf-8')
                        (directory / 'database.json.sha256').write_text(hashlib.sha256(backup.read_bytes()).hexdigest(), encoding='ascii')
                        migrate(connection, old, data)
                        from export_coco_categories import export_blueprint
                        blueprint = export_blueprint(connection, data['source']['code'], 2)
                        if len(blueprint['mappings']) != len(data['classifications']):
                            raise ValueError('DB更新後の対応件数が一致しません。')
                        (directory / 'coco-taxonomy.json').write_text(json.dumps(blueprint, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                        print('COCO export:', len(blueprint['targetCategories']), 'targets,', len(blueprint['mappings']), 'mappings')
                finally:
                    connection.rollback()
                    connection.execute(text("SELECT RELEASE_LOCK('check_annotator.categories')"))
                    connection.commit()
        finally:
            engine.dispose()
    write_bundle(data)
    print('適用完了。COCOへの同期は別途必要です。')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(importer.error_message(error), file=sys.stderr)
        sys.exit(1)
