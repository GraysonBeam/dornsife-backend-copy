from sqlalchemy.orm import DeclarativeBase

"""
A Class for a DeclarativeBase that all the database table models can inherit to
make them all available to the SQLAlchemy db engine
"""


class Base(DeclarativeBase):
    pass
