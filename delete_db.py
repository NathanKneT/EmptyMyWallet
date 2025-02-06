import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from db.db import get_db_config

def delete_database():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)  # Log to console
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    try:
        db_config = get_db_config()

        # 1. Connect to the *postgres* database (or your admin DB)
        admin_connection_string = (
            f'postgresql+psycopg2://{db_config["user"]}:{db_config["password"]}'
            f'@{db_config["host"]}:{db_config["port"]}/{db_config["dbname"]}'
        )
        admin_engine = create_engine(admin_connection_string)

        # 2. Drop the target database
        with admin_engine.connect() as conn:
            try:
                conn.execute(text(f"DROP DATABASE {db_config['dbname']};"))
                conn.commit()  # Important to commit the DROP DATABASE command
                logger.info(f"Database '{db_config['dbname']}' deleted successfully.")
            except SQLAlchemyError as e:
                conn.rollback() # Rollback in case of error
                logger.error(f"Error dropping database: {e}")
                return False # Indicate failure

        # 3. (Optional) Close the admin connection
        admin_engine.dispose()

        return True # Indicate success

    except SQLAlchemyError as e:
        logger.error(f"Database operation error: {e}")
        return False


if __name__ == "__main__":
    if delete_database():
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure