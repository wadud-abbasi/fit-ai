#!/usr/bin/env python
"""
Minimalist Telehealth System
Stripped down version with no web interface
"""
import os
import json
import logging
import sys
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from src.utils.audit_logger import log_phi_access, log_application_event
from src.handlers.database_handler import MockDatabaseHandler
from src.routes.db_mock_data import setup_demo_data, patient_kits, call_logs, audit_logs, get_patient_by_kit_id

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize SocketIO
from flask_socketio import SocketIO
# Use threading mode instead of eventlet to avoid compatibility issues with Python 3.12
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Mock database for demo purposes
class MockDB:
    def __init__(self):
        self.patients = []
        self.kits = []
        self.call_logs = []
        self.audit_logs = []
        
    def get_kit_info(self, kit_id):
        kit = self.get_kit_by_id(kit_id)
        if kit:
            return {'kit_id': kit_id, 'mrn_hash': kit.get('mrn_hash')}
        return None
        
    def get_patient_by_mrn_hash(self, mrn_hash):
        for patient in self.patients:
            if patient.get('mrn_hash') == mrn_hash:
                return {'mrn': patient.get('mrn_hash'), 'phone_number': patient.get('phone')}
        return None
        
    def get_kit_by_id(self, kit_id):
        for kit in self.kits:
            if kit.get('kit_id') == kit_id:
                return kit
        return None

# Create mock database
mock_db = MockDB()

# Import mock data setup and admin routes
from routes import db_mock_data
from routes.admin_routes import admin_bp

# Initialize mock data for demo
db_mock_data.setup_demo_data()

# Override the mock database methods to use the db_mock_data module
# Use the functions that actually exist in db_mock_data
mock_db.get_kit_by_id = db_mock_data.get_kit_by_id
# Implement the required methods using the existing ones
def get_kit_info(kit_id):
    kit = db_mock_data.get_kit_by_id(kit_id)
    if kit:
        return {'kit_id': kit_id, 'mrn_hash': kit.get('mrn')}
    return None

def get_patient_by_mrn_hash(mrn_hash):
    patient = db_mock_data.get_patient_by_mrn(mrn_hash)
    if patient:
        return {'mrn': patient.get('mrn'), 'phone_number': patient.get('phone_number')}
    return None

# Assign the adapter functions
mock_db.get_kit_info = get_kit_info
mock_db.get_patient_by_mrn_hash = get_patient_by_mrn_hash

# Register the admin blueprint
app.register_blueprint(admin_bp, url_prefix='/admin')

# Configure Talisman for# Security headers with Flask-Talisman disabled for demo
# For a production environment, re-enable Talisman for proper HIPAA security

# Demo notice - this is a simplified version with mock data
app.config['DEMO_MODE'] = True

# Initialize mock database for demo version
mock_db = MockDB()

# Setup mock patient data
mock_db.patients = [
    {'id': 1, 'mrn_hash': 'MRN12345', 'name': 'John Doe', 'phone': '+1234567890', 'status': 'active'},
    {'id': 2, 'mrn_hash': 'MRN67890', 'name': 'Jane Smith', 'phone': '+1987654321', 'status': 'active'},
    {'id': 3, 'mrn_hash': 'MRN24680', 'name': 'Bob Johnson', 'phone': '+1122334455', 'status': 'inactive'}
]

# Setup mock kit data
mock_db.kits = [
    {'kit_id': 'KIT001', 'mrn_hash': 'MRN12345', 'status': 'deployed', 'last_check_in': datetime.now() - timedelta(days=2)},
    {'kit_id': 'KIT002', 'mrn_hash': 'MRN67890', 'status': 'deployed', 'last_check_in': datetime.now() - timedelta(hours=6)},
    {'kit_id': 'KIT003', 'mrn_hash': 'MRN24680', 'status': 'inactive', 'last_check_in': datetime.now() - timedelta(days=30)}
]

