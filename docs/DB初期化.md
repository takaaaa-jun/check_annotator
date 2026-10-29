# MySQLの初期化（イシュー46）

対象DBは `check_annotator`。既存テーブルが1つでもあれば停止し、削除・上書きしない。
初期化中はアプリを停止し、管理者以外がこのDBへDDLや書き込みを実行しないこと。

## 作成内容

`sql/000` はDB作成、`001`・`003`・`004` は6テーブルのDDL、
`002` はadmin/workerロールと8ユーザー、`005` は状態4種類を登録する。
日時はアプリと同じUTCのタイムゾーン情報なしDATETIMEで保存する。
全テーブルをInnoDB / utf8mb4 / utf8mb4_unicode_ciで統一する。
`states` はイシュー46のモデル一致要件を優先し、`VARCHAR(20)` とする。
仕様書画像にある `sort_order` は現行モデルにないため作成しない。
グループ名・担当・画像IDは未指定のため、groups/tasks/commentsの実データは登録しない。
ユーザーのパスワードはログインできない `!`。初期化後に下記の手順で設定する。

## ログイン用パスワードの設定

まずはローカルのMySQLを対象に、ユーザーごとに設定・ログインを確認する。
DB初期化とは別の操作であり、DBの作り直しやアプリの停止は不要。
実行するDBユーザーには users のSELECT・UPDATE権限が必要。
接続先は `.env` の `DATABASE_URL`（優先）または `DB_*` に従う。
ローカルでコマンドを実行しても接続先がサーバーならサーバーDBを更新するため、
ローカル検証用MySQLを指定し、表示された接続先を確認する。
SQLiteモック用の `compose.mock.yaml` はこの手順では使わない。

WindowsのPowerShellで、Docker Desktopを起動して次を実行する。

```powershell
cd C:\development\check_annotator
docker compose run --rm --no-deps -v "${PWD}:/source:ro" backend python /source/scripts/set_user_password.py takahashi
```

Linuxサーバーへ反映する段階では、サーバー用 `.env` を用意して次を実行する。

```bash
cd /srv/check_annotator
docker compose run --rm --no-deps -v "$PWD:/source:ro" \
  backend python /source/scripts/set_user_password.py takahashi
```

1. 表示された接続先・ユーザー名を確認し、DB名 `check_annotator` を入力する。
2. 8文字以上のログイン用パスワードを2回入力する（画面には表示されない）。
3. 設定完了の表示後、ローカルは `http://localhost/check_annotator/login`、
   サーバーは `http://<サーバー>/check_annotator/login` でログインする。
   アプリ起動時と同じDBを使うこと。ブラウザでの確認にはgatewayとアプリの起動も必要。

ユーザー名は `takahashi`（管理者）、`kimura`・`imai`・`umehara`・`endo`・`sato`・`tabe`・`matunaga`（作業者）。
作業者にも設定する場合はコマンド末尾のユーザー名を変更し、個別のパスワードを設定する。
パスワードをコマンド引数やSQLファイル、チャットに記載しないこと。
アプリと同じArgon2ハッシュを保存し、平文やハッシュは出力しない。
このコマンドは初期値 `!` のユーザーだけが対象。設定済み・削除済みユーザーは更新しない。
DB初期化専用パスワードやMySQL接続パスワードとは別の値を用意する。

## タスクの初回分配

`scripts/assign_tasks.py` は指定の画像範囲を1グループずつ作成し、画像ID 1〜30000を担当者へ割り当てる。
グループ名は `00001-01000` の形式。画像IDは整数として保存し、全タスクを「未着手」で登録する。
内訳はkimura 7700件、imai 5300件、その他5名は各3400件、合計34グループ。
既存グループ・タスクがあれば停止し、途中失敗時はトランザクション全体を取り消す。

PowerShellで内容確認・登録を行う。

```powershell
docker compose run --rm --no-deps -v "${PWD}:/source:ro" backend python /source/scripts/assign_tasks.py
docker compose run --rm --no-deps -v "${PWD}:/source:ro" backend python /source/scripts/assign_tasks.py --apply
```

