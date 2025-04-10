#!/usr/bin/env python3
import os
import sqlite3
import time
from pathlib import Path
from tinytag import TinyTag
from config import DB_PATH, MOUNT_POINT
from utils import logger
from network_handler import NetworkHandler

SUPPORTED_FORMATS = ['.flac', '.wav', '.alac', '.ape', '.aiff', '.dsd', '.dsf', '.dff', '.wv']

class MusicLibrary:
    def __init__(self, network_handler):
        self.db_path = DB_PATH
        self.network_handler = network_handler
        self.init_db()
    
    def init_db(self):
        """Initialize the SQLite database for the music library."""
        try:
            # Create database directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS albums (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    artist TEXT,
                    year TEXT,
                    directory TEXT UNIQUE,
                    cover_art TEXT,
                    last_updated INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY,
                    album_id INTEGER,
                    title TEXT NOT NULL,
                    artist TEXT,
                    track_number INTEGER,
                    disc_number INTEGER,
                    duration REAL,
                    file_path TEXT UNIQUE,
                    FOREIGN KEY (album_id) REFERENCES albums (id)
                )
            ''')
            
            # Create indices for faster searches
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_album_title ON albums (title)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_album_artist ON albums (artist)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_track_title ON tracks (title)')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def scan_library(self):
        """Scan the music library and update the database."""
        logger.info("Starting music library scan...")
        
        if not self.network_handler.ensure_mounted():
            logger.error("Cannot scan library: network share not mounted")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all music directories
            music_dirs = self.network_handler.list_directories()
            albums_found = 0
            tracks_found = 0
            
            for dir_name in music_dirs:
                # Skip hidden directories
                if dir_name.startswith('.'):
                    continue
                
                # Check if this directory contains music files
                music_files = []
                for ext in SUPPORTED_FORMATS:
                    music_files.extend(self.network_handler.list_files(dir_name, f".*\\{ext}$"))
                
                if not music_files:
                    # Check if this is a parent directory containing album directories
                    subdirs = self.network_handler.list_directories(dir_name)
                    for subdir in subdirs:
                        albums_found += self._process_album_directory(os.path.join(dir_name, subdir), cursor)
                else:
                    # This directory is an album
                    albums_found += self._process_album_directory(dir_name, cursor)
            
            conn.commit()
            conn.close()
            logger.info(f"Library scan complete: {albums_found} albums, {tracks_found} tracks")
            return True
        except Exception as e:
            logger.error(f"Error scanning library: {e}")
            return False
    
    def _process_album_directory(self, album_dir, cursor):
        """Process an album directory and add/update it in the database."""
        try:
            # Get all music files in this directory
            music_files = []
            for ext in SUPPORTED_FORMATS:
                music_files.extend(self.network_handler.list_files(album_dir, f".*\\{ext}$"))
            
            if not music_files:
                return 0
                
            # Check for cover art
            cover_art = None
            for art_file in ['cover.jpg', 'folder.jpg', 'album.jpg', 'front.jpg', 'artwork.jpg']:
                art_path = os.path.join(album_dir, art_file)
                if os.path.exists(os.path.join(MOUNT_POINT, art_path)):
                    cover_art = art_path
                    break
            
            # Get album metadata from the first music file
            first_file_path = os.path.join(MOUNT_POINT, album_dir, music_files[0])
            try:
                tag = TinyTag.get(first_file_path)
                album_title = tag.album or os.path.basename(album_dir)
                album_artist = tag.albumartist or tag.artist or "Unknown Artist"
                album_year = tag.year or "Unknown Year"
            except Exception as e:
                logger.warning(f"Error reading tags from {first_file_path}: {e}")
                album_title = os.path.basename(album_dir)
                album_artist = "Unknown Artist"
                album_year = "Unknown Year"
            
            # Insert or update album in database
            cursor.execute('''
                INSERT OR REPLACE INTO albums (title, artist, year, directory, cover_art, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (album_title, album_artist, album_year, album_dir, cover_art, int(time.time())))
            
            album_id = cursor.lastrowid
            
            # Process tracks
            for file_name in music_files:
                file_path = os.path.join(album_dir, file_name)
                full_path = os.path.join(MOUNT_POINT, file_path)
                
                try:
                    tag = TinyTag.get(full_path)
                    track_title = tag.title or os.path.splitext(file_name)[0]
                    track_artist = tag.artist or album_artist
                    track_number = tag.track or 0
                    disc_number = tag.disc or 1
                    duration = tag.duration or 0
                except Exception as e:
                    logger.warning(f"Error reading tags from {full_path}: {e}")
                    track_title = os.path.splitext(file_name)[0]
                    track_artist = album_artist
                    track_number = 0
                    disc_number = 1
                    duration = 0
                
                cursor.execute('''
                    INSERT OR REPLACE INTO tracks (album_id, title, artist, track_number, disc_number, duration, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (album_id, track_title, track_artist, track_number, disc_number, duration, file_path))
            
            return 1
        except Exception as e:
            logger.error(f"Error processing album directory {album_dir}: {e}")
            return 0
    
    def search_albums(self, query):
        """Search for albums matching the query."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Search in album title and artist
            cursor.execute('''
                SELECT id, title, artist, year, directory, cover_art 
                FROM albums 
                WHERE title LIKE ? OR artist LIKE ?
                ORDER BY title
                LIMIT 10
            ''', (f"%{query}%", f"%{query}%"))
            
            albums = []
            for row in cursor.fetchall():
                album_id, title, artist, year, directory, cover_art = row
                
                # Get tracks for this album
                cursor.execute('''
                    SELECT title, artist, track_number, disc_number, duration, file_path
                    FROM tracks
                    WHERE album_id = ?
                    ORDER BY disc_number, track_number, title
                ''', (album_id,))
                
                tracks = []
                for track_row in cursor.fetchall():
                    track_title, track_artist, track_number, disc_number, duration, file_path = track_row
                    tracks.append({
                        'title': track_title,
                        'artist': track_artist,
                        'track_number': track_number,
                        'disc_number': disc_number,
                        'duration': duration,
                        'file_path': file_path
                    })
                
                albums.append({
                    'id': album_id,
                    'title': title,
                    'artist': artist,
                    'year': year,
                    'directory': directory,
                    'cover_art': cover_art,
                    'tracks': tracks
                })
            
            conn.close()
            return albums
        except Exception as e:
            logger.error(f"Error searching albums: {e}")
            return []
    
    def get_album_by_id(self, album_id):
        """Get album details by ID."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, artist, year, directory, cover_art 
                FROM albums 
                WHERE id = ?
            ''', (album_id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
                
            album_id, title, artist, year, directory, cover_art = row
            
            # Get tracks for this album
            cursor.execute('''
                SELECT title, artist, track_number, disc_number, duration, file_path
                FROM tracks
                WHERE album_id = ?
                ORDER BY disc_number, track_number, title
            ''', (album_id,))
            
            tracks = []
            for track_row in cursor.fetchall():
                track_title, track_artist, track_number, disc_number, duration, file_path = track_row
                tracks.append({
                    'title': track_title,
                    'artist': track_artist,
                    'track_number': track_number,
                    'disc_number': disc_number,
                    'duration': duration,
                    'file_path': file_path
                })
            
            album = {
                'id': album_id,
                'title': title,
                'artist': artist,
                'year': year,
                'directory': directory,
                'cover_art': cover_art,
                'tracks': tracks
            }
            
            conn.close()
            return album
        except Exception as e:
            logger.error(f"Error getting album {album_id}: {e}")
            return None