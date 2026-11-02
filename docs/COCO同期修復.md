# 実サーバーの255カテゴリと新カテゴリの同期

## 結論と原因

サーバーのfood_detectionはデータセットID2で正しいが、確認時点では新対応表が未登録だった。
`selectable:255 / targets:0 / mappings:0`がその証拠。
元表のID40と67は両方ともomeletで、COCOではID40の1件に統合されている。
そのためCOCO ID67はegg sunny-side up、255はhot & sour soupで、元表の番号とは異なる。
従来の同期処理は全256件のID一致を要求して中止していた。
元ID166の名称にも、`green   pepper`と`green pepper`という空白数の差がある。
また、編集画面の保存本文がフォーム形式の扱いになり、「JSONオブジェクトが必要です」となる不具合も修正した。

## 修正内容

- 実COCOのIDや名前は書き換えず、対象データセット内の名称の完全一致から実IDを解決する。
- 一致しない場合は空白だけを正規化して照合する。単語・綴り・大文字小文字は変更しない。
- 同名候補が複数あり、既知IDでも特定できなければ中止。名前の部分一致・近似一致は使わない。
- 元ID67へ、利用者指定の`root → 主菜 → 焼き物 → 皿物 → だし巻き卵`を追加。
- COCOのomeletには「オムレツ」「だし巻き卵」の2候補を表示し、選択と確認を必須にする。
- 古い画面が先頭候補を送信しても、選択確認フラグがなければ拒否する。
- 保存処理は新画面からJSON形式で送り、開いたままの旧画面も同じホストに限って受け付ける。
- 旧カテゴリと既存ボックス・座標・独自メタデータは保持する。同期だけでは既存ボックスを置換しない。

## サーバー反映手順

両リポジトリの修正PRをマージしてから、サーバーで実行する。
MySQLは登録済みのまま使う。DB初期化、カテゴリーの全削除、IDの振り直しは行わない。
以下は`/srv/check_annotator`と`/srv/coco-annotator`に配置されている場合。

### 1. check_annotatorを更新し、元ID67だけ追加する

```bash
cd /srv/check_annotator
git switch main
git pull --ff-only origin main
docker compose build backend frontend

docker compose run --rm --no-deps -v "$PWD:/source:ro" \
  backend python /source/scripts/add_dashimaki_category.py
```

「元ID67 → root / 主菜 / 焼き物 / 皿物 / だし巻き卵」が表示されたら適用する。
限定更新なので、新しい256件JSONをSCPで転送する必要はない。

```bash
docker compose run --rm --no-deps -v "$PWD:/source:ro" \
  backend python /source/scripts/add_dashimaki_category.py --apply

docker compose run --rm --no-deps --user "$(id -u):$(id -g)" -v "$PWD:/source" \
  backend python /source/scripts/export_coco_categories.py \
  --dataset-id 2 --dataset-name food_detection \
  --output /source/imports/categories/coco-taxonomy.json
```

出力の期待値：sourceCategories=256、targetCategories=46、mappings=42。
再実行しても一致する既存行は変更しない。元ID67がomeletでないDBでは停止する。

```bash
mkdir -p /srv/coco-annotator/datasets/.category-review
cp /srv/check_annotator/imports/categories/coco-taxonomy.json \
  /srv/coco-annotator/datasets/.category-review/taxonomy.json
docker compose up -d --no-deps backend frontend
```

### 2. COCOを更新し、保存エラーを直す

```bash
cd /srv/coco-annotator
git switch main
git pull --ff-only origin main
docker compose build backend frontend workers
docker compose up -d backend frontend workers
```

`.env`は`CATEGORY_REVIEW_DATASET_ID=2`、`CATEGORY_REVIEW_CATALOG=`を維持する。
開いている編集画面で保存を完了してから、全員の編集画面を閉じる。
旧画面の本文形式にも対応したため、この段階で保存できる。
保存できていない編集がある状態で、画面を強制再読み込みして破棄しないこと。

### 3. COCOの同期を確認する

```bash
cd /srv/coco-annotator
docker compose stop backend frontend workers
docker compose run --rm --no-deps -v "$PWD/backend:/source:ro" \
  backend python /source/scripts/sync_categories.py \
  --data /datasets/.category-review/taxonomy.json
```

期待値：

| 項目 | 件数 |
| --- | --- |
| sourceRows（元表） | 256 |
| actualSourceCategories（実COCO） | 255 |
| targetCategories（新カテゴリ） | 46 |
| mappings（実COCO IDごとの対応） | 41 |
| replacementChoices（全候補） | 42 |
| ambiguousMappings（選択必須） | 1 |

createCategoriesは初回46、再実行時は0。途中で作成済みのものがあればその分だけ少なくなる。
「元表とCOCOでカテゴリ数が違う」こと自体は、この配置では正常として扱う。
元ID67が未対応のままなら同期は中止する。手順1を確認する。

### 4. 成功した場合だけ適用・再起動する

```bash
docker compose run --rm --no-deps -v "$PWD/backend:/source:ro" \
  backend python /source/scripts/sync_categories.py \
  --data /datasets/.category-review/taxonomy.json --apply
```

`applied:true`と上記件数を確認したら再起動する。

```bash
docker compose up -d backend frontend workers
docker compose ps
```

COCOへログインし直して編集画面を読み込む。新規付与は新カテゴリ46件になる。
旧カテゴリの付与済みボックスは参照・編集用に残るが、旧カテゴリで新しいボックスは作成できない。
check_annotatorの「カテゴリ確認」で、omeletのボックスは置換先を選択するまでボタンが無効になる。
「オムレツ」または「だし巻き卵」を選び、確認後にそのボックスだけ置換する。

## 検証

実サーバーと同じ255カテゴリ・ID67以降がずれた配置を実MongoDBに再現した。
全41対応・42候補を実APIで置換し、旧255カテゴリのID・名前・他ボックス・座標の保持を確認。
同期中・未対応・曖昧な名前・選択なし・古い画面・不正な保存形式・異なるOriginを拒否するテストを実行。
MySQL側は元41分類から42分類へ追加する限定更新の再実行と、既存6テーブルの保持も確認する。
画面側は両候補の選択・キャンセル・確認後の1件更新を実Reactテストで確認している。

実行結果：check_annotatorのPython37件、実MySQL5件、React全92件、COCO同期・実API27件、
既存置換API15件、Vue/Axios18件が成功。型チェック・静的チェックも成功。
Next.jsの本番用ビルドも成功した。
ブラウザーでは検証用データで、選択した1件だけをだし巻き卵へ変更する操作を確認した。
サーバーのDBやアノテーションへの適用は、上記コマンドを実行するまで行われない。