# Setup mock call logs
mock_db.call_logs = [
    {'id': 1, 'kit_id': 'KIT001', 'timestamp': datetime.now() - timedelta(days=5), 'duration_seconds': 125, 'status': 'completed', 'initiated_by': 'system'},
    {'id': 2, 'kit_id': 'KIT002', 'timestamp': datetime.now() - timedelta(days=2), 'duration_seconds': 90, 'status': 'completed', 'initiated_by': 'admin'},
    {'id': 3, 'kit_id': 'KIT001', 'timestamp': datetime.now() - timedelta(days=1), 'duration_seconds': 0, 'status': 'failed', 'initiated_by': 'system'}
]

# Conversation analysis disabled for demo mode
# In production, initialize the ConversationAnalyzer here

# Encryption disabled for demo mode
# In production, initialize encryption for secure PHI handling

# Initialize database handler for demo mode
from handlers.database_handler import get_database_handler
db_handler = get_database_handler()

# Set up audit logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
audit_logger = AuditLogger(log_dir=log_dir, db_handler=db_handler)

# Log application startup
audit_logger.log_event(
    event_type='system',
    action='APPLICATION_START',
    details={
        'version': '1.0.0',
        'environment': 'production' if not os.environ.get('DEBUG', 'False').lower() == 'true' else 'development'
    }
)

# Global variables to maintain state for each call
call_sessions = {}

class CallSession:
    def __init__(self, call_sid, call_id=None, mrn=None, patient_name=None, phone_number=None, reminder_type="fit_kit", kit_status=None):
        self.call_sid = call_sid
        self.call_id = call_id
        self.mrn = mrn
        self.patient_name = patient_name
        self.phone_number = phone_number
        self.reminder_type = reminder_type  # fit_kit, first_reminder, second_reminder
        self.kit_status = kit_status or {}
        self.transcript = ""
        self.conversation_history = []
        self.is_speaking = False
        self.socket = None
        
        # Build FIT kit specific system prompt
        self._build_system_prompt()
        
        # Add initial message to conversation history
        self.conversation_history.append({"role": "system", "content": self.system_prompt})
    
    def _build_system_prompt(self):
        """Build a specialized FIT kit reminder system prompt"""
        # Base HIPAA-compliant system prompt
        system_prompt_base = """
        You are a friendly healthcare assistant making a HIPAA-compliant call about a colorectal cancer screening FIT kit. 
        Be conversational, empathetic, and brief. Do not ask for or confirm identifying 
        information beyond what's needed for the FIT kit reminder.
        Answer basic questions but defer medical questions to their doctor.
        Wrap up the call politely when you have determined the status of their FIT kit.
        """
        
        # Add patient context if available
        patient_context = ""
        if self.patient_name:
            patient_context = f"You are calling {self.patient_name}. "
        
        # Reminder type instructions
        if self.reminder_type == "second_reminder":
            reminder_context = """This is a SECOND reminder call about their FIT kit. 
            Our records show they have not completed or returned their kit after the first reminder."""
        else:
            reminder_context = """This is a reminder call about their FIT kit (Fecal Immunochemical Test) 
            for colorectal cancer screening."""
        
        # FIT kit specific instructions
        fit_kit_instructions = """
        Your goal is to determine:
        1. Whether they have completed and mailed back their FIT kit. If yes, thank them and confirm their address to verify the kit will reach the right location.
        2. If they haven't completed it, ask if they still have the kit and if they need help understanding how to use it.
        3. If they need a new kit, offer to mail one to their address. Confirm their mailing address if they say yes.
        4. If they are having difficulties or questions, offer to schedule a callback with a healthcare provider.
        
        Remember to explain the importance of this screening for colorectal cancer detection. The FIT kit is a simple, at-home test that can detect hidden blood in the stool, which might be a sign of cancer or polyps.
        """
        
        # Kit status context if available
        kit_status_context = ""
        if self.kit_status:
            if self.kit_status.get('prior_letter'):
                kit_status_context += "Our records show we sent you a letter about completing this test. "
            
            if self.kit_status.get('reminder_sent'):
                kit_status_context += "We've called you previously about completing your FIT kit. "
            
            if self.kit_status.get('needs_new_kit'):
                kit_status_context += "Our records indicate you might need a new kit. "
        
        # Combine all prompt components
        self.system_prompt = f"{system_prompt_base}{patient_context}{reminder_context}{fit_kit_instructions}{kit_status_context}"
        
        # Add instructions for getting address info if needed
        if not self.kit_status.get('address_confirmed'):
            self.system_prompt += """
            Please confirm their mailing address if they need a new kit or haven't returned it yet. However, do not directly ask for their address unless they indicate they need a new kit or haven't returned it yet.
            """
        
        # Add callback scheduling instructions
        self.system_prompt += """
        If they request to speak with a healthcare provider, offer to schedule a callback. Ask what time would work best for them.
        """
        
        # Add closing instructions
        self.system_prompt += """
        End the call politely, thanking them for their time and reinforcing the importance of completing the FIT kit for their health.
        """
    
    def update_system_prompt(self, additional_context):
        """Update the system prompt with additional context"""
        self.system_prompt += f"\n\nAdditional context: {additional_context}"
        # Add updated system message
        self.conversation_history.append({"role": "system", "content": f"Additional context: {additional_context}"})
        return self.system_prompt

    def add_user_message(self, text):
        self.conversation_history.append({"role": "user", "content": text})
    
    def add_assistant_message(self, text):
        self.conversation_history.append({"role": "assistant", "content": text})


