# バックエンドの仕様書

## API構成

- POST /api/auth/login
  - ログインの情報送信

- POST /api/auth/logout
  - 認証Cookieを削除してログアウトする

- GET /api/users/me
  - ログインしたユーザの情報を取得

- GET /api/users/{user_id}/groups
  - ユーザの担当しているグループ一覧を取得

- GET /api/users/{user_id}/groups/{group_id}/tasks
  - 各グループ内のタスクを表示

- PATCH /api/tasks/{task_id}/state
  - タスクの状態変更

- POST /api/tasks/{task_id}/comments
  - コメント投稿

- GET /api/tasks/{task_id}/comments
  - 各タスクのコメント一覧取得

## APIのデータ構成

- POST /api/auth/login
  - 処理手順
    1. user_nameに一致するユーザを取得する
    2. deleted_at IS NULLであることを確認する
    3. 入力されたパスワードを照合する
    4. users.login_atを更新する
    5. 署名付き認証トークンを生成する
    6. トークンをCookieへ設定する
    7. ユーザ情報を返す

  - リクエスト想定

    ```json
    {
        "user_name": "takahashi",
        "password": "test1"
    }
    ```

  - 成功レスポンス

    ```json
    {
        "user": {
            "user_id": 1,
            "user_name": "takahashi",
            "role_name": "worker"
        }
    }
    ```

  - ステータス
    - 200: ログイン成功
    - 401: ユーザ名またはパスワード不正
    - 422: 入力値が不正
    - 500: サーバ内部エラー

- POST /api/auth/logout
  - 処理
    1. 認証Cookieを削除する
    2. レスポンス本文を返さず終了する

  - Cookie削除

    ```http
    Set-Cookie: access_token=; Max-Age=0; Path=/; SameSite=Lax
    ```

  - ステータス
    - 204: ログアウト成功

- GET /api/users/me
  - 成功レスポンス

    ```json
    {
        "user_id": 1,
        "user_name": "takahashi",
        "role_id": 1,
        "role_name": "worker",
        "login_at": "2026-09-30T07:30:00Z"
    }
    ```
  
  - 処理
    1. Cookieからaccess_tokenを取得する
    2. トークンの署名と有効期限を確認する
    3. トークンからuser_idを取得する
    4. usersテーブルからユーザを取得する
    5. deleted_at IS NULLであることを確認する
    6. ユーザ情報を返す
  
  - ステータス
    - 200: 取得成功
    - 401: Cookieがない、トークンが無効，期限切れ，ユーザが論理削除済み
    - 500: サーバ内部エラー

- GET /api/users/{user_id}/groups
  - 各グループの進捗情報を表示するために，担当グループと状態毎の件数を返す

  - 自分のuser_idの情報のみを取得

  - 管理者はすべてのユーザの進捗を閲覧可能

  - 成功レスポンス

    ```json
    {
        "user": {
            "user_id": 1,
            "user_name": "takahashi"
        },
        "groups": [
            {
                "group_id": 1,
                "group_name": "グループ1",
                "image_id_min": 1,
                "image_id_max": 1000,
                "total_count": 1000,
                "state_counts": [
                    {
                        "state_id": 1,
                        "state_name": "未着手",
                        "count": 500
                    },
                    {
                        "state_id": 2,
                        "state_name": "完了",
                        "count": 400
                    },
                    {
                        "state_id": 3,
                        "state_name": "付与予定ラベル",
                        "count": 80
                    },
                    {
                        "state_id": 4,
                        "state_name": "コメント",
                        "count": 20
                    }
                ]
            }
        ]
    }
    ```
  
  - ステータス
    - 200: 取得成功
    - 401: Cookieがない，トークンが無効，期限切れ
    - 404: トークンのユーザが存在しない
    - 500: サーバ内部エラー

- GET /api/users/{user_id}/groups/{group_id}/tasks
  - ページネーション
    - 例）GET /api/users/1/groups/1/tasks?state_id=1&page=1&page_size=100
    - ?state_id=1: 状態でフィルタをかける場合に使用
    - &page=1: 1以上
    - &page_size=100: 10, 50, 100を選択可能

  - 成功レスポンス

    ```json
    {
        "group": {
            "group_id": 1,
            "group_name": "グループ1",
            "user_id": 1,
            "user_name": "takahashi"
        },
        "tasks": [
            {
                "task_id": 1,
                "image_id": 1,
                "state_id": 1,
                "state_name": "未着手",
                "updated_at": "2026-09-30T07:30:00Z"
            },
            {
                "task_id": 2,
                "image_id": 2,
                "state_id": 2,
                "state_name": "完了",
                "updated_at": "2026-09-30T07:32:00Z"
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 100,
            "total": 1000,
            "total_pages": 10
        }
    }
    ```

