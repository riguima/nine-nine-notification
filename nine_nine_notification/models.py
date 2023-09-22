from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from nine_nine_notification.database import db


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    url: Mapped[str]
    publication_datetime: Mapped[datetime]


Base.metadata.create_all(db)
