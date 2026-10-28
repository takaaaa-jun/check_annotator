# アノテーションを行うときに，進捗管理を行うWebアプリケーション

## 目的

- 複数人でアノテーションを行う場合，完了紙官僚化の進捗共有や各画像に対して変更したのかどうか，アノテーションルールの共有など，口頭のコミュニケーションでは共有が難しい場面がある．そこで，アノテーションの作業進捗を管理できるダッシュボードを作成することで，誰でも進捗管理が簡単に行えるアプリの構築を目指す．

## 機能要件

- クライアントサイド
  - ユーザ側
    - ※/check_annotator/から始まる
    - /login -> ログインページ（ユーザ名とパスワード）
    - /my_page/{user_id} -> マイページのダッシュボード(アノテーションの進捗管理可能)
    - my_page/{user_id}/task_list -> 各アノテーションタスクを表示する画面
    - my_page/{user_id}/task/{group_id} -> アノテーションの作業進捗管理の詳細画面(状態管理やコメント入力欄)
    - 状態毎のフィルタ
  - 管理側
    - /adminpage/task_list -> 全てのアノテーションタスクの管理画面
    - admin/task/{group_id}/{image_id}/post -> コメント返信の入力欄
- サーバサイド
  - ユーザ側
    - GET /user -> ユーザ情報の取得と認証
    - POST /user -> ユーザの登録
    - GET /my_page/{user_id} -> マイページ情報の取得
    - GET my_page/{user_id}/task_list -> ダッシュボード上に表示
    - GET my_page/{user_id}/task/{group_id} -> 各タスクの詳細
    - POST my_page/{user_id}/task/{group_id}/{image_id}/post -> 状態とコメントの送信
  - 管理者側
    - GEt /adminpage -> 管理者画面
    - GEt /adminpage/task_list -> ダッシュボード上に表表示
    - POST admin/task/{group_id}/{image_id}/post -> コメントの送信

## 非機能要件

- ページが遷移して表示が完了するまでは1秒以内(最大10人のアクセスを想定) [1]
- コメント入力以外はクリック操作のみで作業が完了
- 1日1回決まった時刻にバックアップを行う（作業後に簡単に自動バックアップを停止できること）
- コメントを送ったら管理者に通知

## 参考にしたサイト

