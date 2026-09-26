# バックエンドの仕様書

## 最小構成

### アプリで使用するデータ構造(json)

アプリで使用するjsonの構造を示す．

- task_object

```json
{
    task_id: 1,
    group_id: 1,
    user_name: "担当者A",
    image_id: 1,
    state_name: "完了",
    comment: ["comment1", "comment2", ...]
    update_at: "更新日"
}
```

- tasklist_object

```json
[
    task_object1,
    task_object2,
    task_object3,
    ...
]
```

### バックエンドで作成するAPI

- POST /login
- GET /user
- GET /mypage/{user_id}/tasklist
- GET mypage/{user_id}/tasklist/{group_id}

### データベースからデータを取得する部分

- データベースからデータを取得
- アプリで使用するデータ構造を持ったクラスを定義する部分
- 取得したデータ構造をアプリで使用する構造に変換する部分

## 今後追加する機能

- 後手追記
