import sqlite3
import pickle
import numpy as np
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import time
from datetime import datetime

from .utils import logger
from .config import DB_PATH


class DatabaseManager:
    """Manages SQLite database operations for the face recognition system"""
    
    def __init__(self, db_path: Path = DB_PATH):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.initialize_db()
    
    def initialize_db(self) -> None:
        """Create database tables if they don't exist"""
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            is_authorized BOOLEAN NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create face_encodings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS face_encodings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            encoding BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')
        
        # Create auth_logs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            status TEXT NOT NULL,
            confidence REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def add_user(self, name: str) -> int:
        """
        Add a new user to the database
        
        Args:
            name: User's name
            
        Returns:
            User ID
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT INTO users (name) VALUES (?)", (name,))
            user_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Added user {name} with ID {user_id}")
            return user_id
        except sqlite3.IntegrityError:
            # User already exists, get their ID
            cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
            user_id = cursor.fetchone()[0]
            logger.info(f"User {name} already exists with ID {user_id}")
            return user_id
        finally:
            conn.close()
    
    def get_users(self) -> List[Dict[str, Any]]:
        """
        Get all users
        
        Returns:
            List of user dictionaries
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users")
        users = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return users
    
    def get_authorized_users(self) -> List[str]:
        """
        Get all authorized users' names
        
        Returns:
            List of authorized user names
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM users WHERE is_authorized = 1")
        user_names = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return user_names
    
    def add_face_encoding(self, user_id: int, encoding: np.ndarray) -> int:
        """
        Add a face encoding for a user
        
        Args:
            user_id: User ID
            encoding: Face encoding vector
            
        Returns:
            Encoding ID
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Serialize face encoding to binary
        encoding_bytes = pickle.dumps(encoding)
        
        cursor.execute("INSERT INTO face_encodings (user_id, encoding) VALUES (?, ?)",
                     (user_id, encoding_bytes))
        encoding_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        logger.info(f"Added face encoding {encoding_id} for user {user_id}")
        return encoding_id
    
    def get_face_encodings(self) -> Dict[str, Any]:
        """
        Get all face encodings with user names
        
        Returns:
            Dictionary with 'names' and 'encodings' lists
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT u.name, e.encoding
        FROM face_encodings e
        JOIN users u ON e.user_id = u.id
        WHERE u.is_authorized = 1
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # Unpack into the format expected by the face_recognition library
        result = {
            "names": [],
            "encodings": []
        }
        
        for name, encoding_bytes in rows:
            encoding = pickle.loads(encoding_bytes)
            result["names"].append(name)
            result["encodings"].append(encoding)
            
        return result
    
    def log_authentication(self, user_name: Optional[str], status: str, confidence: Optional[float] = None) -> None:
        """
        Log an authentication attempt
        
        Args:
            user_name: User's name, or None if unknown
            status: 'success', 'failed', or other status string
            confidence: Recognition confidence score (0-1)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        user_id = None
        if user_name and user_name != "Unknown" and user_name != "Fake":
            # Get user ID if available
            cursor.execute("SELECT id FROM users WHERE name = ?", (user_name,))
            result = cursor.fetchone()
            if result:
                user_id = result[0]
        
        cursor.execute(
            "INSERT INTO auth_logs (user_id, status, confidence) VALUES (?, ?, ?)",
            (user_id, status, confidence)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Logged authentication: user={user_name}, status={status}, confidence={confidence}")
    
    def migrate_from_pkl(self, encodings_path: Path) -> int:
        """
        Migrate face encodings from .pkl file to database
        
        Args:
            encodings_path: Path to existing encodings.pkl file
            
        Returns:
            Number of encodings migrated
        """
        if not encodings_path.exists():
            logger.warning(f"Encodings file {encodings_path} does not exist")
            return 0
            
        try:
            # Load existing encodings
            with open(encodings_path, "rb") as f:
                data = pickle.load(f)
                
            migrated = 0
            # Add each encoding to database
            for name, encoding in zip(data["names"], data["encodings"]):
                user_id = self.add_user(name)
                self.add_face_encoding(user_id, encoding)
                migrated += 1
                
            return migrated
        except Exception as e:
            logger.error(f"Error migrating encodings: {e}")
            return 0 