- [1] [Webサイトの応答時間](https://u-site.jp/alertbox/20100621_response-times)

## 技術スタック

- 画像データだけで約3万件あるので，高速に処理を行える言語

- クライアントサイド
  - language: TypeScript
  - framework: Next.js
  - library: react
- サーバサイド
  - language: Python
  - framework: FastAPI
- DB
  - language: MySQL

## 環境設定

`.env.example` を `.env` へコピーし、接続先に合わせて次の値を設定する。

- `DB_HOST`: データベースサーバーのIPアドレスまたはホスト名
- `DB_PORT`: MySQLのポート番号
- `DB_NAME`: 使用するデータベース名
- `DB_USER`: データベースユーザー名
- `DB_PASSWORD`: データベースパスワード
- `DB_SSL_CA`: SSL接続で必要な場合のCA証明書パス
- `DB_CONNECT_TIMEOUT`: MySQL接続のタイムアウト秒数（既定値: 5）
- `DB_POOL_RECYCLE`: 接続プールを再作成するまでの秒数（既定値: 1800）
- `AUTH_SECRET_KEY`: JWT署名用の十分に長いランダム文字列
- `CORS_ORIGINS`: フロントエンドのURL。複数の場合はカンマ区切り

接続先を変更するときは `.env` の値を置き換え、Docker Composeのサービスを再作成する。`.env` は認証情報を含むためGitへコミットしない。

バックエンドの稼働だけを確認する場合は `GET /health`、データベースへの疎通まで確認する場合は `GET /health/database` を使用する。Docker Composeのヘルスチェックは後者を使用するため、MySQLへ接続できないバックエンドは正常状態にならない。

## 開発とサーバー反映の方針

ローカルで開発・確認し、サーバーにはGitで確定した変更をcloneまたはpullして本番用Composeで反映する。サーバーで開発用Composeを起動する必要はない。開発用Composeはローカルのホットリロードと動作確認に使用するため残す。

APIのURLと処理は共通にし、backendが使うデータ元を切り替える。ブラウザからDBへ直接接続する構成にはしない。

| 実行場所・用途 | Composeの指定順 | データ元 | ブラウザのアクセス先 |
| --- | --- | --- | --- |
| ローカル・DB確認 | 共通 → dev | `.env`に指定したサーバーのMySQL | `http://localhost/check_annotator/login` |
| ローカル・モック確認 | 共通 → dev → mock | JSONから初期化した専用SQLite | 同上 |
| サーバー配信 | compose.yaml（共通 → prod） | サーバー用`.env`に指定したMySQL | `http://<サーバー>/check_annotator/login` |

`.env`は各環境に個別に用意する。DB確認には`DB_HOST`・`DB_PORT`・`DB_NAME`・`DB_USER`・`DB_PASSWORD`を設定する。`DATABASE_URL`が設定されている場合はそちらが優先される。サーバーDBへ接続するローカル環境では、そのサーバーに届くホスト名またはIPを指定する。DBモードでの更新操作は接続先DBへ保存されるため、開発用DBを使用する。

認証用の`AUTH_SECRET_KEY`はモックでも必要。秘密値を含む`.env`はGitへ登録せず、サーバーにも別途作成する。サーバーでは`APP_ENV=production`・`APP_DATA_MODE=database`とし、`CORS_ORIGINS`を実際にブラウザで開くオリジンへ合わせる。

## 簡単な起動・停止

Docker Compose 2.20.0以降を使用する。Docker Desktopとgatewayを先に起動し、各環境に`.env`を用意する。

```powershell
# 本番用（MySQL）: compose.yamlが共通＋本番設定を読み込む
# 初回はイメージが自動ビルドされる
docker compose up -d

# モック用（SQLite・ホットリロード）
docker compose -f compose.mock.yaml up -d

# 本番用のログ確認・停止
docker compose logs --tail 100 backend frontend
docker compose down

# モック用のログ確認・停止
docker compose -f compose.mock.yaml logs --tail 100 backend frontend
docker compose -f compose.mock.yaml down
```

`-mock`はDocker Composeに存在しないため、モック用ファイルを`-f`で指定する。本番・モックは同じプロジェクト名とサービス名を使用し、コマンドを切り替えると同じアプリが再作成される。同時には起動しない。両モードのイメージ名を分け、開発用イメージが本番で使われることを防いでいる。コード更新・依存関係変更後は`up -d --build`で再ビルドする。`down -v`はモックの保存データも削除するため通常は使用しない。

本番用は`APP_ENV=production`・`APP_DATA_MODE=database`を固定する。モック用は開発モードと専用SQLiteを固定する。開発支援用の`workspace`サービスは`workspace`プロファイルに分離し、通常の起動では開始しない。Dev Containerでの明示的な起動は引き続き利用できる。

## ローカルで起動する（PowerShell）

Docker Desktopとgatewayを先に起動する。共有ネットワーク`shared-gateway-net`はgatewayと共通で使用する。gatewayが起動済みなら、アプリのリポジトリのルートで以下を実行する。

```powershell
# モックデータで開発する（初回・依存関係変更時は-Build）
.\scripts\dev-compose.ps1 -Mock -Build

# サーバーDBで確認する（接続先は.envで指定）
.\scripts\dev-compose.ps1 -Build
```

起動後は`http://localhost/check_annotator/login`へアクセスする。コードの変更は開発サーバーへ反映される。ローカルでもgatewayを経由し、ホストで公開するのはgatewayの80番のみとする。開発用・本番用ともfrontendは内部80番、backendは内部8000番を使用し、アプリ側の`ports`は指定しない。開発用設定はホットリロードとモック切り替えのために残すが、開発専用ポートは設けない。

コマンドを切り替えると同じローカルのfrontend・backendが再作成され、選択したデータ元が適用される。DB接続に失敗しても自動的にモックへ切り替えない。backendのヘルスチェックに成功するとfrontendが起動する。

モックは`backend/app/mock/data/`のJSONを元に、名前付きボリューム`backend-mock-data`内の`/data/check_annotator_mock.db`へ初期化する。通常の再起動では編集内容を保持する。モックデータを初期状態へ戻す場合のみ以下を実行する（モックの変更内容は失われる）。

```powershell
.\scripts\dev-compose.ps1 -Mock -Reset
```

起動スクリプトを使わない場合も、モック用設定を必ず最後に指定する。

```powershell
docker compose --env-file .env -f docker-compose.base.yaml -f docker-compose.dev.yaml -f docker-compose.mock.yaml up -d --build backend frontend
```

ログ確認・停止は、起動時と同じファイルの組み合わせで実行する。DBモードの場合は最後の`-f docker-compose.mock.yaml`を省略する。

```powershell
docker compose --env-file .env -f docker-compose.base.yaml -f docker-compose.dev.yaml -f docker-compose.mock.yaml logs --tail 100 backend frontend
docker compose --env-file .env -f docker-compose.base.yaml -f docker-compose.dev.yaml -f docker-compose.mock.yaml down
```

## サーバーで反映する

初回はリポジトリをcloneし、`.env.example`を参考にサーバー専用の`.env`を作成する。共有ネットワーク`shared-gateway-net`とgatewayを用意する。更新時は作業中の変更を確認してから、アプリのディレクトリで以下を実行する。

```sh
git pull --ff-only
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

設定検証に成功してから起動する。本番用と開発用・モック用の上書きファイルは同時に指定しない。既存のbackendは本番モードでのモック利用を拒否する。サーバーのfrontend・backendはホストへ直接ポート公開せず、gateway経由でアクセスする。

この手順はアプリの反映であり、DBの作成・スキーマ変更は別途管理する。コード更新だけならgatewayの再読み込みは不要。gatewayの設定も変更した場合は、gatewayディレクトリで`nginx -t`を実行し、成功後に再読み込みする。

Copyright &copy; 2026 Jun Takahashi, Yamazaki Lab, University of Niigata. All rights reserved.