@app.route('/call/start', methods=['POST', 'GET'])
def start_call():
    """Simplified call start route for demo that simulates initiating a call to a patient
    
    For the demo version, this handles:
    1. GET requests with kit_id parameter from admin dashboard
    2. Simulates call initiation with mock data
    3. Logs events appropriately
    """
    kit_id = request.args.get('kit_id')
    initiated_by_admin = request.args.get('initiated_by_admin', 'false').lower() == 'true'
    access_reason = request.args.get('access_reason', 'Manual outreach call')
    
    if not kit_id:
        flash('Kit ID is required to initiate a call', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    # In the demo version, we don't actually make a call, we just simulate it
    try:
        # Look up the kit and patient
        kit_info = mock_db.get_kit_info(kit_id)
        if not kit_info:
            flash(f"Kit not found: {kit_id}", "danger")
            return redirect(url_for('admin.dashboard'))
            
        patient = mock_db.get_patient_by_mrn_hash(kit_info.get('mrn_hash'))
        if not patient:
            flash(f"Patient not found for kit: {kit_id}", "danger")
            return redirect(url_for('admin.dashboard'))
        
        # Log PHI access for HIPAA compliance
        if initiated_by_admin:
            audit_logger.log_event(
                event_type='phi_access',
                action='MANUAL_CALL_INITIATED',
                user_id=session.get('username', 'unknown'),
                details={
                    'kit_id': kit_id,
                    'reason': access_reason,
                    'accessed_fields': ['phone_number']
                }
            )
        
        # Create a mock call record
        call_sid = str(uuid.uuid4())
        call_log = {
            'call_sid': call_sid,
            'kit_id': kit_id,
            'mrn_hash': kit_info.get('mrn_hash'),
            'phone_number': patient.get('phone_number'),
            'start_time': datetime.now(),
            'end_time': datetime.now() + timedelta(minutes=2),  # Mock 2-minute call
            'duration_seconds': 120,  # Mock duration
            'status': 'completed',
            'initiated_by': 'admin' if initiated_by_admin else 'system'
        }
        
        # Save to our mock database
        mock_db.call_logs.append(call_log)
        
        # Also save to the database handler if available
        if db_handler:
            db_handler.save_call_log(call_log)
        
        # Show confirmation
        flash(f"Call to patient with kit ID {kit_id} was successful.", "success")
        
        # Render call completion template or redirect
        if initiated_by_admin:
            return render_template('admin/call_completed.html', 
                                  kit_id=kit_id, 
                                  call_sid=call_sid,
                                  duration=120)
        else:
            return jsonify({
                "success": True,
                "message": f"Call completed for kit ID {kit_id}",
                "call_sid": call_sid,
                "duration": 120
            })
            
    except Exception as e:
        logger.error(f"Error in call simulation: {str(e)}")
        flash(f"Error simulating call: {str(e)}", "danger")
        return redirect(url_for('admin.dashboard'))
    
    except Exception as e:
        logger.error(f"Error initiating FIT kit reminder call: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/call/connect', methods=['POST'])
def connect_call():
    """TwiML instructions for connecting the call to Media Streams"""
    call_sid = request.form.get('CallSid')
    
    if call_sid not in call_sessions:
        # This is an unexpected call, create a default session
        call_sessions[call_sid] = CallSession(
            call_sid=call_sid,
            phone_number=request.form.get('To', ''),
            reminder_type='general'
        )
    
    # Generate TwiML response
    response = VoiceResponse()
    
    # Connect to media streams for real-time audio processing
    connect = Connect()
    connect.stream(url=f"{request.url_root}stream")
    
    # Add initial greeting using GPT-generated text
    initial_greeting = generate_initial_greeting(call_sessions[call_sid])
    response.say(initial_greeting, voice="alice")
    
    # Add the Connect action with the Stream
    response.append(connect)
    
    return Response(str(response), mimetype='text/xml')


def generate_initial_greeting(session):
    """Generate an initial greeting using GPT"""
    reminder_type = session.reminder_type
    
    try:
        if reminder_type == "medication":
            prompt = "Generate a brief, friendly greeting for a medication reminder call. Introduce yourself as a healthcare assistant calling to check if they've taken their medication today."
        elif reminder_type == "fit_kit":
            prompt = "Generate a brief, friendly greeting for a call about a FIT kit (colorectal cancer screening). Introduce yourself as a healthcare assistant calling to check if they've completed and returned their kit."
        else:
            prompt = "Generate a brief, friendly greeting for a healthcare follow-up call. Introduce yourself as a healthcare assistant."
        
        # Add the prompt to the conversation history
        session.add_user_message(prompt)
        
        # Call GPT-4o
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=session.conversation_history,
            max_tokens=100
        )
        
        greeting_text = response.choices[0].message.content.strip()
        
        # Add the response to the conversation history
        session.add_assistant_message(greeting_text)
        
        return greeting_text
        
    except Exception as e:
        logger.error(f"Error generating greeting: {str(e)}")
        return "Hello, this is your healthcare assistant calling with a reminder. How are you doing today?"


@app.route('/call/status', methods=['POST'])
def call_status():
    """Handle Twilio status callback events for FIT kit reminder calls"""
    call_sid = request.form.get('CallSid')
    status = request.form.get('CallStatus')
    duration = request.form.get('CallDuration')
    
    logger.info(f"FIT kit reminder call {call_sid} status: {status}, duration: {duration}")
    
    try:
        # Process completed calls with conversation analysis
        if status == 'completed' and call_sid in call_sessions:
            session = call_sessions[call_sid]
            
            if session.conversation_history and len(session.conversation_history) > 1:
                # Step 1: Generate a summary of the conversation using GPT-4o
                try:
                    logger.info(f"Generating conversation summary for call {call_sid}")
                    summary = conversation_analyzer.generate_conversation_summary(session.conversation_history)
                    
                    # Log summary content
                    logger.info(f"Conversation summary: {json.dumps(summary)}")
                    
                    # Step 2: Extract FIT kit status and patient updates from summary
                    kit_status_updates = conversation_analyzer.extract_kit_status(summary)
                    patient_updates = conversation_analyzer.extract_patient_updates(summary)
                    
                    # Step 3: Update databases with conversation insights
                    if db_handler and session.mrn:
                        # Update both databases with conversation summary
                        db_handler.update_from_conversation_summary(session.mrn, summary)
                        
                        # Append the summary as a comment to the call record
                        outcome = f"Call completed. Summary: {summary.get('comments', '')}" 
                        if summary.get('kit_completed') == True:
                            outcome += " Patient has completed the FIT kit."
                        elif summary.get('needs_new_kit') == True:
                            outcome += " Patient needs a new kit."
                        if summary.get('callback_scheduled') == True:
                            outcome += f" Callback scheduled for {summary.get('callback_datetime')}."
                        
                        # Update call record with outcome
                        call_data = {
                            'call_sid': call_sid,
                            'mrn': session.mrn,
                            'status': status,
                            'end_time': time.time(),
                            'duration': int(duration) if duration else None,
                            'outcome': outcome
                        }
                        db_handler.save_call_log(call_data)
                        
                        # Audit log for conversation analysis
                        audit_logger.log_event(
                            event_type='access',
                            patient_id=session.mrn,
                            action='CONVERSATION_ANALYZED',
                            details={
                                'call_sid': call_sid,
                                'conversation_length': len(session.conversation_history),
                                'summary_generated': True,
                                'kit_status_updated': bool(kit_status_updates),
                                'patient_data_updated': bool(patient_updates)
                            }
                        )
                except Exception as e:
                    logger.error(f"Error processing conversation summary: {str(e)}")
        
        # Handle other call statuses (failed, busy, etc.)
        elif status in ['failed', 'busy', 'no-answer', 'canceled'] and call_sid in call_sessions:
            session = call_sessions[call_sid]
            
            if db_handler and session.mrn:
                # Update call record
                call_data = {
                    'call_sid': call_sid,
                    'mrn': session.mrn,
                    'status': status,
                    'end_time': time.time(),
                    'duration': int(duration) if duration else None,
                    'outcome': f"Call {status}. Patient not reached."
                }
                db_handler.save_call_log(call_data)
                
                # Update kit status to indicate patient was not reached
                kit_status_updates = {
                    'patient_reached': False
                }
                
                # If this is the second failed attempt, mark as unreachable
                if session.reminder_type == 'second_reminder':
                    kit_status_updates['unreachable_flag'] = True
                
                # Update kit status
                db_handler.update_kit_status(session.mrn, kit_status_updates)
                
                # Audit log for call completion
                audit_logger.log_call_event(
                    call_id=session.call_id,
                    patient_id=session.mrn,
                    event=f'FIT_KIT_CALL_{status.upper()}',
                    details={
                        'call_sid': call_sid,
                        'duration': duration,
                        'status': status,
                        'patient_reached': False
                    }
                )
        
        # Clean up session for all completed calls
        if status in ['completed', 'failed', 'busy', 'no-answer', 'canceled']:
            if call_sid in call_sessions:
                logger.info(f"Removing session for FIT kit call {call_sid}")
                del call_sessions[call_sid]
    
    except Exception as e:
        logger.error(f"Error handling FIT kit call status: {str(e)}")
    
    return '', 204


@app.route('/stream', methods=['POST'])
def stream():
    """Endpoint for Twilio media streams to connect"""
    return jsonify({
        "streams": [{
            "track": "inbound_track"
        }]
    })


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"New socket connection: {request.sid}")


