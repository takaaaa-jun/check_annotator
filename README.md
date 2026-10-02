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
- `AUTH_SECRET_KEY`: JWT署名用の十分に長いランダム文字列
- `CORS_ORIGINS`: フロントエンドのURL。複数の場合はカンマ区切り

接続先を変更するときは `.env` の値を置き換え、Docker Composeのサービスを再作成する。`.env` は認証情報を含むためGitへコミットしない。

##

Copyright &copy; 2026 Jun Takahashi, Yamazaki Lab, University of Niigata. All rights reserved.
