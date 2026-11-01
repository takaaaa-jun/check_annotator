# カテゴリテーブルとデータの導入

## 結論

既存6テーブルへ影響を与えず、カテゴリ専用の10テーブルを追加する。
サーバーへコードを反映し、SCPで転送したJSONを投入すれば登録できる。
この変更はDBと投入ツールの準備まで。画面・API・COCO側のカテゴリは変更しない。
実際のサーバーDBへの適用・SCP転送はまだ行っていない。

## 分離する理由

- 内部IDは自動採番。元の1〜256やCOCOの実IDとは別物として扱う。
- 元カテゴリ名は利用者が提示した英語表記を保持する。40と67のomeletのような同名も別IDで登録する。
- 階層マスタは名称・説明を保持し、メインは各マスタのIDを参照する。
- 元IDは分類体系ごとに一意。有効な置換対応は元カテゴリにつき一つ。
- 未提示の分類を推測で作成しない。未対応は対応表の行がない状態で表す。

## ファイルとテーブル

| ファイル | 内容 |
| --- | --- |
| `sql/006_create_categories.sql` | MySQL用の10テーブル追加DDL |
| `backend/app/db/category_schema.py` | SQLAlchemyのスキーマ定義。既存アプリ用初期化とは独立 |
| `data/categories/source_names.txt` | 元カテゴリ256件。行番号が外部ID。並べ替え禁止 |
| `data/categories/classifications.tsv` | 最初に提示された分類41行、説明、対応先階層 |
| `data/categories/categories.json` | サーバー投入用データ。上記2ファイルから生成 |
| `data/categories/categories.json.sha256` | JSON転送後の同一性確認用 |
| `scripts/import_categories.py` | 生成・検証・追加テーブル作成・投入 |

| テーブル | 用途・主要制約 |
| --- | --- |
| `category1_master`〜`category6_master` | 各階層のID、code、name、description、sort_order |
| `food_categories` | 主キーfood_category_id、code、category1_id〜category6_id。6だけNULL可 |
| `category_sources` | 分類体系のcode、name、version。異なる版は異なるcodeで登録 |
| `source_categories` | 分類体系内の外部IDと元名称。分類体系＋外部IDが一意 |
| `category_replacement_mappings` | 元カテゴリ、分類行、target_level（5/6）。有効な元カテゴリごとに一意 |

全テーブルにcreated_at、updated_at、deleted_atを持ち、日時はUTCのタイムゾーンなしDATETIME。
InnoDB / utf8mb4 / utf8mb4_unicode_ci。外部キーは削除・更新ともRESTRICT。
category6がNULLでも同一の分類行を二重登録できないよう、生成列category6_keyを使用する。
対応表は生成列active_source_keyで有効行だけ一意にし、論理削除した旧対応を保持できる。
同じマスタや分類行を再利用し、説明が異なる場合は投入前に競合として拒否する。
取り込み時に、階層6を指す対応にはcategory6が存在することを検証する。
この条件はテーブルをまたぐためDBのCHECKでは保証していない。データ投入は本ツール経由とする。

管理codeは階層・名称から生成する安定したハッシュ値。名前が同じマスタは共有する。
同じ階層に同名で意味が異なる分類を追加する場合や名称変更の場合は、codeを保持する更新機能を先に追加する。
今回のツールは追加・一致確認専用で、既存行の更新・削除はしない。

## 初期データの詳細

- 元カテゴリ：256件（外部ID 1〜256）。名称の綴りや大文字小文字を補正しない。
- メインの分類行：41件。置換対応：41件。未対応：215件。
- 元の分類表のうどん19→20、天ぷらうどん20→21を、今回の元表に従って訂正。
- rootの末尾にあった空白を除去。未記入の説明はNULL。
- ID38のsausageやID43以降の分類は未提示のため対応を作らない。
- ID5・6・16・17・19はcategory6が存在しても、元の表の指定どおりtarget_level=5を保持。
- ID8の名称はchicken rice、利用者による分類名はチキンピラフとして、そのまま分離して保持。
- この256件をCOCOの実カテゴリIDとして自動的に扱わない。実連携にはCOCO実IDとの照合が別途必要。
- 既存の対応表JSONとは形式が異なる。今回のJSONをCOCOのCATEGORY_REVIEW_CATALOGへ設定しない。