@socketio.on('start')
def handle_start(data):
    """Handle the start of a new stream from Twilio"""
    call_sid = data.get('streamSid', '').split('.')[0]
    
    if call_sid in call_sessions:
        logger.info(f"Stream started for call {call_sid}")
        call_sessions[call_sid].socket = request.sid
        
        # Start Whisper connection for this call
        threading.Thread(target=start_whisper_stream, args=(call_sid,)).start()
    else:
        logger.warning(f"Received stream for unknown call: {call_sid}")


def start_whisper_stream(call_sid):
    """Start a Whisper stream for real-time transcription"""
    if call_sid not in call_sessions:
        return
    
    session = call_sessions[call_sid]
    
    try:
        # Initialize WhisperHandler if not already available in the session
        if not hasattr(session, 'whisper_handler'):
            session.whisper_handler = WhisperHandler()
            
            # Set up callback for transcription results
            def transcription_callback(transcript, is_final):
                if is_final and transcript.strip():
                    handle_transcription({
                        'call_sid': call_sid,
                        'transcript': transcript,
                        'is_final': is_final
                    })
            
            # Start transcription with callback
            session.whisper_handler.start_transcription(transcription_callback)
        
        logger.info(f"Whisper stream started for call {call_sid}")
    
    except Exception as e:
        logger.error(f"Error setting up Whisper stream: {str(e)}")
        AuditLogger().log_event(f"Error setting up Whisper stream: {str(e)}", "error")


