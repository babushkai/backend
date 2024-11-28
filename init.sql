CREATE DATABASE IF NOT EXISTS recipe_db;
USE recipe_db;

DROP TABLE IF EXISTS recipes;

CREATE TABLE IF NOT EXISTS recipes (
  id integer PRIMARY KEY AUTO_INCREMENT,
  title varchar(100) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL,
  making_time varchar(100) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL,
  serves varchar(100) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL,
  ingredients varchar(300) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL,
  cost integer NOT NULL,
  created_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at datetime on update CURRENT_TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO recipes (title, making_time, serves, ingredients, cost)
VALUES 
  ('チキンカレー', '45分', '4人', '玉ねぎ,肉,スパイス', 1000),
  ('オムライス', '30分', '2人', '玉ねぎ,卵,スパイス,醤油', 700);
