CREATE TABLE IF NOT EXISTS recipes (
  id SERIAL PRIMARY KEY,
  title varchar(100) NOT NULL,
  making_time varchar(100) NOT NULL,
  serves varchar(100) NOT NULL,
  ingredients varchar(300) NOT NULL,
  cost integer NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO recipes (title, making_time, serves, ingredients, cost)
VALUES 
  ('チキンカレー', '45分', '4人', '玉ねぎ,肉,スパイス', 1000),
  ('オムライス', '30分', '2人', '玉ねぎ,卵,スパイス,醤油', 700);
