# Excelカテゴリ追加（2026-11-26）

## 適用内容

「使用するカテゴリデータ_ver01.xlsx」を既存カテゴリへ統合。
元256分類のID・名称は維持し、43〜55の13対応を追加した。
33はcategory5「焼き野菜」/category6「焼きナス」、28・29のcategory3は「焼き物」、
39は「煮物」、41は「揚げ物 / 皿物」に変更した。説明文もExcelへ合わせた。
Excelにない既存67「だし巻き卵」は保持する。
41のrootの末尾空白を除去。35と54の共有category5「てんぷら」の説明は54の汎用説明へ統一する。

結果は元カテゴリ256、分類/置換対応55、未対応201、新カテゴリ59（category5と6の合計）。
元資料・データはGit対象外という既存運用を維持する。

## バックアップとMySQL反映

この環境の.envに設定されたMySQLへ適用済み。
バックアップ: `backups/categories-20261126T054114487942Z/`。
元Excel、変更前TSV/JSON/チェックサム/元名称、カテゴリ10テーブルの全行を保存した。
`database.json`には日時・削除済み履歴・生成列も含まれる。
`sha256.json`は元ファイル、`database.json.sha256`はDBバックアップの整合性確認用。
既存のタスク・コメント・ユーザー・画像・アノテーションは更新対象外。

`database.json`はSQLダンプではない。復旧時は書き込みを停止し、生成列
`category6_key` / `active_source_key`をINSERT対象から除外し、日時を復元する必要がある。
更新後の他の変更を失わないよう、全表の無条件上書きは行わず管理者が差分を確認する。
ファイルのみ戻してもMySQLやCOCOは戻らない。

## 再実行

通常の初期投入スクリプトは既存説明・対応との不一致を拒否するため、更新専用スクリプトを使う。
環境変数でDB接続先を設定する（既存CLI同様、.envの自動読み込みはしない）。

```powershell
python scripts/update_category_data.py --excel '使用するカテゴリデータ_ver01.xlsx'
python scripts/update_category_data.py --excel '使用するカテゴリデータ_ver01.xlsx' --apply --apply-db
```

既定は検証のみ。--applyはファイル更新、--apply-db併用でMySQLも更新する。
適用前にバックアップし、DB更新はカテゴリ更新ロックと単一トランザクションで行う。
旧対応と参照されなくなった旧分類は論理削除し、履歴は残す。
想定外の既存対応・説明との不一致はロールバックする。

## COCOへの反映

**説明文更新と旧選択肢の移行には `--previous-data` が必要。実際のコマンドは
[カテゴリ追加ver01のサーバー反映手順](カテゴリ追加_ver01_サーバー反映.md)を使用する。**

MySQLへの更新だけではCOCOの保存済み対応表は変わらない。
バックアップ内の`coco-taxonomy.json`は更新後の実MySQLから生成した同期用JSON。
新カテゴリ59・元IDでの対応55が含まれる。
COCO側でomeletを統合している場合は実IDの対応が54件になる。

[COCO同期修復](COCO同期修復.md)の既存手順に従い、このJSONを稼働サーバーの
`datasets/.category-review/taxonomy.json`へ配置する。
COCOのMongoDBもバックアップし、全編集画面の保存と書き込みサービスの停止後に、
`backend/scripts/sync_categories.py --data 新JSON --previous-data 変更前JSON`で確認し、
同コマンドへ`--apply`を付けて同期する。サービス再開後、33・41・43〜55とomeletの2候補を画面確認する。
既存アノテーションのカテゴリを一括で置き換える処理ではない。
