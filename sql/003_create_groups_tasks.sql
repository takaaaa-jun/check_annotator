-- 001_create_users.sql の後に一度だけ実行する（MySQL）。
-- database仕様書.md の groups / states / tasks とインデックスに対応。
-- groups はMySQLの予約語との衝突を避けるためバッククォートで囲む。
USE check_annotator;

CREATE TABLE `groups` (
    group_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    group_name VARCHAR(50) NOT NULL,
    user_id INT UNSIGNED NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted_at DATETIME NULL,
    PRIMARY KEY (group_id),
    CONSTRAINT uq_groups_group_name UNIQUE (group_name),
    KEY ix_groups_user_id (user_id),
    CONSTRAINT fk_groups_user_id FOREIGN KEY (user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE states (
    state_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    state_name VARCHAR(20) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted_at DATETIME NULL,
    PRIMARY KEY (state_id),
    CONSTRAINT uq_states_state_name UNIQUE (state_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE tasks (
    task_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    group_id INT UNSIGNED NULL,
    image_id INT UNSIGNED NOT NULL,
    state_id INT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted_at DATETIME NULL,
    PRIMARY KEY (task_id),
    KEY ix_tasks_group_id (group_id),
    KEY ix_tasks_state_id (state_id),
    KEY ix_tasks_group_id_state_id (group_id, state_id),
    CONSTRAINT fk_tasks_group_id FOREIGN KEY (group_id)
        REFERENCES `groups` (group_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_tasks_state_id FOREIGN KEY (state_id)
        REFERENCES states (state_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- image_idの一意性は仕様書で未確定のため、UNIQUE制約は付けない。
-- グループ名・担当者・画像IDが未指定のため、実データの登録は別途行う。
