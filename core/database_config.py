import os

def get_database_config():
    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": os.getenv("DEFAULT_DB_NAME"),
            "USER": os.getenv("DEFAULT_DB_USER"),
            "PASSWORD": os.getenv("DEFAULT_DB_PASSWORD"),
            "HOST": os.getenv("DEFAULT_DB_HOST"),
            "PORT": os.getenv("DEFAULT_DB_PORT", "5432"),
        }
        # "beta": {
        #     "ENGINE": "django.db.backends.postgresql_psycopg2",
        #     "NAME": os.getenv("BETA_DB_NAME"),
        #     "USER": os.getenv("BETA_DB_USER"),
        #     "PASSWORD": os.getenv("BETA_DB_PASSWORD"),
        #     "HOST": os.getenv("BETA_DB_HOST"),
        #     "PORT": os.getenv("BETA_DB_PORT", "5432"),
        # },
    }