@socketio.on('media')
def handle_media(data):
    """Handle incoming media from Twilio"""
    if 'event' in data and data['event'] == 'connected':
        logger.info(f"Media stream connected: {data}")
        return
    
    try:
        # Extract call SID from stream SID
        stream_sid = data.get('streamSid', '')
        call_sid = stream_sid.split('.')[0] if stream_sid else None
        
        if not call_sid or call_sid not in call_sessions:
            return
        
        session = call_sessions[call_sid]
        
        # Get audio data
        payload = data.get('media', {}).get('payload', '')
        if payload and hasattr(session, 'whisper_handler'):
            # Pass the base64 payload directly to Whisper handler
            session.whisper_handler.add_audio_data(payload)
            
            # Log receipt of audio for debugging
            logger.debug(f"Processed audio chunk from call {call_sid}")
    
    except Exception as e:
        logger.error(f"Error processing media: {str(e)}")
        AuditLogger().log_event(f"Error processing media: {str(e)}", "error")


@socketio.on('stop')
def handle_stop(data):
    """Handle the end of a stream from Twilio"""
    stream_sid = data.get('streamSid', '')
    call_sid = stream_sid.split('.')[0] if stream_sid else None
    
    if call_sid and call_sid in call_sessions:
        session = call_sessions[call_sid]
        logger.info(f"Stream ended for call {call_sid}")
        
        # Clean up Whisper resources
        if hasattr(session, 'whisper_handler'):
            final_transcript = session.whisper_handler.stop_transcription()
            logger.info(f"Final transcript for call {call_sid}: {final_transcript}")
            
            # Log final transcript to database if applicable
            try:
                db_handler = FitKitDBHandler()
                if session.mrn:
                    db_handler.save_transcript(session.mrn, final_transcript['transcript'])
            except Exception as e:
                logger.error(f"Error saving final transcript: {str(e)}")
                AuditLogger().log_event(f"Error saving transcript: {str(e)}", "error")


