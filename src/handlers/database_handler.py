import os
import json
import time
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Simple encryption manager for sensitive data
    
    In a real implementation, this would use proper encryption.
    For this mock/demo version, we just prefix/suffix the string.
    """
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext to ciphertext"""
        if not plaintext:
            return ""
        return f"ENC({plaintext})"
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext to plaintext"""
        if not ciphertext or not ciphertext.startswith("ENC(") or not ciphertext.endswith(")"): 
            return ciphertext
        return ciphertext[4:-1]  # Remove ENC( and )


class DatabaseHandler:
    """Abstract base class for database handlers"""
    
    def __init__(self):
        """Initialize database handler"""
        self.encryption = EncryptionManager()
    
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient by ID"""
        raise NotImplementedError("Subclass must implement abstract method")
    
    def get_patient_by_mrn(self, mrn: str) -> Optional[Dict[str, Any]]:
        """Get patient by MRN"""
        raise NotImplementedError("Subclass must implement abstract method")
    
    def get_patient_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get patient by phone number"""
        raise NotImplementedError("Subclass must implement abstract method")
    
    def save_call_log(self, call_data: Dict[str, Any]) -> str:
        """Save call log and return UUID"""
        raise NotImplementedError("Subclass must implement abstract method")
    
    def save_conversation(self, call_id: str, conversation: List[Dict[str, str]]) -> bool:
        """Save conversation history to database"""
        raise NotImplementedError("Subclass must implement abstract method")
    
    def get_call_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get call history for a patient ID"""
        raise NotImplementedError("Subclass must implement abstract method")
    
    def get_conversation(self, call_id: str) -> List[Dict[str, str]]:
        """Get conversation history for a call"""
        raise NotImplementedError("Subclass must implement abstract method")
    
    def close(self):
        """Close database connection"""
        pass


