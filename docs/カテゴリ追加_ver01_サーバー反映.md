# カテゴリver01のサーバー反映手順

## 現在の状態（2026-11-26）

ローカルCOCO本体の4ファイルを修正し、ローカルMongoDBで検証済み。
この検証作業では共有DB・稼働サーバー・GitHubを変更していない。
前段の作業で共有MySQLは55対応へ更新済みのため、この手順でMySQLの再投入は行わない。
COCOのMongoDBへの同期は、以下をサーバーで実行するまで行われない。

対象は `/srv/coco-annotator` の `food_detection`（データセットID 2）。
既存の `CATEGORY_REVIEW_DATASET_ID=2` と `CATEGORY_REVIEW_CATALOG=` を維持する。

## 変更の理由

- 説明文の更新は、変更前JSONのチェックサム・現在の対応表バージョン・既存カテゴリの内容を照合してから行う。
- 同名の「焼きナス」をcategory5からcategory6へ追加できるよう、新規管理カテゴリの作成者を管理キーごとの名前空間に分ける。
- 選択肢から外す旧カテゴリは、変更前JSONと対応表の両方で識別できるものに限る。カテゴリ文書・旧ID・既存ボックスは保持する。
- 想定外の名前・親・説明・対応表バージョン・無関係なカテゴリは、従来どおり拒否する。

## 1. ローカルの変更をGitHubへ反映する（この作業では未実行）

COCOリポジトリの対象ファイル:

```text
backend/database/categories.py
backend/scripts/sync_categories.py
backend/webserver/util/category_sync.py
backend/tests/test_category_sync.py
```

作業ブランチで差分を確認し、この4ファイルをコミット・pushして、baseがmainのPRを作成する。
check_annotator側の更新スクリプト・テスト・本手順も、別リポジトリのPRとして必要に応じて反映する。
どちらも未コミットの変更があるため、git add . による一括追加は避ける。
`.env`・DBバックアップ・ローカル検証環境はコミットしない。

今回使うJSONは既存のGit対象外運用を維持する。Gitのpullだけではサーバーへ届かない。
転送用パッケージはローカルの `imports/categories/ver01-release.zip`。
中身は `taxonomy.json`、`previous-taxonomy.json`、`SHA256SUMS` の3ファイル。
MySQLの認証情報やDB全行のバックアップは含めない。

## 2. JSONをサーバーへ転送する

PowerShellで実行する。`takahashi@tiger` は実際に使用しているSSH接続先へ読み替える。

```powershell
scp C:\development\check_annotator\imports\categories\ver01-release.zip takahashi@tiger:~/category-ver01-release.zip
```

以降はサーバーのBashで実行する。各コマンドの成功を確認してから次へ進む。

```bash
mkdir -p "$HOME/category-ver01"
unzip "$HOME/category-ver01-release.zip" -d "$HOME/category-ver01"
cd "$HOME/category-ver01"
sha256sum -c SHA256SUMS

cd /srv/coco-annotator
git status --short
code_before=$(git rev-parse HEAD)
git switch main
git pull --ff-only origin main
docker compose build backend workers

mkdir -p datasets/.category-review/ver01
cp "$HOME/category-ver01/taxonomy.json" datasets/.category-review/ver01/taxonomy.json
cp "$HOME/category-ver01/previous-taxonomy.json" datasets/.category-review/ver01/previous-taxonomy.json
cp "$HOME/category-ver01/SHA256SUMS" datasets/.category-review/ver01/SHA256SUMS
cd datasets/.category-review/ver01
sha256sum -c SHA256SUMS
cd /srv/coco-annotator
```

git statusに未反映のローカル変更がある場合は、内容を確認してから進める。
check_annotator側もPRをマージした場合は、`/srv/check_annotator` でmainをpullする。
今回のCOCO修正はPythonだけなので、COCOフロントエンドのコード変更・再ビルドは不要。
過去の未反映PRが別にある場合は、そのPRの手順も適用する。

## 3. 保存・停止・MongoDBバックアップ

全員が編集内容を保存し、COCO編集画面を閉じる。
保存できていない画面を強制再読み込みして破棄しない。

```bash
cd /srv/coco-annotator
docker compose stop backend frontend workers

backup_dir="backups/category-ver01-$(date +%Y%m%dT%H%M%S)"
mkdir -p "$backup_dir"
git rev-parse HEAD > "$backup_dir/code-after-update.txt"
printf '%s\n' "$code_before" > "$backup_dir/code-before-update.txt"
docker compose exec -T database mongodump --archive=/tmp/category-ver01-before.archive --gzip
docker compose cp database:/tmp/category-ver01-before.archive "$backup_dir/mongodb-before.archive.gz"
test -s "$backup_dir/mongodb-before.archive.gz"
cp -a datasets/.category-review "$backup_dir/category-review-files"
printf '%s\n' "$backup_dir"
```

