#!/usr/bin/env python
import os
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Union
from .database_handler import PostgreSQLHandler, EncryptionManager

logger = logging.getLogger(__name__)

class FitKitDatabaseHandler:
    """
    Specialized database handler for FIT kit reminders
    
    Manages two separate databases:
    1. Public tracking database: Non-PHI data about FIT kit status
    2. Private patient database: PHI/demographic data with encryption
    """
    
    def __init__(self, public_db_url=None, private_db_url=None):
        """
        Initialize the FIT kit database handler
        
        Args:
            public_db_url: URL for the public tracking database
            private_db_url: URL for the private PHI database
        """
        # Get database URLs from environment if not provided
        self.public_db_url = public_db_url or os.environ.get('DATABASE_URL_PUBLIC')
        self.private_db_url = private_db_url or os.environ.get('DATABASE_URL_PRIVATE')
        
        # Initialize database connections
        self.public_db = None
        self.private_db = None
        
        # Initialize encryption for PHI
        self.encryption = EncryptionManager()
        
        # Connect to databases if URLs are provided
        if self.public_db_url:
            try:
                self.public_db = PostgreSQLHandler(self.public_db_url)
                logger.info("Connected to public tracking database")
            except Exception as e:
                logger.error(f"Failed to connect to public database: {str(e)}")
        
        if self.private_db_url:
            try:
                self.private_db = PostgreSQLHandler(self.private_db_url)
                logger.info("Connected to private PHI database")
            except Exception as e:
                logger.error(f"Failed to connect to private database: {str(e)}")
        
        # Initialize database schemas
        if self.public_db:
            self._initialize_public_tables()
        
        if self.private_db:
            self._initialize_private_tables()
    
    def _initialize_public_tables(self):
        """Initialize public tracking database tables"""
        try:
            cursor = self.public_db.conn.cursor()
            
            # Create FIT kit status tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fit_kit_status (
                    id UUID PRIMARY KEY,
                    mrn TEXT UNIQUE NOT NULL,
                    kit_completed BOOLEAN DEFAULT FALSE,
                    result TEXT,
                    prior_letter BOOLEAN DEFAULT FALSE,
                    reminder_sent BOOLEAN DEFAULT FALSE,
                    second_reminder_sent BOOLEAN DEFAULT FALSE,
                    comments TEXT[],
                    chart_reviewer TEXT,
                    follow_up_caller TEXT,
                    patient_reached BOOLEAN DEFAULT FALSE,
                    callback_scheduled BOOLEAN DEFAULT FALSE,
                    callback_datetime TIMESTAMP,
                    unreachable_flag BOOLEAN DEFAULT FALSE,
                    kit_received BOOLEAN DEFAULT FALSE,
                    address_confirmed BOOLEAN DEFAULT FALSE,
                    needs_new_kit BOOLEAN DEFAULT FALSE,
                    new_kit_mailed BOOLEAN DEFAULT FALSE,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_fit_kit_status_mrn ON fit_kit_status(mrn)
            """)
            
            # Create index for callback scheduling
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_callback_datetime ON fit_kit_status(callback_scheduled, callback_datetime)
                WHERE callback_scheduled = TRUE
            """)
            
            self.public_db.conn.commit()
            cursor.close()
            logger.info("Public tracking database tables initialized")
            
        except Exception as e:
            logger.error(f"Error initializing public database tables: {str(e)}")
            if hasattr(self.public_db, 'conn'):
                self.public_db.conn.rollback()
    
    def _initialize_private_tables(self):
        """Initialize private PHI database tables"""
        try:
            cursor = self.private_db.conn.cursor()
            
            # Create patients table for PHI
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    mrn TEXT PRIMARY KEY,
                    patient_name TEXT,
                    dob DATE,
                    address TEXT,
                    phone_number TEXT,
                    language TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone_number)
            """)
            
            self.private_db.conn.commit()
            cursor.close()
            logger.info("Private PHI database tables initialized")
            
        except Exception as e:
            logger.error(f"Error initializing private database tables: {str(e)}")
            if hasattr(self.private_db, 'conn'):
                self.private_db.conn.rollback()
    
    def get_patient_by_mrn(self, mrn: str) -> Optional[Dict[str, Any]]:
        """
        Get patient information by MRN, combining public and private data
        
        Args:
            mrn: Medical Record Number
            
        Returns:
            Combined patient data or None if not found
        """
        if not self.private_db or not self.public_db:
            logger.error("Database connections not available")
            return None
        
        try:
            # Get patient PHI from private database
            patient = self._get_private_patient_by_mrn(mrn)
            
            if not patient:
                logger.warning(f"Patient with MRN {mrn} not found in private database")
                return None
            
            # Get FIT kit status from public database
            kit_status = self._get_kit_status_by_mrn(mrn)
            
            # Combine the data
            if kit_status:
                patient['kit_status'] = kit_status
            else:
                patient['kit_status'] = {}
                
            return patient
            
        except Exception as e:
            logger.error(f"Error retrieving patient by MRN: {str(e)}")
            return None
    
    def get_patient_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Get patient information by phone number
        
        Args:
            phone: Phone number
            
        Returns:
            Patient data or None if not found
        """
        if not self.private_db:
            logger.error("Private database connection not available")
            return None
        
        try:
            cursor = self.private_db.conn.cursor()
            
            # Query for patient with the given phone
            cursor.execute("""
                SELECT mrn, patient_name, dob, address, phone_number, language, created_at
                FROM patients
                WHERE phone_number = %s
            """, (phone,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            # Get column names
            columns = ['mrn', 'patient_name', 'dob', 'address', 'phone_number', 'language', 'created_at']
            patient = dict(zip(columns, row))
            
            # Decrypt PHI fields
            patient['patient_name'] = self.encryption.decrypt(patient['patient_name']) if patient['patient_name'] else ''
            patient['address'] = self.encryption.decrypt(patient['address']) if patient['address'] else ''
            
            # Format date
            if patient['dob'] and not isinstance(patient['dob'], str):
                patient['dob'] = patient['dob'].isoformat()
            
            # Get kit status if available
            if self.public_db:
                kit_status = self._get_kit_status_by_mrn(patient['mrn'])
                if kit_status:
                    patient['kit_status'] = kit_status
            
            return patient
            
        except Exception as e:
            logger.error(f"Error retrieving patient by phone: {str(e)}")
            return None
    
    def _get_private_patient_by_mrn(self, mrn: str) -> Optional[Dict[str, Any]]:
        """
        Get patient PHI from private database
        
        Args:
            mrn: Medical Record Number
            
        Returns:
            Patient PHI data or None if not found
        """
        try:
            cursor = self.private_db.conn.cursor()
            
            # Query for patient with the given MRN
            cursor.execute("""
                SELECT mrn, patient_name, dob, address, phone_number, language, created_at
                FROM patients
                WHERE mrn = %s
            """, (mrn,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            # Get column names
            columns = ['mrn', 'patient_name', 'dob', 'address', 'phone_number', 'language', 'created_at']
            patient = dict(zip(columns, row))
            
            # Decrypt PHI fields
            patient['patient_name'] = self.encryption.decrypt(patient['patient_name']) if patient['patient_name'] else ''
            patient['address'] = self.encryption.decrypt(patient['address']) if patient['address'] else ''
            
            # Format date
            if patient['dob'] and not isinstance(patient['dob'], str):
                patient['dob'] = patient['dob'].isoformat()
            
            return patient
            
        except Exception as e:
            logger.error(f"Error retrieving private patient data: {str(e)}")
            return None
    
    def _get_kit_status_by_mrn(self, mrn: str) -> Optional[Dict[str, Any]]:
        """
        Get FIT kit status from public database
        
        Args:
            mrn: Medical Record Number
            
        Returns:
            Kit status data or None if not found
        """
        try:
            cursor = self.public_db.conn.cursor()
            
            # Query for kit status with the given MRN
            cursor.execute("""
                SELECT id, kit_completed, result, prior_letter, reminder_sent, second_reminder_sent,
                       comments, chart_reviewer, follow_up_caller, patient_reached, callback_scheduled,
                       callback_datetime, unreachable_flag, kit_received, address_confirmed,
                       needs_new_kit, new_kit_mailed, updated_at
                FROM fit_kit_status
                WHERE mrn = %s
            """, (mrn,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            # Get column names
            columns = ['id', 'kit_completed', 'result', 'prior_letter', 'reminder_sent', 'second_reminder_sent',
                      'comments', 'chart_reviewer', 'follow_up_caller', 'patient_reached', 'callback_scheduled',
                      'callback_datetime', 'unreachable_flag', 'kit_received', 'address_confirmed',
                      'needs_new_kit', 'new_kit_mailed', 'updated_at']
            
            kit_status = dict(zip(columns, row))
            
            # Convert UUID to string
            kit_status['id'] = str(kit_status['id']) if kit_status['id'] else None
            
            # Format timestamp
            if kit_status['callback_datetime'] and not isinstance(kit_status['callback_datetime'], str):
                kit_status['callback_datetime'] = kit_status['callback_datetime'].isoformat()
            
            if kit_status['updated_at'] and not isinstance(kit_status['updated_at'], str):
                kit_status['updated_at'] = kit_status['updated_at'].isoformat()
            
            return kit_status
            
        except Exception as e:
            logger.error(f"Error retrieving kit status: {str(e)}")
            return None
    
    def save_patient(self, patient_data: Dict[str, Any]) -> bool:
        """
        Save patient PHI to private database
        
        Args:
            patient_data: Patient information
            
        Returns:
            True if successful
        """
        if not self.private_db:
            logger.error("Private database connection not available")
            return False
        
        try:
            cursor = self.private_db.conn.cursor()
            
            # Encrypt PHI fields
            patient_name = self.encryption.encrypt(patient_data.get('patient_name', '')) if patient_data.get('patient_name') else None
            address = self.encryption.encrypt(patient_data.get('address', '')) if patient_data.get('address') else None
            
            # Format date if string
            dob = patient_data.get('dob')
            if dob and isinstance(dob, str):
                dob = f"'{dob}'"  # Format for SQL
            elif dob:
                dob = f"'{dob.isoformat()}'"  # Already a date object
            else:
                dob = "NULL"
            
            # Insert or update patient
            cursor.execute(f"""
                INSERT INTO patients (mrn, patient_name, dob, address, phone_number, language, created_at)
                VALUES (%s, %s, {dob}, %s, %s, %s, NOW())
                ON CONFLICT (mrn) 
                DO UPDATE SET 
                    patient_name = EXCLUDED.patient_name,
                    dob = EXCLUDED.dob,
                    address = EXCLUDED.address,
                    phone_number = EXCLUDED.phone_number,
                    language = EXCLUDED.language
            """, (
                patient_data.get('mrn'),
                patient_name,
                address,
                patient_data.get('phone_number'),
                patient_data.get('language')
            ))
            
            self.private_db.conn.commit()
            cursor.close()
            
            # Create kit status entry if it doesn't exist
            if self.public_db:
                self._ensure_kit_status_exists(patient_data.get('mrn'))
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving patient: {str(e)}")
            if hasattr(self.private_db, 'conn'):
                self.private_db.conn.rollback()
            return False
    
    def _ensure_kit_status_exists(self, mrn: str) -> bool:
        """
        Ensure a FIT kit status entry exists for the patient
        
        Args:
            mrn: Medical Record Number
            
        Returns:
            True if successful
        """
        try:
            cursor = self.public_db.conn.cursor()
            
            # Check if status entry exists
            cursor.execute("""
                SELECT id FROM fit_kit_status WHERE mrn = %s
            """, (mrn,))
            
            if cursor.rowcount == 0:
                # Create new status entry
                status_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO fit_kit_status (id, mrn, updated_at)
                    VALUES (%s, %s, NOW())
                """, (status_id, mrn))
                
                self.public_db.conn.commit()
                logger.info(f"Created new FIT kit status entry for MRN {mrn}")
            
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring kit status exists: {str(e)}")
            if hasattr(self.public_db, 'conn'):
                self.public_db.conn.rollback()
            return False
    
    def update_kit_status(self, mrn: str, status_updates: Dict[str, Any]) -> bool:
        """
        Update FIT kit status in public database
        
        Args:
            mrn: Medical Record Number
            status_updates: Fields to update
            
        Returns:
            True if successful
        """
        if not self.public_db:
            logger.error("Public database connection not available")
            return False
        
        try:
            # Ensure kit status entry exists
            self._ensure_kit_status_exists(mrn)
            
            # Build update query
            update_fields = []
            update_values = []
            
            for field, value in status_updates.items():
                # Skip invalid fields
                if field in ['id', 'mrn', 'updated_at']:
                    continue
                
                # Handle array fields (comments)
                if field == 'comments' and isinstance(value, str):
                    update_fields.append(f"{field} = ARRAY_APPEND({field}, %s)")
                    update_values.append(value)
                elif field == 'comments' and isinstance(value, list):
                    update_fields.append(f"{field} = %s")
                    update_values.append(value)
                # Handle timestamp fields
                elif field == 'callback_datetime' and value:
                    update_fields.append(f"{field} = to_timestamp(%s)")
                    update_values.append(value)
                # Handle regular fields
                else:
                    update_fields.append(f"{field} = %s")
                    update_values.append(value)
            
            # Add updated_at timestamp
            update_fields.append("updated_at = NOW()")
            
            if not update_fields:
                logger.warning(f"No valid fields to update for MRN {mrn}")
                return True
            
            # Execute update query
            cursor = self.public_db.conn.cursor()
            
            query = f"""
                UPDATE fit_kit_status
                SET {', '.join(update_fields)}
                WHERE mrn = %s
            """
            
            # Add MRN to values
            update_values.append(mrn)
            
            cursor.execute(query, update_values)
            
            self.public_db.conn.commit()
            cursor.close()
            
            logger.info(f"Updated FIT kit status for MRN {mrn}: {', '.join(update_fields)}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating kit status: {str(e)}")
            if hasattr(self.public_db, 'conn'):
                self.public_db.conn.rollback()
            return False
    
    def get_patients_needing_reminder(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get patients who need a FIT kit reminder
        
        Args:
            limit: Maximum number of patients to return
            
        Returns:
            List of patient records
        """
        if not self.public_db or not self.private_db:
            logger.error("Database connections not available")
            return []
        
        try:
            cursor = self.public_db.conn.cursor()
            
            # Find patients who need reminders
            cursor.execute("""
                SELECT f.mrn
                FROM fit_kit_status f
                WHERE (f.reminder_sent = FALSE OR f.second_reminder_sent = FALSE)
                AND f.kit_completed = FALSE
                AND f.unreachable_flag = FALSE
                LIMIT %s
            """, (limit,))
            
            mrns = [row[0] for row in cursor.fetchall()]
            cursor.close()
            
            # Get patient data for each MRN
            patients = []
            for mrn in mrns:
                patient = self.get_patient_by_mrn(mrn)
                if patient:
                    patients.append(patient)
            
            return patients
            
        except Exception as e:
            logger.error(f"Error getting patients needing reminders: {str(e)}")
            return []
    
    def save_call_log(self, call_data: Dict[str, Any]) -> str:
        """
        Save call log to public database and update kit status
        
        Args:
            call_data: Call information
            
        Returns:
            Call ID
        """
        if not self.public_db:
            logger.error("Public database connection not available")
            return None
        
        try:
            # Generate UUID if not provided
            call_id = call_data.get('id') or str(uuid.uuid4())
            
            # Update FIT kit status based on call outcome
            mrn = call_data.get('mrn')
            if mrn:
                # Determine which reminder this is
                status_updates = {}
                
                # Mark patient as reached
                status_updates['patient_reached'] = True
                
                # Update reminder flags based on call data
                if call_data.get('reminder_type') == 'first_reminder':
                    status_updates['reminder_sent'] = True
                elif call_data.get('reminder_type') == 'second_reminder':
                    status_updates['second_reminder_sent'] = True
                
                # Add call outcome as comment
                if call_data.get('outcome'):
                    status_updates['comments'] = call_data.get('outcome')
                
                # Update kit status
                self.update_kit_status(mrn, status_updates)
            
            return call_id
            
        except Exception as e:
            logger.error(f"Error saving call log: {str(e)}")
            return None
    
    def update_from_conversation_summary(self, mrn: str, summary: Dict[str, Any]) -> bool:
        """
        Update databases based on conversation summary
        
        Args:
            mrn: Medical Record Number
            summary: Conversation summary from GPT
            
        Returns:
            True if successful
        """
        try:
            # Update public tracking database
            if self.public_db:
                kit_status_updates = {}
                
                # Extract FIT kit status fields
                if 'kit_completed' in summary:
                    kit_status_updates['kit_completed'] = summary['kit_completed']
                
                if 'patient_reached' in summary:
                    kit_status_updates['patient_reached'] = summary['patient_reached']
                
                if 'needs_new_kit' in summary:
                    kit_status_updates['needs_new_kit'] = summary['needs_new_kit']
                
                if 'address_confirmed' in summary:
                    kit_status_updates['address_confirmed'] = summary['address_confirmed']
                
                if 'callback_scheduled' in summary:
                    kit_status_updates['callback_scheduled'] = summary['callback_scheduled']
                
                if 'callback_datetime' in summary:
                    kit_status_updates['callback_datetime'] = summary['callback_datetime']
                
                if 'comments' in summary and summary['comments']:
                    kit_status_updates['comments'] = summary['comments']
                
                # Update kit status
                if kit_status_updates:
                    self.update_kit_status(mrn, kit_status_updates)
            
            # Update private patient database
            if self.private_db:
                patient_updates = {}
                
                # Extract patient PHI fields
                if 'address' in summary:
                    patient_updates['address'] = summary['address']
                
                if 'language' in summary:
                    patient_updates['language'] = summary['language']
                
                # Update patient data
                if patient_updates:
                    self.save_patient({
                        'mrn': mrn,
                        **patient_updates
                    })
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating from conversation summary: {str(e)}")
            return False


# Function to get FIT kit database handler
def get_fit_kit_db_handler():
    """Get FIT kit database handler singleton"""
    if not hasattr(get_fit_kit_db_handler, 'instance'):
        public_db_url = os.environ.get('DATABASE_URL_PUBLIC')
        private_db_url = os.environ.get('DATABASE_URL_PRIVATE')
        
        if not public_db_url or not private_db_url:
            logger.warning("Missing database URLs for FIT kit handler")
            return None
        
        get_fit_kit_db_handler.instance = FitKitDatabaseHandler(
            public_db_url=public_db_url,
            private_db_url=private_db_url
        )
    
    return get_fit_kit_db_handler.instance
