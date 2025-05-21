from typing import Dict, Any, List, Optional, Tuple
import threading
import time
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from .biometric_auth import BiometricAuth
from .face_encoder import FaceEncoder
from .camera_handler import CameraHandler
from .utils import logger
from .config import TRAINING_DIR

class BioAuthController:
    """Controller for biometric authentication API endpoints"""
    
    def __init__(self):
        """Initialize the biometric authentication controller"""
        self.auth = BiometricAuth(
            recognition_threshold=0.55,
            consecutive_matches_required=3,
            model="hog",
            use_threading=True,
            use_anti_spoofing=True
        )
        self.camera_handler = CameraHandler()
        self.face_encoder = FaceEncoder()
        
        # Active authentication session
        self.active_session = None
        self.session_lock = threading.Lock()
        self.session_result = None
        
    def register_flask_routes(self, app):
        """
        Register API endpoints with the Flask app
        
        Args:
            app: Flask application instance
        """
        # Import Flask-specific code here to avoid dependencies when not used
        from flask import request, jsonify
        
        @app.route('/api/auth/trigger', methods=['POST'])
        def trigger_auth():
            """Trigger an authentication session"""
            # Check if there's already an active session
            with self.session_lock:
                if self.active_session and self.active_session.is_alive():
                    return jsonify({
                        'status': 'error',
                        'message': 'Authentication session already in progress'
                    }), 409
                
                # Start a new authentication session
                self.session_result = None
                self.active_session = threading.Thread(
                    target=self._run_authentication_session
                )
                self.active_session.daemon = True
                self.active_session.start()
                
                return jsonify({
                    'status': 'success',
                    'message': 'Authentication session started',
                    'session_id': datetime.now().strftime('%Y%m%d%H%M%S')
                })
                
        @app.route('/api/auth/status', methods=['GET'])
        def get_auth_status():
            """Get the status of the current authentication session"""
            with self.session_lock:
                if not self.active_session:
                    return jsonify({
                        'status': 'error',
                        'message': 'No authentication session found'
                    }), 404
                    
                if self.active_session.is_alive():
                    return jsonify({
                        'status': 'processing',
                        'message': 'Authentication in progress'
                    })
                    
                if self.session_result:
                    success, username = self.session_result
                    if success:
                        return jsonify({
                            'status': 'success',
                            'message': 'Authentication successful',
                            'user': username
                        })
                    else:
                        return jsonify({
                            'status': 'failed',
                            'message': 'Authentication failed'
                        })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Session completed with no result'
                    }), 500
                    
        @app.route('/api/users', methods=['GET'])
        def get_users():
            """Get all registered users"""
            try:
                # Import here to avoid circular imports
                from .db_manager import DatabaseManager
                db_manager = DatabaseManager()
                users = db_manager.get_users()
                
                return jsonify({
                    'status': 'success',
                    'count': len(users),
                    'users': users
                })
            except Exception as e:
                logger.error(f"Error getting users: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
                
        @app.route('/api/users/register', methods=['POST'])
        def register_user():
            """Register a new user with provided images"""
            try:
                data = request.json
                if not data or 'name' not in data:
                    return jsonify({
                        'status': 'error',
                        'message': 'Name is required'
                    }), 400
                    
                name = data['name']
                
                # Handle file upload if provided
                if 'image' in request.files:
                    # Create directory for user images
                    user_dir = TRAINING_DIR / name
                    user_dir.mkdir(parents=True, exist_ok=True)
                    
                    image_file = request.files['image']
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{name}_{timestamp}.png"
                    filepath = user_dir / filename
                    
                    # Save the image
                    image_file.save(str(filepath))
                    
                    # Re-encode faces to update database
                    self.face_encoder.encode_known_faces(force_rebuild=True)
                    
                    return jsonify({
                        'status': 'success',
                        'message': f'User {name} registered with uploaded image'
                    })
                else:
                    # Return info for camera-based registration
                    return jsonify({
                        'status': 'info',
                        'message': 'No image provided, use camera registration endpoint'
                    }), 202
                    
            except Exception as e:
                logger.error(f"Error registering user: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
                
        @app.route('/api/users/register-camera', methods=['POST'])
        def register_user_camera():
            """Start camera-based user registration"""
            try:
                data = request.json
                if not data or 'name' not in data:
                    return jsonify({
                        'status': 'error',
                        'message': 'Name is required'
                    }), 400
                    
                name = data['name']
                num_images = data.get('num_images', 5)
                
                # Check if camera is available
                if not self.camera_handler.is_running:
                    if not self.camera_handler.start():
                        return jsonify({
                            'status': 'error',
                            'message': 'Failed to start camera'
                        }), 500
                
                # Start registration in a new thread
                def run_registration():
                    try:
                        success = self.face_encoder.register_person_from_camera(
                            self.camera_handler, name, num_images
                        )
                        logger.info(f"Registration for {name}: {'success' if success else 'failed'}")
                    finally:
                        if self.camera_handler.is_running:
                            self.camera_handler.stop()
                
                registration_thread = threading.Thread(target=run_registration)
                registration_thread.daemon = True
                registration_thread.start()
                
                return jsonify({
                    'status': 'success',
                    'message': f'Registration started for {name}',
                    'instructions': 'Follow prompts on camera preview window'
                })
                
            except Exception as e:
                logger.error(f"Error starting camera registration: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
                
        @app.route('/api/auth/log', methods=['GET'])
        def get_auth_logs():
            """Get authentication logs"""
            try:
                # Import here to avoid circular imports
                from .db_manager import DatabaseManager
                db_manager = DatabaseManager()
                
                # Connect to database directly for a more complex query
                import sqlite3
                from .config import DB_PATH
                
                conn = sqlite3.connect(str(DB_PATH))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get authentication logs with user names
                cursor.execute('''
                SELECT l.id, l.status, l.confidence, l.timestamp, u.name as user_name
                FROM auth_logs l
                LEFT JOIN users u ON l.user_id = u.id
                ORDER BY l.timestamp DESC
                LIMIT 100
                ''')
                
                logs = [dict(row) for row in cursor.fetchall()]
                conn.close()
                
                return jsonify({
                    'status': 'success',
                    'count': len(logs),
                    'logs': logs
                })
                
            except Exception as e:
                logger.error(f"Error getting auth logs: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        logger.info("Registered biometric authentication API endpoints")
    
    def _run_authentication_session(self):
        """Run authentication session in a separate thread"""
        try:
            # Run authentication process
            success, username = self.auth.authenticate(
                max_attempts=30,  # About 3 seconds at 10 FPS
                timeout=15        # Max 15 seconds timeout
            )
            
            # Store result
            with self.session_lock:
                self.session_result = (success, username)
                
            logger.info(f"Authentication session completed: {'success' if success else 'failed'}" +
                      (f" ({username})" if success else ""))
                      
        except Exception as e:
            logger.error(f"Error in authentication session: {e}")
            with self.session_lock:
                self.session_result = (False, None)
                
def create_flask_app():
    """
    Create a Flask app with biometric authentication endpoints
    
    Returns:
        Flask application
    """
    # Import Flask here to make it optional when using other features
    from flask import Flask, jsonify
    
    app = Flask(__name__)
    
    # Register authentication endpoints
    auth_controller = BioAuthController()
    auth_controller.register_flask_routes(app)
    
    # Basic error handling
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            'status': 'error',
            'message': 'Endpoint not found'
        }), 404
        
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500
    
    return app 