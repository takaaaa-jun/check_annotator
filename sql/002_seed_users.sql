-- 001_create_users.sql の後に一度だけ実行する。
-- 添付のCOCO Annotator画面のユーザー名・管理者指定を反映。
-- COCO AnnotatorのID・パスワードは移行しない。
-- '!' は認証できない初期値。各ユーザーに個別のハッシュを設定するまでログイン不可。
-- 平文パスワードや実際のハッシュをこのファイルにコミットしないこと。
USE check_annotator;

START TRANSACTION;

SET @seed_time = UTC_TIMESTAMP();

INSERT INTO roles (role_name, created_at, updated_at, deleted_at)
VALUES
    ('admin', @seed_time, @seed_time, NULL),
    ('worker', @seed_time, @seed_time, NULL);

INSERT INTO users (
    user_name, password, role_id, login_at, created_at, updated_at, deleted_at
)
SELECT initial_users.user_name, '!', roles.role_id, NULL, @seed_time, @seed_time, NULL
FROM (
    SELECT 'takahashi' AS user_name, 'admin' AS role_name
    UNION ALL SELECT 'kimura', 'worker'
    UNION ALL SELECT 'imai', 'worker'
    UNION ALL SELECT 'umehara', 'worker'
    UNION ALL SELECT 'endo', 'worker'
    UNION ALL SELECT 'sato', 'worker'
    UNION ALL SELECT 'tabe', 'worker'
    UNION ALL SELECT 'matunaga', 'worker'
) AS initial_users
INNER JOIN roles ON roles.role_name = initial_users.role_name;

COMMIT;

SELECT users.user_id, users.user_name, roles.role_name
FROM users
INNER JOIN roles ON roles.role_id = users.role_id
ORDER BY users.user_id;
