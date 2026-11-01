# MySQLの新カテゴリとCOCO Annotatorの同期

## 結論

登録済みMySQLからcategory5・category6を出力し、COCOの対象データセットに新カテゴリを作成・同期する。
今回のデータでは新カテゴリ45件、置換対応41件。未対応215件は置換できない。
check_annotatorのタスク行を展開すると、既存の確認ダイアログから対応済みボックスを1件ずつ置換できる。
新規付与・手動再分類はCOCO側で、新しく同期したカテゴリだけを選択する。

## IDを照合する理由

MySQLの内部ID、元256分類の外部ID、COCOの実IDは別物。
元IDをCOCO IDの候補として利用しても、元名称との完全一致を必ず確認する。
新カテゴリは階層と管理codeをキーにし、COCOが採番した実IDへ解決する。
同名だからという理由で既存カテゴリを上書き・流用しない。
ID・名称・管理code・対象データセット名に不一致があれば、同期を中止する。

旧カテゴリは既存アノテーション・履歴の参照用に保持する。
対象データセットの新規付与の選択肢だけを新カテゴリへ切り替える。
旧カテゴリの付与済みボックスはCOCO編集画面にも残し、新規作成ボタン・再分類先からは除外する。
管理者の全カテゴリ一覧には参照用の旧カテゴリが残る。

## 変更するファイル

check_annotator側：`scripts/export_coco_categories.py`、`tests/test_coco_export.py`。
COCO側：`backend/scripts/sync_categories.py`、同期ヘルパー、置換・編集・付与API、Vueカテゴリ選択、テスト。
両リポジトリの変更を反映する必要がある。
学内サーバーへの適用は、この作業では実施していない。

## サーバーで反映する

以下はcheck_annotatorが`/srv/check_annotator`、COCOが`/srv/coco-annotator`の場合。
実際の配置場所へ読み替える。事前に両リポジトリの変更をマージしてpullする。
既存のMySQL10テーブル・MongoDB・画像データは初期化しない。

1. check_annotator側で、実際のMySQLから同期用JSONを出力する。MySQLへの書き込みはない。

```bash
cd /srv/check_annotator
docker compose build backend
docker compose run --rm --no-deps --user "$(id -u):$(id -g)" -v "$PWD:/source" \
  backend python /source/scripts/export_coco_categories.py \
  --dataset-id 2 --dataset-name food_detection \
  --output /source/imports/categories/coco-taxonomy.json
```

期待する件数はsourceCategories=256、targetCategories=45、mappings=41。
データセットID・名称はCOCO側で実在する対象の値を指定する。名前も同期時に照合する。

2. COCOのdatasets内へJSONを配置する。同じサーバーに両リポジトリがある場合：

```bash
mkdir -p /srv/coco-annotator/datasets/.category-review
cp /srv/check_annotator/imports/categories/coco-taxonomy.json \
  /srv/coco-annotator/datasets/.category-review/taxonomy.json
```

別サーバーの場合はこのJSONをSCPで同じ位置へ転送する。
このJSONは既存のcatalog.jsonとは別形式。CATEGORY_REVIEW_CATALOGへ直接指定しない。

3. COCOの全編集画面を閉じて保存を完了する。COCO側の`.env`に次を設定する。

```dotenv
CATEGORY_REVIEW_DATASET_ID=2
CATEGORY_REVIEW_CATALOG=
```

新しい対応表はMongoDBの対象データセットに保存され、この設定から参照する。
同期済みデータセットで古いファイル対応表へ戻る動作は拒否する。

4. COCO側をビルドし、書き込み元を停止してから内容確認する。

```bash
cd /srv/coco-annotator
docker compose build backend frontend workers
docker compose stop backend frontend workers
docker compose run --rm --no-deps -v "$PWD/backend:/source:ro" \
  backend python /source/scripts/sync_categories.py \
  --data /datasets/.category-review/taxonomy.json
```

プレビューは参照のみで、新カテゴリ45件・対応41件を報告する。
元IDとCOCOの実IDが異なる場合は、誤対応を避けるため中止する。
その場合のみ、実IDを確認したJSON（例：`{"20": 320}`）を用意し、
`--source-bindings /datasets/.category-review/source-bindings.json`を追加する。
明示指定しても名称一致・一意性の検証は省略しない。
元表のID40と67は同名omeletなので、COCO側で別IDとして存在することも確認する。
対象データセットに元表・管理対象以外のカテゴリがある場合も、無断で選択肢から外さず中止する。

5. プレビュー成功後、同じコマンドへ`--apply`を追加して適用する。

```bash
docker compose run --rm --no-deps -v "$PWD/backend:/source:ro" \
  backend python /source/scripts/sync_categories.py \
  --data /datasets/.category-review/taxonomy.json --apply
docker compose up -d backend frontend workers
```

source-bindingsを指定して確認した場合は、適用時も同じ指定を付ける。
同期は新カテゴリ作成後に全件を再照合し、カテゴリ選択肢と対応表をデータセットの単一更新で有効化する。
途中失敗時に作成済みカテゴリが残る場合はあるが、対応表は部分的に有効化されない。
原因を解消して再実行すると管理codeで再利用する。同期自体は画像・既存ボックスを変更しない。
強制終了でcategory_sync_lockが残った場合は、別の同期が実行中でないことを確認して管理者が復旧する。

6. COCOへログインし、check_annotatorのタスク行の「カテゴリ確認」を開く。
対応済みのボックスだけに新しい日本語の置換候補が表示される。
「置き換えを確認」→対象ボックスと新カテゴリを確認→「この1件を置き換える」で保存する。
未対応215件は参照のみ。編集中・古い画面・別の保存との競合は拒否される。
単独のカテゴリ確認ページではデータ元をCOCO Annotator（実データ）へ切り替える。

## テスト結果

実MySQL 8.0.44から出力した256元カテゴリ・45新カテゴリ・41対応を、
隔離した実MongoDB 4.4.29、実際のCOCOモデル、Flask 1.0.2 / Flask-RESTPlus 0.12.1のAPIで確認した。
41対応すべてを実APIで置換し、別ボックス・座標・セグメンテーション・独自メタデータが保持されることを確認。
未対応、元名称不一致、対象外データセット、管理code改変、旧カテゴリ新規付与、古い編集内容の保存、権限・Origin違反を拒否するテストを用意している。
COCOの既存置換APIテストと、Vue 2の実テンプレートによる選択肢・作成禁止のテストも実行する。

今回の実行結果：同期・実API21件、既存置換API15件、Vueカテゴリ選択15件、
check_annotatorの出力・既存DB投入関連35件が成功（計86件）。
Vue側は実際のVue 2.5.17テンプレートを使って検証した。
ローカルのBabel依存不足により標準Jest一括実行は起動できなかったため、
カテゴリ関連2スイートは隔離したBabel変換設定で実行している。全フロントエンドのテスト成功を意味しない。

MongoDB本番構成は既存Composeの4.0。今回ローカルで実行確認した版は4.4.29。
Docker本番イメージ全体のビルドと、実ブラウザーでの操作確認は未実施。
41件の既存アノテーションをサーバーで自動一括更新する機能ではない。

参考：[MongoDBの単一ドキュメント更新の原子性](https://www.mongodb.com/docs/v8.0/core/write-operations-atomicity/)。