## ローカルで準備する

backendイメージに既存requirements.txtのSQLAlchemy・PyMySQLが含まれていれば追加ライブラリ不要。
`data/`はGit管理対象外。JSON・SHA256・元資料2ファイルは作業PCの`data/categories/`に保存してあり、SCPで別送する。
通常はこのPCに保存されたJSONと、リポジトリに保存されたDDLをそのまま使える。
サーバーへclone/pullしただけではデータは配置されないため、次のSCP手順を実施する。
TSVや元名称を編集した場合のみ、リポジトリのルートで次を実行する。

```powershell
docker compose run --rm --no-deps -v "${PWD}:/source" backend python /source/scripts/import_categories.py --build-bundle
```

JSON・SHA256・DDLが再生成され、DB接続なしで検証される。
今後も元カテゴリの名称ファイルの途中に行を挿入しない。
新しい元分類体系はJSON内のsource.code・versionを変更して別体系として投入する。

## SCPによるデータ転送

以下の`USER`・`HOST`は実際のSSH接続先へ置き換える。
サーバー側のコードは、今回の変更をGitで確定・マージ後、サーバーでpullしておく。
`.env`はサーバーにある既存の設定を使用し、転送物へ含めない。

サーバーで受け取り先を作成する。

```bash
mkdir -p /srv/check_annotator/imports/categories
```

ローカルのリポジトリ直下から転送する。

```powershell
scp data/categories/categories.json data/categories/categories.json.sha256 USER@HOST:/srv/check_annotator/imports/categories/
```

Gitを使わず初期DDLも転送する場合は次を追加する。投入スクリプトとbackendコードは別途同じ版を配置する。

```powershell
scp sql/006_create_categories.sql USER@HOST:/srv/check_annotator/imports/categories/
```

## サーバーで読み込む

前提：MySQL 8.0.16以上、既存DB check_annotator、Docker Compose、サーバー用.env。
新規DBの場合は先に`docs/DB初期化.md`の手順で既存6テーブルを作成し、その後この手順を実行する。
既存DBには全体初期化スクリプトを再実行しない。
DBユーザーにはSELECT・INSERT、および初回のCREATE・REFERENCES権限が必要。
通常の投入でUPDATE・DELETE・DROPは使用しない。作業前に通常のDBバックアップを取得する。

```bash
cd /srv/check_annotator/imports/categories
sha256sum -c categories.json.sha256
cd /srv/check_annotator
docker compose build backend
```

まず検証する。これはDBへ接続しない。

```bash
docker compose run --rm --no-deps -v "$PWD:/source:ro" \
  backend python /source/scripts/import_categories.py \
  --data /source/imports/categories/categories.json
```

出力件数はsource_categories=256、food_categories=41、mappings=41、unmapped=215。
`.env`のDB_HOST・DB_NAME（または優先されるDATABASE_URL）が対象DBを指すことを確認する。
初回は次の1コマンドで、初期DDLと同じ構造を作成してから転送データを登録する。

```bash
docker compose run --rm --no-deps -v "$PWD:/source:ro" \
  backend python /source/scripts/import_categories.py \
  --data /source/imports/categories/categories.json --apply --create-schema
```

DDLをMySQLクライアントで適用済みの場合、または再投入・分類追加の場合は、`--create-schema`を外す。

```bash
docker compose run --rm --no-deps -v "$PWD:/source:ro" \
  backend python /source/scripts/import_categories.py \
  --data /source/imports/categories/categories.json --apply
```

同じファイルの再投入では既存行の内容を照合して重複登録を防止する。
競合時は上書きせず、今回のデータ変更全体をロールバックする。
投入処理間はMySQLの名前付きロックで排他制御する。
既存のタスク・ユーザー・進捗・コメント、COCO側の画像や矩形は変更しない。

確認用SQL（初期投入直後の期待件数）：

```sql
SELECT COUNT(*) FROM source_categories; -- 256
SELECT COUNT(*) FROM food_categories; -- 41
SELECT COUNT(*) FROM category_replacement_mappings WHERE deleted_at IS NULL; -- 41
SELECT s.external_category_id, s.name
FROM source_categories s
JOIN category_sources c ON c.category_source_id = s.category_source_id
LEFT JOIN category_replacement_mappings m
  ON m.source_category_id = s.source_category_id AND m.deleted_at IS NULL
WHERE c.code = 'original-food-256-v1' AND m.mapping_id IS NULL
ORDER BY s.external_category_id; -- 215件
```

