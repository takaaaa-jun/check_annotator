-- 001_create_users.sql と 003_create_groups_tasks.sql の後に一度だけ実行する。
-- database仕様書.md の comments 定義とインデックスに対応（MySQL）。
USE check_annotator;

CREATE TABLE comments (
    comment_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    task_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    content TEXT NOT NULL,
    parent_id INT UNSIGNED NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted_at DATETIME NULL,
    PRIMARY KEY (comment_id),
    KEY ix_comments_task_id (task_id),
    KEY ix_comments_user_id (user_id),
    KEY ix_comments_parent_id (parent_id),
    KEY ix_comments_task_id_created_at (task_id, created_at),
    CONSTRAINT fk_comments_task_id FOREIGN KEY (task_id)
        REFERENCES tasks (task_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_comments_user_id FOREIGN KEY (user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_comments_parent_id FOREIGN KEY (parent_id)
        REFERENCES comments (comment_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
