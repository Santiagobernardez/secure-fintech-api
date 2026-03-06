import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 1. Securely fetch database credentials from environment variables
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "super_secret_password")
DB_SERVER = os.getenv("POSTGRES_SERVER", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "fintech_db")

# 2. Construct the secure connection string (DSN)
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}"

# 3. Create the SQLAlchemy Engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 4. Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. Create a Base class for our data models
Base = declarative_base()

# 6. Dependency function to handle database sessions safely
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()