import unittest
import os
import shutil
import json
try: from urllib.parse import urlparse
except ImportError: from urlparse import urlparse # Py2 compatibility
from io import StringIO, BytesIO

import sys; print(list(sys.modules.keys()))
# Configure our app to use the testing databse
os.environ["CONFIG_PATH"] = "tuneful.config.TestingConfig"

from tuneful import app
from tuneful import models
from tuneful.utils import upload_path
from tuneful.database import Base, engine, session

class TestAPI(unittest.TestCase):
    """ Tests for the tuneful API """

    def setUp(self):
        """ Test setup """
        self.client = app.test_client()

        # Set up the tables in the database
        Base.metadata.create_all(engine)

        # Create folder for test uploads
        os.mkdir(upload_path())

    def tearDown(self):
        """ Test teardown """
        session.close()
        # Remove the tables and their data from the database
        Base.metadata.drop_all(engine)

        # Delete test upload folder
        shutil.rmtree(upload_path())
        
    def test_get_empty_songs(self):
        response = self.client.get(
            "/api/songs",
            headers=[("Accept", "application/json")])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(data, [])

    def test_get_songs(self):
        fileA = models.File(filename = "Test File 1")
        fileB = models.File(filename = "Test File 2")
        
        session.add_all([fileA, fileB])
        session.commit()
        
        songA = models.Song(original_file_id = fileA.id)
        songB = models.Song(original_file_id = fileB.id)

        session.add_all([songA, songB])
        session.commit()
        
        response = self.client.get("/api/songs", headers=[("Accept", "application/json")])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data.decode("ascii"))
        songA = data[0]
        self.assertEqual(songA["file"]["name"], "Test File 1")
        self.assertEqual(songA["file"]["id"], fileA.id)

        songB = data[1]
        self.assertEqual(songB["file"]["name"], "Test File 2")
        self.assertEqual(songB["file"]["id"], fileB.id)

        
    def test_add_songs(self):
        fileA = models.File(filename = 'Test File 1')
        
        session.add(fileA)
        session.commit()
        
        data = {
            "file": {
                "id" : fileA.id
            }
        }

        response = self.client.post("/api/songs",
            data=json.dumps(data),
            content_type="application/json",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(urlparse(response.headers.get("Location")).path,
                         "/api/songs")
    
        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["file"]["id"], fileA.id)
        self.assertEqual(data["file"]["name"], fileA.filename)

        songs = session.query(models.Song).all()
        self.assertEqual(len(songs), 1)

        song = songs[0]
        self.assertEqual(song.id, fileA.id)
        
    def test_song_delete(self):
        file1 = models.File(filename ="File1")
        file2 = models.File(filename = "File2")
        session.add_all([file1, file2])
        session.commit()
        song1 = models.Song(original_file_id=file1.id)
        song2 = models.Song(original_file_id=file2.id)
        session.add_all([song1, song2])
        session.commit()
        
        response = self.client.delete(
            "/api/songs/{}".format(song1.id),
            headers=[("Accept", "application/json")])
            
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        songs = session.query(models.Song).all()
        self.assertEqual(len(songs), 1)
        
        song = songs[0]
        self.assertEqual(song.id, file2.id)
        
    def test_song_edit(self):
        file1 = models.File(filename ="File1")
        file2 = models.File(filename = "File2")
        session.add_all([file1, file2])
        session.commit()
        song1 = models.Song(original_file_id=file1.id)
        session.add(song1)
        session.commit()
        
        data = {
            "file": {
                "id" : file2.id
            }
        }
        
        response = self.client.put("/api/songs/{}".format(song1.id),
            data=json.dumps(data),
            content_type="application/json",
            headers=[("Accept", "application/json")]
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")        

        songs = session.query(models.Song).all()
        self.assertEqual(len(songs), 1)
        
        song = songs[0]
        self.assertEqual(song.original_file_id, file2.id)
        
    def test_get_uploaded_file(self):
        path =  upload_path("test.txt")
        with open(path, "wb") as f:
            f.write(b"File contents")

        response = self.client.get("/uploads/test.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/plain")
        self.assertEqual(response.data, b"File contents")
        
    def test_file_upload(self):
        data = {
            "file": (BytesIO(b"File contents"), "test.txt")
        }

        response = self.client.post("/api/files",
            data=data,
            content_type="multipart/form-data",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(urlparse(data["path"]).path, "/uploads/test.txt")

        path = upload_path("test.txt")
        self.assertTrue(os.path.isfile(path))
        with open(path, "rb") as f:
            contents = f.read()
        self.assertEqual(contents, b"File contents")