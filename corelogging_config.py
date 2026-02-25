"""
Structured logging configuration for DATE ecosystem.
Enables log aggregation, severity levels, and Firestore integration.
"""

import logging
import sys
from datetime import datetime
from typing import Dict, Any

import structlog
from google.cloud.firestore import Client

class DATELogger:
    """Centralized logging with Firestore persistence."""
    
    def __init__(self, module_name: str, firestore_client: Client = None):
        """
        Initialize logger for a specific module.
        
        Args:
            module_name: Name of the module/agent
            firestore_client: Optional Firestore client for log persistence
        """
        self.module_name = module_name
        self.firestore_client = firestore_client
        
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        self.logger = structlog.get_logger(module_name)
        
    def log(self, level: str, message: str, **kwargs):
        """
        Log message with Firestore persistence.
        
        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            **kwargs: Additional context data
        """
        log_method = getattr(self.logger, level)
        
        # Add module context
        context = {
            'module': self.module_name,
            'timestamp': datetime.utcnow().isoformat(),
            **kwargs
        }
        
        # Log to stdout
        log_method(message, **context)
        
        # Persist to Firestore if client available
        if self.firestore_client and level in ('warning', 'error', 'critical'):
            try:
                log_entry = {
                    'module': self.module_name,
                    'level': level,
                    'message': message,
                    'context': kwargs,
                    'timestamp': datetime.utcnow(),
                    'resolved': False
                }
                
                self.firestore_client.collection('system_logs').add(log_entry)
            except Exception as e:
                # Fallback to console if Firestore fails
                print(f"Failed to persist log to Firestore: {e}", file=sys.stderr)
    
    def error(self, message: str, exception: Exception = None, **kwargs):
        """Convenience method for error logging."""
        if exception:
            kwargs['exception'] = str(exception)
            kwargs['exception_type'] = type(exception).__name__
        self.log('error', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Convenience method for info logging."""
        self.log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Convenience method for warning logging."""
        self.log('warning', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Convenience method for debug logging."""
        self.log('debug', message, **kwargs)