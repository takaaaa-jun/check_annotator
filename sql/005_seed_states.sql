-- 003_create_groups_tasks.sql の後に一度だけ実行する。
USE check_annotator;
START TRANSACTION;
SET @seed_time = UTC_TIMESTAMP();
INSERT INTO states (state_id, state_name, created_at, updated_at, deleted_at)
VALUES
    (1, '未着手', @seed_time, @seed_time, NULL),
    (2, '完了', @seed_time, @seed_time, NULL),
    (3, '付与予定ラベル', @seed_time, @seed_time, NULL),
    (4, 'コメント', @seed_time, @seed_time, NULL);
COMMIT;
