import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

load_dotenv()

engine = create_engine(os.getenv('SQLALCHEMY_URL'))
localsession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()