class PostgresHandler(DatabaseHandler):
    """PostgreSQL implementation of database handler"""
    
    def __init__(self, connection_string: str):
        """Initialize database handler with connection string"""
        super().__init__()
        import psycopg2
        self.conn = psycopg2.connect(connection_string)
        logger.info("Connected to PostgreSQL database")
        
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        Get patient by UUID
        
        Args:
            patient_id: UUID of the patient
            
        Returns:
            Dictionary with patient information or None if not found
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT id, mrn, name, gender, race, phone, address, created_at
                FROM patients
                WHERE id = %s
            """, (patient_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            # Decrypt sensitive fields
            name = self.encryption.decrypt(row[2]) if row[2] else ''
            address = self.encryption.decrypt(row[6]) if row[6] else ''
            
            return {
                'id': str(row[0]),
                'mrn': row[1],
                'name': name,
                'gender': row[3],
                'race': row[4],
                'phone': row[5],
                'address': address,
                'created_at': row[7].timestamp() if row[7] else None
            }
            
        except Exception as e:
            logger.error(f"Error retrieving patient: {str(e)}")
            return None
            
    def get_patient_by_mrn(self, mrn: str) -> Optional[Dict[str, Any]]:
        """
        Get patient by MRN
        
        Args:
            mrn: Patient MRN
            
        Returns:
            Dictionary with patient information or None if not found
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT id, mrn, name, gender, race, phone, address, created_at
                FROM patients
                WHERE mrn = %s
            """, (mrn,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            # Decrypt sensitive fields
            name = self.encryption.decrypt(row[2]) if row[2] else ''
            address = self.encryption.decrypt(row[6]) if row[6] else ''
            
            return {
                'id': str(row[0]),
                'mrn': row[1],
                'name': name,
                'gender': row[3],
                'race': row[4],
                'phone': row[5],
                'address': address,
                'created_at': row[7].timestamp() if row[7] else None
            }
            
        except Exception as e:
            logger.error(f"Error retrieving patient by MRN: {str(e)}")
            return None
            
    def get_patient_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Get patient by phone number
        
        Args:
            phone: Patient phone number
            
        Returns:
            Dictionary with patient information or None if not found
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT id, mrn, name, gender, race, phone, address, created_at
                FROM patients
                WHERE phone = %s
            """, (phone,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            # Decrypt sensitive fields
            name = self.encryption.decrypt(row[2]) if row[2] else ''
            address = self.encryption.decrypt(row[6]) if row[6] else ''
            
            return {
                'id': str(row[0]),
                'mrn': row[1],
                'name': name,
                'gender': row[3],
                'race': row[4],
                'phone': row[5],
                'address': address,
                'created_at': row[7].timestamp() if row[7] else None
            }
            
        except Exception as e:
            logger.error(f"Error retrieving patient by phone: {str(e)}")
            return None
            
    def save_call_log(self, call_data: Dict[str, Any]) -> str:
        """
        Save call log to database and return UUID
        
        Args:
            call_data: Dictionary with call information
            
        Returns:
            UUID of the call as string
        """
        try:
            cursor = self.conn.cursor()
            
            # Generate UUID if not provided
            call_id = call_data.get('id') or str(uuid.uuid4())
            
            # Insert call data
            cursor.execute("""
                INSERT INTO calls (id, call_sid, patient_id, reminder_type, status, start_time, end_time, duration)
                VALUES (%s, %s, %s, %s, %s, to_timestamp(%s), %s, %s)
                ON CONFLICT (id) 
                DO UPDATE SET 
                    call_sid = EXCLUDED.call_sid,
                    status = EXCLUDED.status,
                    end_time = EXCLUDED.end_time,
                    duration = EXCLUDED.duration
                RETURNING id
            """, (
                call_id,
                call_data.get('call_sid', ''),
                call_data.get('patient_id'),
                call_data.get('reminder_type', 'general'),
                call_data.get('status', 'initiated'),
                call_data.get('start_time', time.time()),
                None if 'end_time' not in call_data else f"to_timestamp({call_data['end_time']})",
                call_data.get('duration', None)
            ))
            
            # Get the UUID
            result = cursor.fetchone()
            call_id = str(result[0]) if result else call_id
            
            self.conn.commit()
            cursor.close()
            return call_id
            
        except Exception as e:
            logger.error(f"Error saving call log: {str(e)}")
            self.conn.rollback()
            return None
    
    def save_conversation(self, call_id: str, conversation: List[Dict[str, str]]) -> bool:
        """
        Save conversation history to database
        
        Args:
            call_id: Call UUID
            conversation: List of message objects with role and content
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            
            # First check if call exists
            cursor.execute("SELECT id FROM calls WHERE id = %s", (call_id,))
            if cursor.rowcount == 0:
                logger.warning(f"Call {call_id} not found in database, cannot save conversation")
                cursor.close()
                return False
            
            # Delete existing conversation for this call
            cursor.execute("DELETE FROM conversations WHERE call_id = %s", (call_id,))
            
            # Insert conversation messages
            for i, message in enumerate(conversation):
                # Encrypt content if it's a user message (contains PHI)
                content = message.get('content', '')
                if message.get('role') == 'user':
                    content = self.encryption.encrypt(content)
                
                cursor.execute("""
                    INSERT INTO conversations (call_id, role, content, timestamp)
                    VALUES (%s, %s, %s, NOW())
                """, (
                    call_id,
                    message.get('role', 'unknown'),
                    content
                ))
            
            self.conn.commit()
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation: {str(e)}")
            self.conn.rollback()
            return False
    
    def get_call_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Get call history for a patient ID
        
        Args:
            patient_id: Patient UUID
            
        Returns:
            List of call records
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT id, call_sid, reminder_type, status, 
                       EXTRACT(EPOCH FROM start_time) as start_time,
                       EXTRACT(EPOCH FROM end_time) as end_time,
                       duration
                FROM calls
                WHERE patient_id = %s
                ORDER BY start_time DESC
            """, (patient_id,))
            
            columns = [desc[0] for desc in cursor.description]
            calls = []
            
            for row in cursor.fetchall():
                call_data = dict(zip(columns, row))
                # Convert UUID to string
                call_data['id'] = str(call_data['id'])
                calls.append(call_data)
            
            cursor.close()
            return calls
            
        except Exception as e:
            logger.error(f"Error retrieving call history: {str(e)}")
            return []
    
    def get_conversation(self, call_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a call
        
        Args:
            call_id: Call UUID
            
        Returns:
            List of message objects with role and content
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT role, content
                FROM conversations
                WHERE call_id = %s
                ORDER BY id ASC
            """, (call_id,))
            
            conversation = []
            
            for row in cursor.fetchall():
                role = row[0]
                content = row[1]
                
                # Decrypt content if it's a user message (contains PHI)
                if role == 'user':
                    content = self.encryption.decrypt(content)
                
                conversation.append({
                    'role': role,
                    'content': content
                })
            
            cursor.close()
            return conversation
            
        except Exception as e:
            logger.error(f"Error retrieving conversation: {str(e)}")
            return []
            
    def save_audit_log(self, audit_data: Dict[str, Any]) -> str:
        """
        Save audit log entry to database and return UUID
        
        Args:
            audit_data: Dictionary with audit information
            
        Returns:
            UUID of the audit log entry as string
        """
        try:
            cursor = self.conn.cursor()
            
            # Generate UUID if not provided
            audit_id = audit_data.get('id') or str(uuid.uuid4())
            
            # Convert accessed_fields list to array string if present
            accessed_fields = audit_data.get('accessed_fields', [])
            accessed_fields_str = '{' + ','.join(f'"{field}"' for field in accessed_fields) + '}' if accessed_fields else None
            
            # Insert audit data
            cursor.execute("""
                INSERT INTO audit_logs (id, user_id, event_type, patient_mrn, timestamp, action_description, 
                                      accessed_fields, reason, ip_address)
                VALUES (%s, %s, %s, %s, to_timestamp(%s), %s, %s, %s, %s)
                RETURNING id
            """, (
                audit_id,
                audit_data.get('user_id'),
                audit_data.get('event_type'),
                audit_data.get('patient_mrn'),
                audit_data.get('timestamp', time.time()),
                audit_data.get('action_description'),
                accessed_fields_str,
                audit_data.get('reason'),
                audit_data.get('ip_address')
            ))
            
            # Get the UUID
            result = cursor.fetchone()
            audit_id = str(result[0]) if result else audit_id
            
            self.conn.commit()
            cursor.close()
            return audit_id
            
        except Exception as e:
            logger.error(f"Error saving audit log: {str(e)}")
            self.conn.rollback()
            return None
    
    def get_audit_logs(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get audit logs with optional filters
        
        Args:
            filters: Dictionary of filter criteria
            
        Returns:
            List of audit log records
        """
        try:
            cursor = self.conn.cursor()
            
            query = "SELECT id, user_id, event_type, patient_mrn, EXTRACT(EPOCH FROM timestamp) as timestamp, " + \
                   "action_description, accessed_fields, reason, ip_address FROM audit_logs"
            
            params = []
            where_clauses = []
            
            if filters:
                for key, value in filters.items():
                    if key in ['user_id', 'event_type', 'patient_mrn', 'ip_address']:
                        where_clauses.append(f"{key} = %s")
                        params.append(value)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            
            columns = [desc[0] for desc in cursor.description]
            logs = []
            
            for row in cursor.fetchall():
                log_data = dict(zip(columns, row))
                # Convert UUID to string and array to list
                log_data['id'] = str(log_data['id'])
                log_data['accessed_fields'] = log_data['accessed_fields'][1:-1].split(',') if log_data['accessed_fields'] else []
                logs.append(log_data)
            
            cursor.close()
            return logs
            
        except Exception as e:
            logger.error(f"Error retrieving audit logs: {str(e)}")
            return []
    
    def close(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()
            
    def save_transcript(self, call_id: str, transcript: str) -> bool:
        """
        Save transcript to database
        
        Args:
            call_id: Call UUID
            transcript: Full transcript text
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            
            # First check if call exists
            cursor.execute("SELECT id FROM calls WHERE id = %s", (call_id,))
            if cursor.rowcount == 0:
                logger.warning(f"Call {call_id} not found in database, cannot save transcript")
                cursor.close()
                return False
            
            # Insert or update transcript
            cursor.execute("""
                INSERT INTO transcripts (call_id, transcript_text, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (call_id) 
                DO UPDATE SET 
                    transcript_text = EXCLUDED.transcript_text,
                    updated_at = NOW()
            """, (call_id, self.encryption.encrypt(transcript)))
            
            self.conn.commit()
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving transcript: {str(e)}")
            self.conn.rollback()
            return False
            
    def get_transcript(self, call_id: str) -> Optional[str]:
        """
        Get transcript for a call
        
        Args:
            call_id: Call UUID
            
        Returns:
            Transcript text or None if not found
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT transcript_text
                FROM transcripts
                WHERE call_id = %s
            """, (call_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
                
            # Decrypt transcript text
            return self.encryption.decrypt(row[0])
            
        except Exception as e:
            logger.error(f"Error retrieving transcript: {str(e)}")
            return None


class ConsolidatedDatabaseHandler(DatabaseHandler):
    """Consolidated database handler for simplified telehealth system"""
    
    def __init__(self):
        """Initialize in-memory database"""
        super().__init__()
        self.patient_kits = []
        self.call_logs = []
        self.audit_logs = []
        logger.info("Initialized consolidated database handler")
    
    def save_patient_kit(self, patient_data: Dict[str, Any]) -> str:
        """Save combined patient and kit information and return ID"""
        # Generate a unique ID if not provided
        if 'kit_id' not in patient_data:
            patient_data['kit_id'] = f"KIT{len(self.patient_kits) + 1:05}"
        
        patient_data['created_at'] = datetime.now().isoformat()
        patient_data['updated_at'] = datetime.now().isoformat()
        
        # Encrypt sensitive data
        if 'mrn' in patient_data:
            patient_data['mrn'] = self.encryption.encrypt(patient_data['mrn'])
        if 'phone' in patient_data:
            patient_data['phone'] = self.encryption.encrypt(patient_data['phone'])
        if 'address' in patient_data:
            patient_data['address'] = self.encryption.encrypt(patient_data['address'])
        if 'email' in patient_data:
            patient_data['email'] = self.encryption.encrypt(patient_data['email'])
            
        self.patient_kits.append(patient_data)
        logger.info(f"Saved patient with kit ID {patient_data['kit_id']}")
        return patient_data['kit_id']
    
    def get_patient_kit(self, kit_id: str) -> Optional[Dict[str, Any]]:
        """Get patient kit by ID"""
        for patient in self.patient_kits:
            if patient.get('kit_id') == kit_id:
                return patient
        return None
    
    def get_patient_kit_by_mrn(self, mrn: str) -> Optional[Dict[str, Any]]:
        """Get patient kit by MRN"""
        for patient in self.patient_kits:
            if self.encryption.decrypt(patient.get('mrn')) == mrn:
                return patient
        return None
    
    def save_patient_kit(self, patient_data: Dict[str, Any]) -> str:
        """Save combined patient and kit information and return ID"""
        # Generate a unique ID if not provided
        if 'kit_id' not in patient_data:
            patient_data['kit_id'] = f"KIT{len(self.patient_kits) + 1:05}"
        
        patient_data['created_at'] = datetime.now().isoformat()
        patient_data['updated_at'] = datetime.now().isoformat()
        
        # Encrypt sensitive data
        if 'mrn' in patient_data:
            patient_data['mrn'] = self.encryption.encrypt(patient_data['mrn'])
        if 'phone' in patient_data:
            patient_data['phone'] = self.encryption.encrypt(patient_data['phone'])
        if 'address' in patient_data:
            patient_data['address'] = self.encryption.encrypt(patient_data['address'])
        if 'email' in patient_data:
            patient_data['email'] = self.encryption.encrypt(patient_data['email'])
            
        self.patient_kits.append(patient_data)
        logger.info(f"Saved patient with kit ID {patient_data['kit_id']}")
        return patient_data['kit_id']
    
    def get_patient_kit(self, kit_id: str) -> Optional[Dict[str, Any]]:
        """Get patient kit by ID"""
        for patient in self.patient_kits:
            if patient.get('kit_id') == kit_id:
                return patient
        return None
    
    def get_patient_kit_by_mrn(self, mrn: str) -> Optional[Dict[str, Any]]:
        """Get patient kit by MRN"""
        for patient in self.patient_kits:
            if self.encryption.decrypt(patient.get('mrn')) == mrn:
                return patient
        return None
    
    def get_patient_kit_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get patient kit by phone number"""
        for patient in self.patient_kits:
            if self.encryption.decrypt(patient.get('phone')) == phone:
                return patient
        return None
        
    def list_patients(self) -> List[Dict[str, Any]]:
        """List all patients with kit information"""
        return self.patient_kits
        
    # Method implementations for the abstract base class
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient by ID - implements abstract method"""
        return self.get_patient_kit(patient_id)
        
    def get_patient_by_mrn(self, mrn: str) -> Optional[Dict[str, Any]]:
        """Get patient by MRN - implements abstract method"""
        return self.get_patient_kit_by_mrn(mrn)
        
    def get_patient_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get patient by phone number - implements abstract method"""
        return self.get_patient_kit_by_phone(phone)
    
    def save_call_log(self, call_data: Dict[str, Any]) -> str:
        """Save call log and return UUID"""
        call_id = str(uuid.uuid4())
        call_data['id'] = call_id
        call_data['timestamp'] = datetime.now().isoformat()
        self.call_logs.append(call_data)
        logger.info(f"Saved call log with ID {call_id}")
        return call_id
    
    def get_call_logs(self, kit_id: str = None) -> List[Dict[str, Any]]:
        """Get call logs with optional kit ID filter"""
        if kit_id:
            return [call for call in self.call_logs if call.get('kit_id') == kit_id]
        return self.call_logs
    
    def save_audit_log(self, audit_data: Dict[str, Any]) -> str:
        """Save audit log entry and return UUID"""
        audit_id = str(uuid.uuid4())
        audit_data['id'] = audit_id
        audit_data['timestamp'] = datetime.now().isoformat()
        self.audit_logs.append(audit_data)
        logger.info(f"Saved audit log with ID {audit_id}")
        return audit_id
    
    def get_audit_logs(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get audit logs with optional filters"""
        if not filters:
            return self.audit_logs
        
        filtered_logs = self.audit_logs
        for key, value in filters.items():
            filtered_logs = [log for log in filtered_logs if log.get(key) == value]
        
        return filtered_logs
    def save_transcript(self, call_id: str, transcript: str) -> bool:
        """Save call transcript for a completed call"""
        for call in self.call_logs:
            if call.get('id') == call_id:
                call['transcript'] = transcript
                logger.info(f"Saved transcript for call {call_id}")
                return True
        logger.warning(f"Call {call_id} not found for transcript")
        return False
    
    def get_transcript(self, call_id: str) -> Optional[str]:
        """Get transcript for a call"""
        for call in self.call_logs:
            if call.get('id') == call_id and 'transcript' in call:
                return call['transcript']
        return None


    def list_patients(self) -> List[Dict[str, Any]]:
        """List all patients with kit information"""
        return self.patient_kits
        
    def simulate_call_completion(self, kit_id: str, call_sid: str, outcome: str = "completed") -> bool:
        """Simulate the completion of a call for testing purposes"""
        # Find relevant call record
        for call in self.call_logs:
            if call.get('call_sid') == call_sid:
                call['status'] = outcome
                call['end_time'] = datetime.now().isoformat()
                logger.info(f"Call {call_sid} to kit {kit_id} marked as {outcome}")
                return True
        logger.warning(f"Call {call_sid} not found for completion simulation")
        return False


# Factory function to create the database handler
def get_database_handler() -> DatabaseHandler:
    """
    Factory function to create the appropriate database handler
    
    Returns:
        DatabaseHandler instance (PostgreSQL or Consolidated based on env)
    """
    # Get database type from environment
    db_type = os.environ.get('DB_TYPE', 'consolidated').lower()
    
    if db_type == 'postgres':
        # Get PostgreSQL connection string from environment
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '5432')
        db_name = os.environ.get('DB_NAME', 'healthcare')
        db_user = os.environ.get('DB_USER', 'postgres')
        db_password = os.environ.get('DB_PASSWORD', '')
        
        connection_string = f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_password}"
        
        try:
            return PostgresHandler(connection_string)
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}. Falling back to consolidated handler.")
    
    # Default to consolidated handler
    logger.info("Using consolidated in-memory database handler")
    
    # Import mock data provider to initialize with sample data
    from ..routes.db_mock_data import setup_demo_data
    
    # Create consolidated database handler
    db_handler = ConsolidatedDatabaseHandler()
    
    # Initialize with demo data
    patient_kits, call_logs, audit_logs = setup_demo_data()
    db_handler.patient_kits = patient_kits
    db_handler.call_logs = call_logs
    db_handler.audit_logs = audit_logs
    
    logger.info(f"Initialized database handler with {len(patient_kits)} patients")
    return db_handler
        Args:
            call_id: Call UUID
            conversation: List of message objects with role and content
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            
            # First check if call exists
            cursor.execute("SELECT id FROM calls WHERE id = %s", (call_id,))
            if cursor.rowcount == 0:
                logger.warning(f"Call {call_id} not found in database, cannot save conversation")
                cursor.close()
                return False
            
            # Delete existing conversation for this call
            cursor.execute("DELETE FROM conversations WHERE call_id = %s", (call_id,))
            
            # Insert conversation messages
            for i, message in enumerate(conversation):
                # Encrypt content if it's a user message (contains PHI)
                content = message.get('content', '')
                if message.get('role') == 'user':
                    content = self.encryption.encrypt(content)
                
                cursor.execute("""
                    INSERT INTO conversations (call_id, role, content, timestamp)
                    VALUES (%s, %s, %s, NOW())
                """, (
                    call_id,
                    message.get('role', 'unknown'),
                    content
                ))
            
            self.conn.commit()
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation: {str(e)}")
            self.conn.rollback()
            return False
    
    def get_call_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Get call history for a patient ID
        
        Args:
            patient_id: Patient UUID
            
        Returns:
            List of call records
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT id, call_sid, reminder_type, status, 
                       EXTRACT(EPOCH FROM start_time) as start_time,
                       EXTRACT(EPOCH FROM end_time) as end_time,
                       duration
                FROM calls
                WHERE patient_id = %s
                ORDER BY start_time DESC
            """, (patient_id,))
            
            columns = [desc[0] for desc in cursor.description]
            calls = []
            
            for row in cursor.fetchall():
                call_data = dict(zip(columns, row))
                # Convert UUID to string
                call_data['id'] = str(call_data['id'])
                calls.append(call_data)
            
            cursor.close()
            return calls
            
        except Exception as e:
            logger.error(f"Error retrieving call history: {str(e)}")
            return []
    
    def get_call_by_sid(self, call_sid: str) -> Optional[Dict[str, Any]]:
        """
        Get call by Twilio SID
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            Dictionary with call information or None if not found
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT id, call_sid, patient_id, reminder_type, status, 
                       EXTRACT(EPOCH FROM start_time) as start_time,
                       EXTRACT(EPOCH FROM end_time) as end_time,
                       duration
                FROM calls
                WHERE call_sid = %s
            """, (call_sid,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            columns = [desc[0] for desc in cursor.description]
            call_data = dict(zip(columns, row))
            
            # Convert UUIDs to strings
            call_data['id'] = str(call_data['id'])
            call_data['patient_id'] = str(call_data['patient_id']) if call_data['patient_id'] else None
            
            return call_data
            
        except Exception as e:
            logger.error(f"Error retrieving call by SID: {str(e)}")
            return None
    
    def get_conversation(self, call_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a call
        
        Args:
            call_id: Call UUID
            
        Returns:
            List of message objects with role and content
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT role, content
                FROM conversations
                WHERE call_id = %s
                ORDER BY id ASC
            """, (call_id,))
            
            conversation = []
            
            for row in cursor.fetchall():
                role = row[0]
                content = row[1]
                
                # Decrypt content if it's a user message (contains PHI)
                if role == 'user':
                    content = self.encryption.decrypt(content)
                
                conversation.append({
                    'role': role,
                    'content': content
                })
            
            cursor.close()
            return conversation
            
        except Exception as e:
            logger.error(f"Error retrieving conversation: {str(e)}")
            return []
    
    def close(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()


class FirebaseHandler(DatabaseHandler):
    """Firebase implementation of database handler"""
    
    def __init__(self, credentials_path: Optional[str] = None, credentials_json: Optional[Dict] = None):
        """
        Initialize Firebase handler
        
        Args:
            credentials_path: Path to Firebase credentials JSON file
            credentials_json: Firebase credentials as a dictionary
        """
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
            
            # Initialize Firebase app
            if credentials_path:
                cred = credentials.Certificate(credentials_path)
            elif credentials_json:
                cred = credentials.Certificate(credentials_json)
            else:
                raise ValueError("Either credentials_path or credentials_json must be provided")
            
            # Check if app already initialized
            try:
                self.app = firebase_admin.get_app()
            except ValueError:
                self.app = firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
            logger.info("Connected to Firebase")
            
        except ImportError:
            logger.error("firebase_admin not installed, cannot use Firebase")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Firebase: {str(e)}")
            raise
    
    def save_call_log(self, call_data: Dict[str, Any]) -> bool:
        """
        Save call log to database
        
        Args:
            call_data: Dictionary with call information
            
        Returns:
            True if successful
        """
        try:
            call_sid = call_data.get('call_sid')
            if not call_sid:
                logger.error("Cannot save call log: missing call_sid")
                return False
            
            # Add timestamps
            if 'start_time' in call_data:
                from firebase_admin import firestore
                call_data['start_time'] = firestore.SERVER_TIMESTAMP
                
            if 'end_time' in call_data:
                from firebase_admin import firestore
                call_data['end_time'] = firestore.SERVER_TIMESTAMP
            
            # Save to Firestore
            self.db.collection('calls').document(call_sid).set(call_data, merge=True)
            return True
            
        except Exception as e:
            logger.error(f"Error saving call log: {str(e)}")
            return False
    
    def save_conversation(self, call_sid: str, conversation: List[Dict[str, str]]) -> bool:
        """
        Save conversation history to database
        
        Args:
            call_sid: Twilio call SID
            conversation: List of message objects with role and content
            
        Returns:
            True if successful
        """
        try:
            # Save conversation as a subcollection
            batch = self.db.batch()
            
            # Delete existing messages
            existing_msgs = self.db.collection(f'calls/{call_sid}/messages').stream()
            for msg in existing_msgs:
                batch.delete(msg.reference)
            
            # Add new messages
            for i, message in enumerate(conversation):
                msg_ref = self.db.collection(f'calls/{call_sid}/messages').document(f'msg_{i:03d}')
                msg_data = {
                    'role': message.get('role', 'unknown'),
                    'content': message.get('content', ''),
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'order': i
                }
                batch.set(msg_ref, msg_data)
            
            # Commit the batch
            batch.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation: {str(e)}")
            return False
    
    def get_call_history(self, phone_number: str) -> List[Dict[str, Any]]:
        """
        Get call history for a phone number
        
        Args:
            phone_number: Patient phone number
            
        Returns:
            List of call records
        """
        try:
            # Query calls by phone number
            query = self.db.collection('calls').where('phone_number', '==', phone_number).order_by('start_time', direction='DESCENDING')
            docs = query.stream()
            
            calls = []
            for doc in docs:
                call_data = doc.to_dict()
                call_data['call_sid'] = doc.id
                calls.append(call_data)
            
            return calls
            
        except Exception as e:
            logger.error(f"Error retrieving call history: {str(e)}")
            return []
    
    def get_conversation(self, call_sid: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a call
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            List of message objects with role and content
        """
        try:
            # Get messages from subcollection
            query = self.db.collection(f'calls/{call_sid}/messages').order_by('order')
            docs = query.stream()
            
            conversation = []
            for doc in docs:
                msg_data = doc.to_dict()
                conversation.append({
                    'role': msg_data.get('role', 'unknown'),
                    'content': msg_data.get('content', '')
                })
            
            return conversation
            
        except Exception as e:
            logger.error(f"Error retrieving conversation: {str(e)}")
            return []


def get_database_handler() -> MockDatabaseHandler:
    """
    Factory function to create the appropriate database handler
    
    For the demo version, we always return the MockDatabaseHandler
    regardless of environment variables.
    
    Returns:
        MockDatabaseHandler instance with mock data
    """
    # Always return MockDatabaseHandler for the demo
    logger.info("Using mock database handler for demo")
    return MockDatabaseHandler()
