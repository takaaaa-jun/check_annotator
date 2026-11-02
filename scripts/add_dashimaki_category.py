"""既存の元ID67へ「だし巻き卵」を追加する、再実行可能な限定更新。"""
import argparse
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, select, text  # noqa: E402
from app.db.category_schema import category_sources, source_categories  # noqa: E402

spec = importlib.util.spec_from_file_location('category_import_for_dashimaki', ROOT / 'scripts/import_categories.py')
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


def update(connection, apply=False):
    source = connection.execute(select(category_sources).where(
        category_sources.c.code == 'original-food-256-v1', category_sources.c.deleted_at.is_(None))).mappings().one_or_none()
    if source is None:
        raise ValueError('元カテゴリ登録済みのDBが必要です。初期化は行いません。')
    original = connection.execute(select(source_categories).where(
        source_categories.c.category_source_id == source['category_source_id'],
        source_categories.c.external_category_id == 67, source_categories.c.deleted_at.is_(None))).mappings().one_or_none()
    if original is None or original['name'] != 'omelet':
        raise ValueError('元ID67の名称がomeletと一致しません。変更せず停止します。')
    row = dict(source_id=67, target_level=5, category1='root', category2='主菜', category3='焼き物',
               category4='皿物', category5='だし巻き卵', category5_description='', category6='', category6_description='')
    data = {'format_version': 1, 'source': {key: source[key] for key in ('code', 'name', 'version')},
            'source_categories': [{'id': 67, 'name': original['name']}], 'classifications': [row]}
    importer.validate(data)
    if apply:
        importer.import_data(connection, data)
    return '元ID67 → root / 主菜 / 焼き物 / 皿物 / だし巻き卵'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    from app.database import build_database_url, build_engine_options
    from sqlalchemy.engine import make_url
    url = make_url(build_database_url())
    if url.drivername != 'mysql+pymysql' or url.database != 'check_annotator':
        raise ValueError('接続先はMySQLのcheck_annotator DBに限定しています。')
    engine = create_engine(url, **build_engine_options(str(url)))
    try:
        with engine.connect() as connection:
            if not args.apply:
                print(update(connection))
                print('確認のみ。--applyを付けると登録します。')
                return
            if connection.execute(text("SELECT GET_LOCK('check_annotator.categories', 0)")).scalar_one() != 1:
                raise ValueError('別のカテゴリ更新が実行中です。')
            connection.commit()
            try:
                with connection.begin():
                    print(update(connection, apply=True))
                print('登録完了（既存の一致行は変更しません）。')
            finally:
                connection.rollback()
                connection.execute(text("SELECT RELEASE_LOCK('check_annotator.categories')"))
                connection.commit()
    finally:
        engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(importer.error_message(error), file=sys.stderr)
        sys.exit(1)
