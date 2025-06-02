import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

def setup_demo_data() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Create sample data for demo purposes
    
    Returns:
        Tuple of (patient_kits, call_logs, audit_logs)
    """
    # Create sample patient data
    patient_kits = [
        {
            'kit_id': 'KIT00001',
            'mrn': 'ENC(MRN12345)',
            'name': 'John Smith',
            'gender': 'Male',
            'dob': '1975-05-15',
            'phone': 'ENC(+14155552671)',
            'address': 'ENC(123 Main St, San Francisco, CA)',
            'email': 'ENC(john.smith@example.com)',
            'kit_status': 'delivered',
            'kit_sent': (datetime.now() - timedelta(days=10)).isoformat(),
            'created_at': (datetime.now() - timedelta(days=15)).isoformat(),
            'updated_at': datetime.now().isoformat()
        },
        {
            'kit_id': 'KIT00002',
            'mrn': 'ENC(MRN67890)',
            'name': 'Emily Johnson',
            'gender': 'Female',
            'dob': '1982-08-24',
            'phone': 'ENC(+14155552672)',
            'address': 'ENC(456 Oak St, San Francisco, CA)',
            'email': 'ENC(emily.johnson@example.com)',
            'kit_status': 'pending',
            'kit_sent': (datetime.now() - timedelta(days=3)).isoformat(),
            'created_at': (datetime.now() - timedelta(days=7)).isoformat(),
            'updated_at': datetime.now().isoformat()
        },
        {
            'kit_id': 'KIT00003',
            'mrn': 'ENC(MRN24680)',
            'name': 'Michael Wong',
            'gender': 'Male',
            'dob': '1990-02-10',
            'phone': 'ENC(+14155552673)',
            'address': 'ENC(789 Pine St, San Francisco, CA)',
            'email': 'ENC(michael.wong@example.com)',
            'kit_status': 'returned',
            'kit_sent': (datetime.now() - timedelta(days=25)).isoformat(),
            'kit_returned': (datetime.now() - timedelta(days=15)).isoformat(),
            'created_at': (datetime.now() - timedelta(days=30)).isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    ]
    
    # Create sample call logs
    call_logs = [
        {
            'id': str(uuid.uuid4()),
            'kit_id': 'KIT00001',
            'call_sid': 'CA12345678901234567890123456789012',
            'status': 'completed',
            'reminder_type': 'kit_delivery',
            'start_time': (datetime.now() - timedelta(days=8)).isoformat(),
            'end_time': (datetime.now() - timedelta(days=8, minutes=-5)).isoformat(),
            'duration': 300,
            'transcript': 'Patient confirmed kit was received and will complete soon.'
        },
        {
            'id': str(uuid.uuid4()),
            'kit_id': 'KIT00001',
            'call_sid': 'CA23456789012345678901234567890123',
            'status': 'completed',
            'reminder_type': 'kit_completion',
            'start_time': (datetime.now() - timedelta(days=5)).isoformat(),
            'end_time': (datetime.now() - timedelta(days=5, minutes=-4)).isoformat(),
            'duration': 240,
            'transcript': 'Patient says they completed the kit and will mail it back tomorrow.'
        },
        {
            'id': str(uuid.uuid4()),
            'kit_id': 'KIT00002',
            'call_sid': 'CA34567890123456789012345678901234',
            'status': 'no-answer',
            'reminder_type': 'kit_delivery',
            'start_time': (datetime.now() - timedelta(days=2)).isoformat(),
            'end_time': (datetime.now() - timedelta(days=2, minutes=-1)).isoformat(),
            'duration': 60,
            'transcript': None
        }
    ]
    
    # Create sample audit logs
    audit_logs = [
        {
            'id': str(uuid.uuid4()),
            'user_id': 'admin',
            'event_type': 'phi_access',
            'patient_mrn': 'MRN12345',
            'timestamp': (datetime.now() - timedelta(days=10)).isoformat(),
            'action_description': 'Viewed patient profile',
            'accessed_fields': ['name', 'phone', 'address', 'email'],
            'reason': 'Patient onboarding',
            'ip_address': '192.168.1.100'
        },
        {
            'id': str(uuid.uuid4()),
            'user_id': 'system',
            'event_type': 'call_initiated',
            'patient_mrn': 'MRN12345',
            'timestamp': (datetime.now() - timedelta(days=8)).isoformat(),
            'action_description': 'Automated call initiated',
            'accessed_fields': ['phone'],
            'reason': 'Kit delivery confirmation',
            'ip_address': '10.0.0.1'
        },
        {
            'id': str(uuid.uuid4()),
            'user_id': 'admin',
            'event_type': 'phi_access',
            'patient_mrn': 'MRN67890',
            'timestamp': (datetime.now() - timedelta(days=3)).isoformat(),
            'action_description': 'Viewed patient call history',
            'accessed_fields': ['name', 'phone'],
            'reason': 'Follow-up scheduling',
            'ip_address': '192.168.1.100'
        }
    ]
    
    return patient_kits, call_logs, audit_logs
