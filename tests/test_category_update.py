import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, func

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('category_update', ROOT / 'scripts/update_category_data.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


def test_migration_preserves_history_and_is_repeatable():
    # Git対象外の実データがない環境でも、移行と履歴保持を検証する。
    def classification(identifier, name, description=''):
        return dict(source_id=identifier, target_level=5, category1='root', category2='主菜',
                    category3='焼き物', category4='皿物', category5=name,
                    category5_description=description, category6='', category6_description='')

    old = dict(format_version=1,
               source=dict(code='original-food-256-v1', name='テスト元カテゴリ', version='1'),
               source_categories=[dict(id=1, name='rice'), dict(id=33, name='grilled eggplant'),
                                  dict(id=43, name='stew'), dict(id=67, name='omelet')],
               classifications=[classification(1, 'ご飯', '変更前の説明'),
                                classification(33, '焼きナス'), classification(67, 'だし巻き卵')])
    new = deepcopy(old)
    row = next(r for r in new['classifications'] if r['source_id'] == 33)
    row['category5'] = '移行テスト野菜'
    rice = next(r for r in new['classifications'] if r['source_id'] == 1)
    rice['category5_description'] = '変更後の説明'
    added = deepcopy(rice)
    added.update(source_id=43, category5='移行テストシチュー', category5_description='')
    new['classifications'].append(added)
    engine = create_engine('sqlite://')
    updater.metadata.create_all(engine)
    with engine.begin() as c:
        updater.importer.import_data(c, old)
        updater.migrate(c, old, new)
        counts = {t.name: c.scalar(select(func.count()).select_from(t)) for t in updater.metadata.sorted_tables}
        updater.migrate(c, old, new)
        assert counts == {t.name: c.scalar(select(func.count()).select_from(t)) for t in updater.metadata.sorted_tables}
        mappings = updater.category_replacement_mappings
        assert c.scalar(select(func.count()).select_from(mappings).where(mappings.c.deleted_at.is_not(None))) == 1
        assert c.scalar(select(func.count()).select_from(mappings).where(mappings.c.deleted_at.is_(None))) == len(new['classifications'])
        assert c.scalar(select(func.count()).select_from(updater.food_categories).where(updater.food_categories.c.deleted_at.is_not(None))) == 1
    # 想定外のDB差分では、途中変更もロールバックする。
    conflicting = deepcopy(new)
    next(r for r in conflicting['classifications'] if r['source_id'] == 33)['category5'] = '想定外'
    with pytest.raises(ValueError, match='一致しません'):
        with engine.begin() as c:
            updater.migrate(c, old, conflicting)
    with engine.connect() as c:
        assert counts == {t.name: c.scalar(select(func.count()).select_from(t)) for t in updater.metadata.sorted_tables}
    engine.dispose()
