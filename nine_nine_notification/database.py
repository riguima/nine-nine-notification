import toml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

secrets = toml.load(open('.secrets.toml'))

db = create_engine(secrets['DATABASE_URI'])
Session = sessionmaker(db)
