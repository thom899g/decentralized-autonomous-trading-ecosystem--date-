"""
Firebase Admin SDK initialization with proper credential handling.
Firestore is used for:
- Agent state persistence
- Market data caching
- Strategy parameter storage
- Inter-agent communication
"""

import os
import logging
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

# Initialize structured logging
logger = logging.getLogger(__name__)

class FirebaseManager:
    """Manages Firebase connection with failover mechanisms."""
    
    _instance: Optional[Client] = None
    _initialized = False
    
    @classmethod
    def initialize(cls, credential_path: Optional[str] = None) -> Client:
        """
        Initialize Firebase Admin SDK with multiple credential sources.
        
        Priority:
        1. GOOGLE_APPLICATION_CREDENTIALS environment variable
        2. Explicit credential file path
        3. Default service account discovery
        
        Args:
            credential_path: Optional path to service account JSON file
            
        Returns:
            Firestore client instance
            
        Raises:
            FileNotFoundError: If credential file doesn't exist
            ValueError: If Firebase initialization fails
        """
        if cls._initialized and cls._instance:
            logger.info("Firebase already initialized")
            return cls._instance
        
        try:
            # Check for environment variable first
            env_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            
            if credential_path:
                cred_path = Path(credential_path)
                if not cred_path.exists():
                    raise FileNotFoundError(f"Credential file not found: {credential_path}")
                cred = credentials.Certificate(str(cred_path))
                logger.info(f"Using credential file: {credential_path}")
            elif env_cred:
                env_path = Path(env_cred)
                if not env_path.exists():
                    raise FileNotFoundError(f"Environment credential file not found: {env_cred}")
                cred = credentials.Certificate(str(env_path))
                logger.info(f"Using environment credential: {env_cred}")
            else:
                # Attempt to use default service account (GCP environments)
                cred = credentials.ApplicationDefault()
                logger.info("Using default application credentials")
            
            # Initialize Firebase app (avoid duplicate initialization)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                logger.info("Firebase app already exists, reusing")
            
            # Get Firestore client with retry settings
            firestore_settings = {
                'project': cred.project_id,
                'client_options': {
                    'max_retries': 3,
                    'timeout': 30.0
                }
            }
            
            cls._instance = firestore.Client(**firestore_settings)
            cls._initialized = True
            
            # Test connection
            test_doc = cls._instance.collection('system_health').document('connection_test')
            test_doc.set({'timestamp': firestore.SERVER_TIMESTAMP, 'status': 'connected'})
            logger.info("Firestore connection verified")
            
            return cls._instance
            
        except Exception as e:
            logger.error(f"Firebase initialization failed: {str(e)}")
            raise ValueError(f"Firebase initialization error: {str(e)}")
    
    @classmethod
    def get_client(cls) -> Client:
        """Get Firestore client, initializing if necessary."""
        if not cls._instance:
            cls.initialize()
        return cls._instance