import os.path

from flask import url_for
from sqlalchemy import Column, Integer, String, Sequence, ForeignKey
from sqlalchemy.orm import relationship

from tuneful import app
from .database import Base, engine, session

class Song(Base):
    __tablename__="songs"
    id = Column(Integer, primary_key=True)
    
    original_file_id = Column(Integer, ForeignKey('files.id'), nullable=False)
    
    def as_dictionary(self):
        song = {
            "id": self.id,
            "file": {
                "id": self.file.id,
                "name": self.file.filename,
                "path": url_for("uploaded_file", filename=self.file.filename)
            }
        }
        return song


    
class File(Base):
    __tablename__="files"
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    
    song = relationship("Song", uselist=False, backref="file")

    def as_dictionary(self):
        return {
            "id": self.id,
            "name": self.filename,
            "path": url_for("uploaded_file", filename=self.filename)
        }