@socketio.on('transcription')
def handle_transcription(data):
    """Handle transcription results from Whisper"""
    call_sid = data.get('call_sid')
    transcript = data.get('transcript', '')
    is_final = data.get('is_final', False)
    
    if call_sid not in call_sessions:
        return
    
    session = call_sessions[call_sid]
    
    if is_final and transcript.strip():
        # Add to session transcript
        session.transcript += f"Patient: {transcript}\n"
        
        # Add to conversation history for GPT
        session.add_user_message(transcript)
        
        # Generate response using GPT
        generate_and_speak_response(session)


def generate_and_speak_response(session):
    """Generate a response using GPT and speak it using Coqui TTS"""
    try:
        # Call GPT-4o to generate a response
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=session.conversation_history,
            max_tokens=150,
            temperature=0.7
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Add response to conversation history
        session.add_assistant_message(response_text)
        session.transcript += f"Assistant: {response_text}\n"
        
        # Initialize Coqui TTS handler if not already available
        if not hasattr(session, 'tts_handler'):
            session.tts_handler = CoquiTTSHandler()
            # Wait for TTS model initialization
            if not session.tts_handler.wait_for_initialization():
                logger.warning(f"TTS model initialization timed out for call {session.call_sid}")
                raise Exception("TTS model initialization timed out")
        
        # Generate audio using Coqui TTS
        audio_base64 = session.tts_handler.text_to_speech(response_text, output_format="base64")
        
        if not audio_base64:
            raise Exception("Failed to generate speech audio")
        
        # Send audio to Twilio via WebSocket connection
        if session.socket:
            audio_message = {
                'event': 'media',
                'streamSid': f"{session.call_sid}.{uuid.uuid4()}",
                'media': {
                    'payload': audio_base64
                }
            }
            session.socket.emit('media', audio_message)
            
        # Log successful response generation
        logger.info(f"Generated response for call {session.call_sid}: {response_text}")
        
        # Log to audit trail for HIPAA compliance
        AuditLogger().log_event(
            f"Generated voice response for patient MRN {session.mrn}", 
            "conversation",
            metadata={'response_length': len(response_text)}
        )
    
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        AuditLogger().log_event(f"Error generating response: {str(e)}", "error")