## 失敗した場合

OperationalErrorの場合は、更新せずに次のコマンドで接続と作成済みテーブルを確認する。

```powershell
docker compose run --rm --no-deps -v "${PWD}:/source:ro" backend python /source/scripts/import_categories.py --check-db
```

接続先の表示に加え、失敗時はMySQLのエラー番号と対処の目安を表示する。
認証情報・SQL本文・ドライバーの生エラーメッセージは出力しない。
--check-dbはSELECTとメタデータ参照のみを行い、DDL作成権限やINSERT権限までは検証しない。
接続先がサーバーの場合、この確認もサーバーDBへの参照となる。
MySQLエラー2003はネットワークや接続許可、1045は認証、1044/1142は権限を確認する。

データは単一トランザクションで登録するが、MySQLのDDLはロールバックできない。
テーブル作成後に投入が失敗した場合、空のカテゴリテーブルは残す。
作成途中の失敗では一部テーブルが残る可能性があるため、状態を確認して不足DDLだけを適用する。
既存テーブルを自動削除しない。全10テーブルを揃えてから`--create-schema`なしで再実行する。
同じ名前の既存テーブルがあれば列・型・一意制約・外部キー等を検証し、不一致時は停止する。

## 検証と次の作業

`python -m pytest tests/test_categories.py -q`で、入力・重複・参照制約・NULL時の一意性・再投入・ロールバックを確認する。
MySQL 8.0.44と8.4.7の実サーバーをローカルに隔離して起動し、実コマンド・配布DDLで検証済み。
初回作成、SQLファイル経由の作成、256件と分類41件の投入、再投入の同一性、後続分類追加、
競合時の全データ行ロールバック、NULL分類の一意性・外部キー・CHECK制約、論理削除後の再対応を確認。
既存6テーブルは実際の初期SQLで作成し、担当・タスク・コメントの検証データも登録したうえで、
投入前後のテーブル定義・全行の一致を確認している。MySQLのロールバックでは採番値に欠番が生じ得るが、データ行は復元される。
この検証で、文字列型の反映結果に付くCOLLATEを型不一致と誤判定する不具合を修正した。
学内サーバーには接続・変更していない。8.0.16は機能上の最低条件であり、今回実行検証した版は8.0.44と8.4.7。

同じ実MySQL検証は、学外でもDocker Desktopだけで実行できる。
新しくcloneした環境では、先にJSONとSHA256を`data/categories/`へ配置する。
データなしの通常テストは実データ依存部分をスキップし、実MySQL検証はデータ欠落時に失敗する。
専用Composeは通常のDB接続設定を使用せず、本番と別のプロジェクト名、使い捨てDB、ホストへのポート公開なしで起動する。
次のコマンドはリポジトリ直下のPowerShellで実行する。

```powershell
docker compose -f compose.categories-test.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.categories-test.yaml down
```

MySQL 8.4.7で再現する場合：

```powershell
$env:CATEGORY_TEST_MYSQL_IMAGE = 'mysql:8.4.7'
docker compose -f compose.categories-test.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.categories-test.yaml down
Remove-Item Env:CATEGORY_TEST_MYSQL_IMAGE
```

通常のテストは`CATEGORY_TEST_MYSQL_URL`未設定時に実MySQL用テストをスキップする。
この専用Composeは設定済みのため、スキップせずに実行する。
この作業環境にはDockerがないため、実検証は同じテストを公式ZIP配布のMySQLで実行した。
Docker専用Compose自体の起動確認は未実施。

次は未対応215件の分類追加と、COCO実カテゴリIDへの対応・API接続を行う。
今回の実装だけでは画面上のカテゴリ置換データ元は切り替わらない。

MySQL仕様の参照先：
- [CHECK制約（8.0.16以降）](https://dev.mysql.com/doc/refman/8.0/en/create-table-check-constraints.html)
- [生成列](https://dev.mysql.com/doc/refman/8.0/en/create-table-generated-columns.html)
- [DDLの暗黙コミット](https://dev.mysql.com/doc/refman/8.0/en/implicit-commit.html)
