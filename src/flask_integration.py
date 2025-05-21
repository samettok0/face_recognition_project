"""
Flask Integration Example

This file shows how to integrate the biometric authentication system
with an existing Flask application.

Usage:
    1. Import the BioAuthController from api_controller
    2. Create an instance of the controller
    3. Call register_flask_routes() with your Flask app
"""

from flask import Flask, jsonify, request
from .api_controller import BioAuthController
from .config import API_PORT, API_HOST

def integrate_with_existing_flask(app: Flask):
    """
    Integrate biometric authentication with an existing Flask app
    
    Args:
        app: Existing Flask application
    """
    # Create the biometric authentication controller
    bio_auth = BioAuthController()
    
    # Register routes with the existing app
    bio_auth.register_flask_routes(app)
    
    # You can add more routes or modify existing ones as needed
    @app.route('/')
    def home():
        return jsonify({
            'status': 'success',
            'message': 'Biometric authentication system integrated',
            'endpoints': [
                '/api/auth/trigger',
                '/api/auth/status',
                '/api/users',
                '/api/users/register',
                '/api/users/register-camera',
                '/api/auth/log'
            ]
        })

def start_standalone_server():
    """
    Start a standalone server for the biometric authentication system
    
    This can be used for testing or when you don't have an existing Flask app
    """
    from .api_controller import create_flask_app
    
    app = create_flask_app()
    
    # Add a basic home route
    @app.route('/')
    def home():
        return jsonify({
            'status': 'success',
            'message': 'Biometric authentication server running',
            'endpoints': [
                '/api/auth/trigger',
                '/api/auth/status',
                '/api/users',
                '/api/users/register',
                '/api/users/register-camera',
                '/api/auth/log'
            ]
        })
    
    # Run the app
    app.run(host=API_HOST, port=API_PORT, debug=True)

if __name__ == '__main__':
    # If running this file directly, start the standalone server
    start_standalone_server() 