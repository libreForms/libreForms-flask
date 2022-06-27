DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS post;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE,
  organization TEXT,
  phone TEXT,
  created_date TEXT,
  password TEXT NOT NULL
);

INSERT INTO user (id,username,created_date,password)
VALUES 
   (1,'libreforms','2022-06-01 00:00:00','pbkdf2:sha256:260000$nQVWxd59E8lmkruy$13d8c4d408185ccc3549d3629be9cd57267a7d660abef389b3be70850e1bbfbf'
   );

