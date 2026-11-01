-- MySQL 8.0.16以上。既存6テーブルを変更しない追加DDL。
-- scripts/import_categories.py --build-bundle で生成。USEは接続先で指定。

CREATE TABLE category1_master (
	category1_id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
	code VARCHAR(100) NOT NULL,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	sort_order INTEGER UNSIGNED NOT NULL DEFAULT '0',
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (category1_id),
	UNIQUE (code)
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE category2_master (
	category2_id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
	code VARCHAR(100) NOT NULL,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	sort_order INTEGER UNSIGNED NOT NULL DEFAULT '0',
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (category2_id),
	UNIQUE (code)
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE category3_master (
	category3_id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
	code VARCHAR(100) NOT NULL,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	sort_order INTEGER UNSIGNED NOT NULL DEFAULT '0',
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (category3_id),
	UNIQUE (code)
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE category4_master (
	category4_id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
	code VARCHAR(100) NOT NULL,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	sort_order INTEGER UNSIGNED NOT NULL DEFAULT '0',
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (category4_id),
	UNIQUE (code)
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE category5_master (
	category5_id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
	code VARCHAR(100) NOT NULL,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	sort_order INTEGER UNSIGNED NOT NULL DEFAULT '0',
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (category5_id),
	UNIQUE (code)
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE category6_master (
	category6_id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
	code VARCHAR(100) NOT NULL,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	sort_order INTEGER UNSIGNED NOT NULL DEFAULT '0',
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (category6_id),
	UNIQUE (code)
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE category_sources (
	category_source_id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
	code VARCHAR(100) NOT NULL,
	name VARCHAR(100) NOT NULL,
	version VARCHAR(50) NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (category_source_id),
	UNIQUE (code)
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE food_categories (
	food_category_id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
	code VARCHAR(100) NOT NULL,
	category1_id INTEGER UNSIGNED NOT NULL,
	category2_id INTEGER UNSIGNED NOT NULL,
	category3_id INTEGER UNSIGNED NOT NULL,
	category4_id INTEGER UNSIGNED NOT NULL,
	category5_id INTEGER UNSIGNED NOT NULL,
	category6_id INTEGER UNSIGNED,
	category6_key INTEGER UNSIGNED GENERATED ALWAYS AS (COALESCE(category6_id, 0)) STORED,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (food_category_id),
	CONSTRAINT uq_food_category_path UNIQUE (category1_id, category2_id, category3_id, category4_id, category5_id, category6_key),
	UNIQUE (code),
	FOREIGN KEY(category1_id) REFERENCES category1_master (category1_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(category2_id) REFERENCES category2_master (category2_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(category3_id) REFERENCES category3_master (category3_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(category4_id) REFERENCES category4_master (category4_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(category5_id) REFERENCES category5_master (category5_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(category6_id) REFERENCES category6_master (category6_id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE source_categories (
	source_category_id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
	category_source_id INTEGER UNSIGNED NOT NULL,
	external_category_id INTEGER UNSIGNED NOT NULL,
	name VARCHAR(100) NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (source_category_id),
	CONSTRAINT uq_source_external_category UNIQUE (category_source_id, external_category_id),
	FOREIGN KEY(category_source_id) REFERENCES category_sources (category_source_id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE category_replacement_mappings (
	mapping_id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
	source_category_id INTEGER UNSIGNED NOT NULL,
	food_category_id INTEGER UNSIGNED NOT NULL,
	target_level INTEGER UNSIGNED NOT NULL,
	active_source_key INTEGER UNSIGNED GENERATED ALWAYS AS (CASE WHEN deleted_at IS NULL THEN source_category_id ELSE NULL END) STORED,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (mapping_id),
	CONSTRAINT ck_mapping_target_level CHECK (target_level IN (5, 6)),
	CONSTRAINT uq_active_source_mapping UNIQUE (active_source_key),
	FOREIGN KEY(source_category_id) REFERENCES source_categories (source_category_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(food_category_id) REFERENCES food_categories (food_category_id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