MongoDBに別の書き込みクライアントがある場合は、それも停止してからバックアップする。
バックアップ保存に失敗した場合は同期しない。

## 4. 参照のみのプレビュー

```bash
docker compose run --rm --no-deps -v "$PWD/backend:/source:ro" \
  backend python /source/scripts/sync_categories.py \
  --data /datasets/.category-review/ver01/taxonomy.json \
  --previous-data /datasets/.category-review/ver01/previous-taxonomy.json
```

旧46カテゴリ・42候補を同期済みの255元カテゴリ構成から更新する場合の期待値:

| 項目 | 件数 |
| --- | ---: |
| sourceRows | 256 |
| actualSourceCategories | 255 |
| targetCategories | 59 |
| mappings | 54 |
| replacementChoices | 55 |
| ambiguousMappings | 1 |
| createCategories | 14 |
| updateDescriptions | 15 |
| retireCategories | 1 |

`createCategories`・`updateDescriptions`・`retireCategories` は更新状況により減る。
適用済みならすべて0。まだ旧カテゴリを同期していない環境では初期作成件数になる。
256元カテゴリを保持する別構成ではactualSourceCategories=256、mappings=55になる。

「Previous blueprint does not match the active catalog version」等のエラーが出た場合は停止する。
同梱の変更前JSONはローカルに保存していた旧MySQLデータから再生成したものであり、
稼働サーバーの実際の旧対応表と一致することを、このプレビューで必ず確認する。
エラーを避けるためにJSONのversionを書き換えたり、--previous-dataを外したりしない。
使用中の旧エクスポートが別の場合は、その原本を確認してから再計画する。

## 5. プレビュー成功後に適用・再開

```bash
docker compose run --rm --no-deps -v "$PWD/backend:/source:ro" \
  backend python /source/scripts/sync_categories.py \
  --data /datasets/.category-review/ver01/taxonomy.json \
  --previous-data /datasets/.category-review/ver01/previous-taxonomy.json \
  --apply
```

`applied: true`、targetCategories=59、replacementChoices=55を確認してから再開する。

```bash
docker compose up -d backend frontend workers
docker compose ps
```

画像や既存ボックスを一括で置き換える処理ではない。
COCOで新規付与のカテゴリが59件になり、旧「焼きナス」の付与済みボックスが残ることを確認する。
check_annotatorのカテゴリ確認で43「シチュー」、55「唐揚げ」、33「焼き野菜」が候補になることを確認する。
omeletは「オムレツ」「だし巻き卵」の明示選択を引き続き必要とする。

## 途中失敗・復旧

同期はMongoDB単一ドキュメントの条件付き更新で対応表を有効化する。
途中失敗時に説明文の一部更新・作成済みカテゴリが残る場合はあるが、半端な対応表は有効化しない。
原因を解消後、同じ新旧JSONで再実行できる。同期ロックを無条件で消したり、カテゴリを削除したりしない。
失敗後にサービスを再開するかどうかは、現在の対応表とロック状態を確認して判断する。

旧JSONを新JSONの代わりに渡すだけでは復旧にならない。
完全復旧が必要なら、すべての書き込み元を止めた状態で保存したMongoDBバックアップとコードを復旧する。
同期後に新しいアノテーション作業が行われている場合、DB全体の復元はその作業を失うため、差分を確認してから行う。

## ローカル検証結果

- COCO本体の同期・CLI・実API: 33件成功（ローカルMongoDB 4.4.29、127.0.0.1:27028/category_sync_tests）。
- 既存の置換・競合検証: 21件成功（同ローカルMongoDBのcategory_review_tests）。
- check_annotatorのカテゴリ関連: 26件成功。
- 現在のフロントエンドの本番ビルド: 成功。
- Chromeで最新カテゴリ確認画面を操作し、シチュー・唐揚げ・焼き野菜・旧焼きナスの表示を確認。
- キャンセル時はDB差分なし。確定時はボックス90003のみシチューへ変更。他6件・座標・独自メタデータの保持をDB照合で確認。

実モデル・実APIをローカル検証用のFlaskアプリへ登録して確認した。
テスト利用者の認証と画像SVGはローカル専用の検証用実装。
Docker Compose全体・本番認証・COCOの全描画ツールの動作確認を意味しない。
この検証では共有MySQLへ接続せず、サーバー同期・GitHubへのpushやPR作成も実行していない。
