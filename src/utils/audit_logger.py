#!/usr/bin/env python
import os
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

# Configure logging
logger = logging.getLogger(__name__)

class AuditLogger:
    """
    HIPAA-compliant audit logging system
    
    Maintains a secure audit trail of all PHI access, modifications, and system events
    as required for HIPAA compliance.
    """
    
    EVENT_TYPES = {
        'access': 'PHI_ACCESS',        # Viewing patient information
        'create': 'PHI_CREATE',        # Creating new patient record
        'update': 'PHI_UPDATE',        # Updating patient information
        'delete': 'PHI_DELETE',        # Deleting patient information
        'export': 'PHI_EXPORT',        # Exporting/downloading patient data
        'call': 'PATIENT_CALL',        # Patient call events
        'auth': 'AUTH_EVENT',          # Authentication events
        'admin': 'ADMIN_ACTION',       # Administrative actions
        'system': 'SYSTEM_EVENT'       # System-level events
    }
    
    def __init__(self, log_dir: str = None, db_handler = None):
        """
        Initialize the audit logger
        
        Args:
            log_dir: Directory to store audit logs (if file-based)
            db_handler: Database handler for storing logs in database
        """
        self.db_handler = db_handler
        
        # Set up file-based logging if specified
        if log_dir:
            self.log_dir = log_dir
            os.makedirs(log_dir, exist_ok=True)
            
            # Set up file handler
            self.log_file = os.path.join(log_dir, f"audit_{datetime.now().strftime('%Y%m%d')}.log")
            self.file_handler = logging.FileHandler(self.log_file)
            self.file_handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(message)s')
            self.file_handler.setFormatter(formatter)
            
            # Add handler to logger
            audit_logger = logging.getLogger('audit')
            audit_logger.setLevel(logging.INFO)
            audit_logger.addHandler(self.file_handler)
            self.logger = audit_logger
        else:
            self.logger = logger
    
    def log_event(self, 
                 event_type: str, 
                 user_id: str = 'system', 
                 patient_id: Optional[str] = None,
                 resource_id: Optional[str] = None,
                 action: str = '',
                 details: Dict[str, Any] = None,
                 status: str = 'success') -> str:
        """
        Log an audit event
        
        Args:
            event_type: Type of event (access, create, update, etc.)
            user_id: ID of user performing the action
            patient_id: ID of patient (if applicable)
            resource_id: ID of resource being accessed (e.g., call_id)
            action: Description of action
            details: Additional details about the event
            status: Outcome of the event (success, failure)
            
        Returns:
            ID of the audit log entry
        """
        # Generate unique ID for this audit event
        event_id = str(uuid.uuid4())
        
        # Create audit event
        event = {
            'id': event_id,
            'timestamp': time.time(),
            'event_type': self.EVENT_TYPES.get(event_type, 'UNKNOWN_EVENT'),
            'user_id': user_id,
            'patient_id': patient_id,
            'resource_id': resource_id,
            'action': action,
            'details': details or {},
            'status': status
        }
        
        # Log to file if configured
        self.logger.info(f"AUDIT|{json.dumps(event)}")
        
        # Log to database if available
        if self.db_handler and hasattr(self.db_handler, 'save_audit_log'):
            try:
                self.db_handler.save_audit_log(event)
            except Exception as e:
                logger.error(f"Failed to save audit log to database: {str(e)}")
        
        return event_id
    
    def log_phi_access(self, 
                      user_id: str, 
                      patient_id: str,
                      reason: str,
                      phi_elements: List[str]) -> str:
        """
        Log PHI access event (specialized method for PHI access)
        
        Args:
            user_id: ID of user accessing PHI
            patient_id: ID of patient whose PHI is accessed
            reason: Reason for accessing PHI
            phi_elements: List of PHI elements accessed
            
        Returns:
            ID of the audit log entry
        """
        details = {
            'reason': reason,
            'phi_elements': phi_elements,
            'access_time': time.time()
        }
        
        return self.log_event(
            event_type='access',
            user_id=user_id,
            patient_id=patient_id,
            action='PHI_ACCESS',
            details=details
        )
    
    def log_call_event(self,
                      call_id: str,
                      patient_id: Optional[str],
                      event: str,
                      details: Dict[str, Any] = None) -> str:
        """
        Log call-related event
        
        Args:
            call_id: ID of the call
            patient_id: ID of patient
            event: Description of call event
            details: Additional details
            
        Returns:
            ID of the audit log entry
        """
        return self.log_event(
            event_type='call',
            patient_id=patient_id,
            resource_id=call_id,
            action=event,
            details=details
        )
    
    def log_phi_access_event(
        self,
        event_type: str,
        user_id: str,
        patient_mrn: Optional[str],
        action_description: str,
        accessed_fields: List[str],
        reason: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """
        Log PHI access for HIPAA compliance
        
        Args:
            event_type: Type of event (e.g., 'phi_view', 'transcript_view', 'manual_call')
            user_id: ID of the user accessing the PHI
            patient_mrn: Patient MRN (can be None for some events)
            action_description: Description of the action being performed
            accessed_fields: List of PHI fields being accessed
            reason: Reason for accessing the PHI
            ip_address: IP address of the user
            
        Returns:
            Dict containing the log entry
        """
        # For the demo, we'll just print the log rather than storing it
        log_entry = {
            'log_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'patient_mrn': patient_mrn,
            'action_description': action_description,
            'accessed_fields': accessed_fields,
            'reason': reason,
            'ip_address': ip_address
        }
        
        # Log the entry
        logger.info(f"PHI ACCESS: {json.dumps(log_entry)}")
        
        return log_entry


# Singleton instance for use throughout the application
_audit_logger = None

def get_audit_logger(log_dir: str = None, db_handler = None):
    """Get or create audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(log_dir, db_handler)
    return _audit_logger

def log_phi_access(
    event_type: str,
    user_id: str,
    patient_mrn: Optional[str],
    action_description: str,
    accessed_fields: List[str],
    reason: str,
    ip_address: str
) -> Dict[str, Any]:
    """
    Log PHI access for HIPAA compliance
    
    Args:
        event_type: Type of event (e.g., 'phi_view', 'transcript_view', 'manual_call')
        user_id: ID of the user accessing the PHI
        patient_mrn: Patient MRN (can be None for some events)
        action_description: Description of the action being performed
        accessed_fields: List of PHI fields being accessed
        reason: Reason for accessing the PHI
        ip_address: IP address of the user
        
    Returns:
        Dict containing the log entry
    """
    return get_audit_logger().log_phi_access_event(
        event_type,
        user_id,
        patient_mrn,
        action_description,
        accessed_fields,
        reason,
        ip_address
    )
