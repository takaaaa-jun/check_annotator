# データベースの仕様書

## 使用するテーブル

以下の六つのテーブルを使用する．

- users
  - ユーザ情報を管理するテーブル
  - 管理者用のアカウントと作業作用のアカウントで権限を分ける

  ![alt text](images/table_users.png)

- types
  - ユーザの管理タイプを定義するテーブル
  - 作業者と管理者を管理タイプとして定義

  ![alt text](images/table_types.png)

- groups
  - タスクのグループを管理するテーブル
  - 各グループの担当者を決めるときに使用する

  ![alt text](images/table_groups.png)

- states
  - タスクの状態を管理するテーブル
  - 未着手，完了，付与予定ラベル，コメントの四つを想定

  ![alt text](images/table_states.png)

- comments
  - タスクに対するコメントを管理するテーブル
  - 付与予定ラベルとコメントの状態の場合に投稿されるコメントデータを管理するテーブル

  ![alt text](images/table_comments.png)

- tasks
  - タスクを管理するテーブル
  - アノテーションをする画像がimage_idとなっており，番号に対応させて状態の更新を行う

  ![alt text](images/table_tasks.png)

## ER図

上記の六つのテーブルに対するER図を示す．

![alt text](images/table_ER_diagram.png)
