-- Consolidated Database Schema
-- Combines essential elements from both public and private databases

-- Patient and Kit Information Table
CREATE TABLE IF NOT EXISTS patient_kits (
    id SERIAL PRIMARY KEY,
    kit_id VARCHAR(50) UNIQUE,
    mrn VARCHAR(50) UNIQUE,
    patient_name VARCHAR(200),
    date_of_birth DATE,
    phone_number VARCHAR(15),
    email VARCHAR(100),
    preferred_language VARCHAR(50) DEFAULT 'English',
    kit_status VARCHAR(20) NOT NULL, -- 'sent', 'delivered', 'completed', 'processed', 'expired'
    date_sent DATE,
    date_completed DATE,
    needs_followup BOOLEAN DEFAULT FALSE,
    comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Call logs table
CREATE TABLE IF NOT EXISTS call_logs (
    id SERIAL PRIMARY KEY,
    call_sid VARCHAR(50) UNIQUE,
    kit_id VARCHAR(50) REFERENCES patient_kits(kit_id),
    mrn VARCHAR(50) REFERENCES patient_kits(mrn),
    call_status VARCHAR(20),
    call_duration INT,  -- in seconds
    call_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    conversation_summary TEXT,
    outcome VARCHAR(50),  -- 'kit_completed', 'will_complete', 'needs_new_kit', etc.
    follow_up_required BOOLEAN DEFAULT FALSE
);

-- Audit logs for HIPAA compliance
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(36) UNIQUE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(100),
    action VARCHAR(50),
    resource_type VARCHAR(50),
    resource_id VARCHAR(50),
    detail JSONB,
    ip_address VARCHAR(45)
);

-- Indexes for improved query performance
CREATE INDEX IF NOT EXISTS idx_patient_kits_kit_id ON patient_kits(kit_id);
CREATE INDEX IF NOT EXISTS idx_patient_kits_mrn ON patient_kits(mrn);
CREATE INDEX IF NOT EXISTS idx_call_logs_kit_id ON call_logs(kit_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_call_sid ON call_logs(call_sid);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
