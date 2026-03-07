import os

# MYSQL
mysql = {
    "DB_HOSTNAME": os.environ.get("MYSQL_DB_HOSTNAME", ""),
    "DB_USER": os.environ.get("MYSQL_DB_USER", ""),
    "DB_PASSWORD": os.environ.get("MYSQL_DB_PASSWORD", ""),
    "DB_NAME": os.environ.get("MYSQL_DB_NAME", ""),
    "DB_PORT": int(os.environ.get("MYSQL_DB_PORT", 3306))
}

# UTILITS
utilits = {
    "HOST": os.environ.get("UTILITS_HOST", ""),
    "PATH_SCHEMA": os.environ.get("UTILITS_PATH_SCHEMA", "/api/schema")
}

# JWT
jwt = {
    "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY", ""),
    "JWT_ACCESS_TOKEN_EXPIRES": int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 2629743))
}