## 必要な環境と権限

- Docker EngineとComposeが動作するサーバー。Pythonの依存関係はbackendイメージを使う。
- `.env` にサーバー用DB接続情報を設定し、`DB_NAME=check_annotator` とする。
  `DATABASE_URL` が設定されていればそちらが優先される。
- DB接続ユーザーには対象DBの CREATE / DROP / REFERENCES / SELECT / INSERT / UPDATE / DELETE が必要。
  DB自体を作成する場合も対象DBに対するCREATE権限が必要。
  DROPは途中失敗時に今回作成したテーブル・DBを復旧するために使う。
  `information_schema` で対象DBのメタデータを参照できること。
- `AUTH_SECRET_KEY` を設定し、`APP_DATA_MODE=database` を使用する。
- TLSを使う場合はCA証明書をコンテナへマウントし、`DB_SSL_CA` を設定する。
- 通常運用のアプリ用DBユーザーとは別に初期化専用ユーザーを使うことを推奨。

## 推奨手順：確認付きスクリプト

以下はLinuxサーバーのシェルで、リポジトリのルートから実行する。
まずアプリを停止し、初期化スクリプト実行用イメージをビルドする。

```bash
docker compose stop frontend backend
docker compose build backend
```

初期化専用パスワードはDBログイン用とは別に管理者が用意する。
次のコマンドで非表示入力し、確認用SHA-256を取得する。
パスワードそのものは引数・履歴・出力に載せない。

```bash
docker compose run --rm --no-deps backend python -c 'import getpass,hashlib; print(hashlib.sha256(getpass.getpass("初期化専用パスワード: ").encode("utf-8")).hexdigest())'
```

表示された確認用ハッシュを次のコマンドで非表示入力し、
初期化スクリプトへ環境変数として渡す。`.env` への追加は不要。

```bash
read -rs -p '確認用SHA-256: ' DB_INIT_PASSWORD_SHA256; echo
export DB_INIT_PASSWORD_SHA256
docker compose run --rm --no-deps -e DB_INIT_PASSWORD_SHA256 \
  -v "$PWD:/source:ro" backend python /source/scripts/initialize_database.py
unset DB_INIT_PASSWORD_SHA256
```

表示されたホスト・ポート・DB名を確認する。
初期化専用パスワードを非表示入力し、続いて `check_annotator` を再入力する。
環境変数 `DB_INIT_PASSWORD` からの入力も可能だが、コマンドに平文で指定しないこと。
いずれかが一致しなければDBへ接続する前に停止する。

成功時は次を自動確認する。

- テーブル・カラム・型・NULL可否・AUTO_INCREMENT・主キー
- UNIQUE・外部キーの更新/削除動作・検索インデックス・照合順序
- ロール2種類、状態4種類、ユーザー8名と権限
- 不正な外部キーによるINSERTの拒否（検証データは保存しない）
- アプリ内の `/health/database` が200、未認証の既存認証APIが401
- メモリ上のJWTで認証したユーザー情報・グループAPIが200（パスワードやDBデータは変更しない）

API確認は同じDB設定のアプリをプロセス内で実行する。
稼働中コンテナやgateway経由のHTTP疎通は、起動後に別途確認する。

```bash
docker compose up -d --build
docker compose ps
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health/database').read().decode())"
```

## 失敗時・再実行

- 確認入力の不一致や既存テーブル検出時はDBを変更しない。初期化ツールは既存DBの再作成機能を提供しない。
- MySQLのDDLは暗黙コミットされるため、途中失敗時は今回作成したテーブルだけを逆順に削除する。
  DB自体も今回新規作成した場合のみ削除する。既存の空DBは残す。
- 接続断・サーバー停止・プロセス強制終了では自動復旧できない場合がある。
  復旧失敗の表示があれば、管理者が `SHOW TABLES FROM check_annotator` と `SHOW CREATE TABLE` で確認する。
  バックアップと照合し、今回作成したものだけを整理してから再実行する。
- 詳細なDB例外は接続情報流出を避けて出力しない。接続先・権限・証明書を管理者が確認する。
