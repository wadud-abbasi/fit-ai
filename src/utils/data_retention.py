#!/usr/bin/env python
import os
import logging
import time
import json
from datetime import datetime, timedelta
from ..handlers.database_handler import get_database_handler
from .audit_logger import get_audit_logger

logger = logging.getLogger(__name__)

class DataRetentionPolicy:
    """
    Implements HIPAA-compliant data retention policies
    
    Manages the lifecycle of PHI data according to configurable retention periods,
    ensuring data is properly archived and/or deleted when retention periods expire.
    """
    
    def __init__(self, db_handler=None):
        """
        Initialize the data retention policy manager
        
        Args:
            db_handler: Database handler for data operations
        """
        self.db_handler = db_handler
        self.audit_logger = get_audit_logger()
        
        # Default retention periods (in days)
        self.retention_periods = {
            'call_recordings': 90,      # Voice recordings retention period
            'call_transcripts': 365,    # Call transcripts retention period
            'call_metadata': 730,       # Call metadata retention period
            'audit_logs': 2190,         # Audit logs retention (6 years for HIPAA)
            'inactive_patients': 2555   # Inactive patient records (7 years)
        }
        
        # Load custom retention periods from environment if available
        self._load_retention_config()
        
        logger.info(f"Data retention policy initialized with periods: {self.retention_periods}")
    
    def _load_retention_config(self):
        """Load retention periods from environment variables or config file"""
        # Check for environment variable overrides
        for key in self.retention_periods:
            env_key = f"RETENTION_{key.upper()}"
            if os.environ.get(env_key):
                try:
                    days = int(os.environ.get(env_key))
                    self.retention_periods[key] = days
                    logger.info(f"Loaded custom retention period for {key}: {days} days")
                except ValueError:
                    logger.warning(f"Invalid retention period in {env_key}, using default")
        
        # Check for config file
        config_path = os.environ.get('RETENTION_CONFIG_PATH')
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    for key, days in config.items():
                        if key in self.retention_periods and isinstance(days, int):
                            self.retention_periods[key] = days
                            logger.info(f"Loaded retention period from config for {key}: {days} days")
            except Exception as e:
                logger.error(f"Failed to load retention config file: {str(e)}")
    
    def execute_retention_policy(self):
        """Execute data retention policy based on configured periods"""
        if not self.db_handler:
            logger.warning("No database handler available, skipping retention policy execution")
            return False
        
        try:
            current_time = time.time()
            stats = {
                'calls_archived': 0,
                'transcripts_deleted': 0,
                'recordings_deleted': 0,
                'patients_archived': 0,
                'audit_logs_deleted': 0
            }
            
            # Archive old call recordings
            cutoff_timestamp = current_time - (self.retention_periods['call_recordings'] * 86400)
            if hasattr(self.db_handler, 'archive_call_recordings'):
                count = self.db_handler.archive_call_recordings(cutoff_timestamp)
                stats['calls_archived'] = count
                logger.info(f"Archived {count} call recordings older than {self.retention_periods['call_recordings']} days")
            
            # Delete old call transcripts
            cutoff_timestamp = current_time - (self.retention_periods['call_transcripts'] * 86400)
            if hasattr(self.db_handler, 'delete_call_transcripts'):
                count = self.db_handler.delete_call_transcripts(cutoff_timestamp)
                stats['transcripts_deleted'] = count
                logger.info(f"Deleted {count} call transcripts older than {self.retention_periods['call_transcripts']} days")
            
            # Archive inactive patients
            cutoff_timestamp = current_time - (self.retention_periods['inactive_patients'] * 86400)
            if hasattr(self.db_handler, 'archive_inactive_patients'):
                count = self.db_handler.archive_inactive_patients(cutoff_timestamp)
                stats['patients_archived'] = count
                logger.info(f"Archived {count} inactive patients with no activity for {self.retention_periods['inactive_patients']} days")
            
            # Delete old audit logs (if retention period passed)
            cutoff_timestamp = current_time - (self.retention_periods['audit_logs'] * 86400)
            if hasattr(self.db_handler, 'delete_audit_logs'):
                count = self.db_handler.delete_audit_logs(cutoff_timestamp)
                stats['audit_logs_deleted'] = count
                logger.info(f"Deleted {count} audit logs older than {self.retention_periods['audit_logs']} days")
            
            # Log retention policy execution
            self.audit_logger.log_event(
                event_type='system',
                action='RETENTION_POLICY_EXECUTED',
                details={
                    'statistics': stats,
                    'retention_periods': self.retention_periods
                }
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error executing retention policy: {str(e)}")
            return False
    
    def get_retention_status(self):
        """Get current retention policy status and statistics"""
        return {
            'retention_periods': self.retention_periods,
            'last_execution': getattr(self, 'last_execution', None),
            'next_scheduled_execution': getattr(self, 'next_execution', None)
        }


# Function to run the data retention policy on a schedule
def schedule_retention_policy(app, interval_hours=24):
    """
    Schedule the data retention policy to run at regular intervals
    
    Args:
        app: Flask application context
        interval_hours: How often to run the policy (in hours)
    """
    import threading
    import time
    
    db_handler = get_database_handler()
    retention_policy = DataRetentionPolicy(db_handler)
    
    def run_retention_job():
        with app.app_context():
            while True:
                logger.info("Running scheduled data retention policy job")
                retention_policy.execute_retention_policy()
                # Sleep for the specified interval
                time.sleep(interval_hours * 3600)
    
    # Start the retention policy thread
    retention_thread = threading.Thread(target=run_retention_job)
    retention_thread.daemon = True
    retention_thread.start()
    
    return retention_policy