@app.route('/stream/incoming', methods=['POST'])
def stream_incoming():
    """Endpoint to receive processed transcription from Whisper"""
    call_sid = request.json.get('call_sid')
    transcript = request.json.get('transcript', '')
    is_final = request.json.get('is_final', False)
    
    if call_sid and call_sid in call_sessions:
        socketio.emit('transcription', {
            'call_sid': call_sid,
            'transcript': transcript,
            'is_final': is_final
        })
    
    return '', 204


@app.route('/stream/response', methods=['POST'])
def stream_response():
    """Endpoint to send TTS response back to Twilio"""
    call_sid = request.json.get('call_sid')
    audio_data = request.json.get('audio_data')
    
    # This would process the audio data and send it back to Twilio
    # Implementation details would depend on how Twilio expects to receive the audio
    
    return '', 204


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "database": "connected" if db_handler else "not_configured",
            "twilio": "configured" if os.environ.get('TWILIO_ACCOUNT_SID') else "not_configured",
            "openai": "configured" if os.environ.get('OPENAI_API_KEY') else "not_configured",
        }
    }
    return jsonify(health_status)


@app.route('/admin/retention', methods=['GET', 'POST'])
def retention_policy():
    """Endpoint to view and manually trigger data retention policy"""
    # Check for API key authentication
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != os.environ.get('API_KEY'):
        return jsonify({"error": "Unauthorized"}), 401
    
    # Initialize retention policy
    from .utils.data_retention import DataRetentionPolicy
    retention_policy = DataRetentionPolicy(db_handler)
    
    if request.method == 'POST':
        # Execute retention policy manually
        try:
            results = retention_policy.execute_retention_policy()
            return jsonify({
                "status": "success",
                "message": "Retention policy executed",
                "results": results
            })
        except Exception as e:
            logger.error(f"Error executing retention policy: {str(e)}")
            return jsonify({"error": str(e)}), 500
    else:
        # Get retention policy status
        status = retention_policy.get_retention_status()
        return jsonify(status)


# Home route that redirects directly to patients list
@app.route('/')
def home():
    return redirect(url_for('admin.patient_list'))

# Demo route to go directly to patient list
@app.route('/demo-login')
def demo_login():
    # For demo purposes, automatically set up session
    from flask import session
    session['user_id'] = 'demo_user_id'
    session['username'] = 'demo_user'
    session['role'] = 'admin'
    session['last_activity'] = time.time()
    return redirect(url_for('admin.patient_list'))

# Admin blueprint is already registered at the top of the file

if __name__ == '__main__':
    print("Starting HIPAA-compliant FIT Kit Voice Assistant Demo...")
    
    # Set debug mode for development
    debug_mode = True
    
    # Run the app with socketio for WebSocket support
    socketio.run(app, host='127.0.0.1', port=int(os.environ.get('PORT', 5000)), debug=debug_mode)