- PATCH /api/tasks/{task_id}/state
  - リクエスト想定
  
    ```json
    {
        "state_id": 2
    }
    ```

  - 成功レスポンス

    ```json
    {
        "task_id": 1,
        "group_id": 1,
        "image_id": 1,
        "state_id": 2,
        "state_name": "完了",
        "updated_at": "2026-09-30T07:35:00Z"
    }
    ```

  - 処理の流れ
    1. ログイン状態を確認
    2. タスクを取得(deleted_at IS NULL)
    3. ログインユーザが担当グループに該当しているかを確認
    4. state_idの存在確認
    5. tasks.state_idを更新
    6. 更新日時を更新
    7. 更新後のタスクを返す

  - ステータス
    - 200: 更新成功
    - 401: 未認証
    - 403: 担当外のタスク
    - 404: タスクまたは状態が存在しない
    - 422: クエリパラメータが不正
    - 500: サーバー内部エラー

- POST /api/tasks/{task_id}/comments
  - リクエスト想定

    ```json
    {
        "content": "付与予定ラベル: tuna",
        "parent_id": null
    }
    ```

  - 成功レスポンス

    ```json
    {
        "comment_id": 1,
        "task_id": 1,
        "user_id": 1,
        "user_name": "takahashi",
        "parent_id": null,
        "content": "付与予定ラベル: tuna",
        "created_at": "2026-09-30T07:30:00Z"
    }
    ```

  - ステータス
    - 201: コメント作成成功
    - 401: 未認証
    - 403: コメント投稿権限なし
    - 404: タスクまたは親コメントが存在しない
    - 422: コメント本文が空、長すぎる、形式不正

- GET /api/tasks/{task_id}/comments
  - 成功レスポンス

    ```json
    {
        "task_id": 1,
        "comments": [
            {
            "comment_id": 1,
            "user_id": 1,
            "user_name": "takahashi",
            "parent_id": null,
            "content": "付与予定ラベル: tuna",
            "created_at": "2026-09-30T07:30:00Z",
            "updated_at": "2026-09-30T07:30:00Z"
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 50,
            "total": 1,
            "total_pages": 1
        }
    }
    ```

## エラーレスポンス

- レスポンス

    ```json
    {
    "error": {
        "code": "TASK_NOT_FOUND",
        "message": "指定されたタスクが存在しません"
    }
    }
    ```

| code | HTTP | 意味 |
| --- | ---: | --- |
| `VALIDATION_ERROR` | `422` | 入力値不正 |
| `AUTHENTICATION_REQUIRED` | `401` | 未認証・認証期限切れ |
| `INVALID_CREDENTIALS` | `401` | ログイン失敗 |
| `PERMISSION_DENIED` | `403` | 権限不足 |
| `USER_NOT_FOUND` | `404` | ユーザーなし |
| `GROUP_NOT_FOUND` | `404` | グループなし |
| `TASK_NOT_FOUND` | `404` | タスクなし |
| `STATE_NOT_FOUND` | `404` | 状態なし |
| `COMMENT_NOT_FOUND` | `404` | コメントなし |
| `INTERNAL_SERVER_ERROR` | `500` | サーバー内部エラー |

## 権限仕様

| API | 作業者 | 管理者 |
| --- | --- | --- |
| `GET /users/me` | 自分のみ | 自分のみ |
| `GET /users/{id}/groups` | 自分のみ | 全員 |
| `GET /users/{id}/groups/{group_id}/tasks` | 担当グループのみ | 全グループ |
| `PATCH /tasks/{task_id}/state` | 担当タスクのみ | 全タスク |
| `POST /tasks/{task_id}/comments` | 担当タスクのみ | 全タスク |
| `GET /tasks/{task_id}/comments` | 担当タスクのみ | 全タスク |

## データの流れ

```mermaid
flowchart TD
    A["Next.js"] --> B["FastAPI Router"]
    B --> C["認証・入力検証"]
    C --> D["Service"]
    D --> E["Repository"]
    E --> F["MySQL DB"]
    F --> E
    E --> G["SQLAlchemy Model"]
    G --> H["Mapper"]
    H --> I["Pydantic Schema"]
    I --> A
```

## 認証方式

- 初期実装では，ユーザ名とパスワードによるログイン認証を行う．
- ログイン成功時，バックエンドはユーザを識別するための署名付き認証トークンを生成し，Cookieへ保存する．
- 初期実装は大学内ネットワークでの利用を想定．

### Cookie設定

| 項目 | 初期設定 |
| --- | --- |
| Cookie名 | `access_token` |
| Path | `/` |
| SameSite | `Lax` |
| HttpOnly | （今後実装予定） |
| Secure | HTTPS導入後に有効 |
| Max-Age | 28800秒（8時間） |

## 今後の追加要素

### 認証Cookieのセキュリティ強化

初期実装では，大学内ネットワークでの利用を前提として，
認証CookieにHttpOnly属性を設定しない．

将来的に以下の対応を行う．

- 認証CookieのHttpOnly属性を有効化する
- HTTPSを導入する
- 認証CookieのSecure属性を有効化する
- CSRF対策を強化する
- トークンの更新方式を追加する
- 認証失敗回数の制限を追加する
- セッションまたはトークンの失効管理を追加する
