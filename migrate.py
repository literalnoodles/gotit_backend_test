from database import db

migration_sqls = [
    [
        """
        CREATE TABLE IF NOT EXISTS User (
            id int(11) NOT NULL PRIMARY KEY AUTO_INCREMENT,
            email VARCHAR(50) not null,
            platform VARCHAR(20) not null,
            name VARCHAR(50),
            phone_number VARCHAR(20),
            occupation VARCHAR(50)
        )""",
        []
    ],
    [
        """
        CREATE TABLE IF NOT EXISTS Post (
            id int(11) NOT NULL PRIMARY KEY AUTO_INCREMENT,
            title VARCHAR(240) not null,
            body TEXT not null,
            author int(11) not null,
            created datetime DEFAULT CURRENT_TIMESTAMP
        )""",
        []
    ],
    [
        """
        CREATE TABLE IF NOT EXISTS Post_Like (
            id int(11) NOT NULL PRIMARY KEY AUTO_INCREMENT,
            post_id int(11) not null,
            user_id int(11) not null,
            created datetime DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT UK_post_user UNIQUE (post_id, user_id)
        )""",
        []
    ]
]

for sql, params in migration_sqls:
    db.execute_sql(sql, params)
