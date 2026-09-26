-- ============================================================================
-- AKAI COMMUNITY HOSPITAL EHR & INFORMATICS SYSTEM
-- MASTER DATABASE SCHEMA (MICROSOFT SQL SERVER VERSION)
--
-- AUTHOR: Theophilus K. Akai
-- PURPOSE: Direct line-by-line translation of the original PostgreSQL script.
--          Ensures exact logical parity with school systems.
-- ============================================================================

-- Clean up existing triggers if rerun
IF OBJECT_ID('trg_MS_Audit_Patients', 'TR') IS NOT NULL DROP TRIGGER trg_MS_Audit_Patients;
IF OBJECT_ID('trg_MS_Audit_Orders', 'TR') IS NOT NULL DROP TRIGGER trg_MS_Audit_Orders;
IF OBJECT_ID('trg_MS_Audit_Specimens', 'TR') IS NOT NULL DROP TRIGGER trg_MS_Audit_Specimens;
IF OBJECT_ID('trg_MS_Audit_Lab_Results', 'TR') IS NOT NULL DROP TRIGGER trg_MS_Audit_Lab_Results;
GO

-- Cleanup old indexes (safe to rerun)
-- Note: SQL Server handles index dropping via 'DROP INDEX IF EXISTS index_name ON table_name'
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_orders_order_datetime') DROP INDEX idx_orders_order_datetime ON orders;
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_orders_patient_id') DROP INDEX idx_orders_patient_id ON orders;
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_specimens_collection_datetime') DROP INDEX idx_specimens_collection_datetime ON specimens;
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_specimens_accession_number') DROP INDEX idx_specimens_accession_number ON specimens;
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_specimens_order_id') DROP INDEX idx_specimens_order_id ON specimens;
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_results_result_datetime') DROP INDEX idx_results_result_datetime ON lab_results;
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_results_loinc_code') DROP INDEX idx_results_loinc_code ON lab_results;
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_results_flag') DROP INDEX idx_results_flag ON lab_results;

-- Cleanup old tables (including legacy table name)
-- Note: SQL Server does not support CASCADE on DROP TABLE. 
-- Dropping tables in reverse-relationship order safely eliminates foreign key blockages.
IF OBJECT_ID('dbo.audit_log', 'U') IS NOT NULL DROP TABLE dbo.audit_log;
IF OBJECT_ID('dbo.lab_results', 'U') IS NOT NULL DROP TABLE dbo.lab_results;
IF OBJECT_ID('dbo.specimens', 'U') IS NOT NULL DROP TABLE dbo.specimens;
IF OBJECT_ID('dbo.accession_orders', 'U') IS NOT NULL DROP TABLE dbo.accession_orders; -- Legacy table handling
IF OBJECT_ID('dbo.orders', 'U') IS NOT NULL DROP TABLE dbo.orders;
IF OBJECT_ID('dbo.users', 'U') IS NOT NULL DROP TABLE dbo.users;
IF OBJECT_ID('dbo.patients', 'U') IS NOT NULL DROP TABLE dbo.patients;
IF OBJECT_ID('dbo.loinc_map', 'U') IS NOT NULL DROP TABLE dbo.loinc_map;

-- Patients
CREATE TABLE patients (
    patient_id INT IDENTITY(1,1) PRIMARY KEY,
    mrn VARCHAR(32) UNIQUE NOT NULL,
    first_name VARCHAR(MAX), -- Replaced TEXT with VARCHAR(MAX)
    last_name VARCHAR(MAX),  -- Replaced TEXT with VARCHAR(MAX)
    dob DATE,
    sex CHAR(1) CHECK (sex IN ('M', 'F', 'U')),
    created_at DATETIMEOFFSET DEFAULT SYSDATETIMEOFFSET() -- Replaced TIMESTAMPTZ and now()
);

-- Users (lab staff / clinicians)
CREATE TABLE users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    display_name VARCHAR(MAX), -- Replaced TEXT with VARCHAR(MAX)
    role VARCHAR(32) CHECK (role IN ('technician', 'clinician', 'admin')),
    created_at DATETIMEOFFSET DEFAULT SYSDATETIMEOFFSET()
);

-- Orders (orders placed for lab tests)
CREATE TABLE orders (
    order_id INT IDENTITY(1,1) PRIMARY KEY,
    patient_id INT NOT NULL REFERENCES patients(patient_id),
    ordering_provider VARCHAR(128),
    order_datetime DATETIMEOFFSET NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ordered' CHECK (status IN ('ordered', 'active', 'received', 'completed', 'canceled')),
    created_at DATETIMEOFFSET DEFAULT SYSDATETIMEOFFSET()
);

-- Specimens collected for an order (one order may have multiple specimens)
CREATE TABLE specimens (
    specimen_id INT IDENTITY(1,1) PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(order_id),
    accession_number VARCHAR(64) UNIQUE NOT NULL,
    specimen_type VARCHAR(64) NOT NULL, -- e.g., blood, urine
    collection_datetime DATETIMEOFFSET,
    received_datetime DATETIMEOFFSET,
    accessioned_datetime DATETIMEOFFSET,
    rejection_reason VARCHAR(MAX), -- Replaced TEXT with VARCHAR(MAX)
    created_at DATETIMEOFFSET DEFAULT SYSDATETIMEOFFSET(),
    
CONSTRAINT chk_specimen_received_after_collection CHECK (
    received_datetime IS NULL
    OR collection_datetime IS NULL
    OR received_datetime >= collection_datetime
),

CONSTRAINT chk_accessioned_after_received CHECK (
    accessioned_datetime IS NULL
    OR received_datetime IS NULL
    OR accessioned_datetime >= received_datetime
)
);

-- LOINC mapping / lookup master directory
CREATE TABLE loinc_map (
    loinc_code VARCHAR(32) PRIMARY KEY,
    test_name VARCHAR(255) NOT NULL, -- Specified length constraint for compatibility
    units VARCHAR(64),
    ref_range VARCHAR(64)
);

-- Lab results (Normalized: Holds transactional data linked to loinc_map)
CREATE TABLE lab_results (
    result_id INT IDENTITY(1,1) PRIMARY KEY,
    specimen_id INT NOT NULL REFERENCES specimens(specimen_id),
    loinc_code VARCHAR(32) NOT NULL REFERENCES loinc_map(loinc_code),
    status VARCHAR(32) NOT NULL DEFAULT 'final' CHECK (status IN ('preliminary', 'final', 'corrected', 'amended')),
    result_value VARCHAR(MAX), -- Replaced TEXT with VARCHAR(MAX)
    result_flag VARCHAR(16) CHECK (result_flag IN ('normal', 'abnormal', 'critical')),
    result_datetime DATETIMEOFFSET,
    reported_datetime DATETIMEOFFSET,
    created_at DATETIMEOFFSET DEFAULT SYSDATETIMEOFFSET(),

CONSTRAINT chk_reported_after_result CHECK (
    reported_datetime IS NULL
    OR result_datetime IS NULL
    OR reported_datetime >= result_datetime
)    
);

-- Simple audit log for PHI access/actions
CREATE TABLE audit_log (
    audit_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    object_type VARCHAR(64),
    object_id INT,
    action VARCHAR(64),
    action_time DATETIMEOFFSET DEFAULT SYSDATETIMEOFFSET(),
    detail NVARCHAR(MAX) -- Replaced JSONB with NVARCHAR(MAX) for SQL Server JSON string tracking
);

-- Indexes for optimized relational query performance
-- Note: SQL Server handles 'IF NOT EXISTS' options through standard creation scripts
CREATE INDEX idx_orders_order_datetime ON orders(order_datetime);
CREATE INDEX idx_orders_patient_id ON orders(patient_id);
CREATE INDEX idx_specimens_collection_datetime ON specimens(collection_datetime);
CREATE INDEX idx_specimens_accession_number ON specimens(accession_number);
CREATE INDEX idx_specimens_order_id ON specimens(order_id);
CREATE INDEX idx_results_result_datetime ON lab_results(result_datetime);
CREATE INDEX idx_results_loinc_code ON lab_results(loinc_code);
CREATE INDEX idx_results_flag ON lab_results(result_flag);

-- AUTOMATED HIPAA COMPLIANCE AUDIT TRIGGERS
CREATE TRIGGER trg_MS_Audit_Patients ON patients AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO audit_log (user_id, object_type, object_id, action, detail)
    SELECT 1, 'patients', i.patient_id, 'CREATE', (SELECT i.mrn, i.first_name, i.last_name, i.dob, i.sex FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i;
END;
GO

CREATE TRIGGER trg_MS_Audit_Orders ON orders AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO audit_log (user_id, object_type, object_id, action, detail)
    SELECT 1, 'orders', i.order_id, 'CREATE', (SELECT i.patient_id, i.ordering_provider, i.status FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i;
END;
GO

CREATE TRIGGER trg_MS_Audit_Specimens ON specimens AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO audit_log (user_id, object_type, object_id, action, detail)
    SELECT 1, 'specimens', i.specimen_id, 'CREATE', (SELECT i.order_id, i.accession_number, i.specimen_type, i.rejection_reason FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i;
END;
GO

CREATE TRIGGER trg_MS_Audit_Lab_Results ON lab_results AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO audit_log (user_id, object_type, object_id, action, detail)
    SELECT 1, 'lab_results', i.result_id, 'CREATE', (SELECT i.specimen_id, i.loinc_code, i.result_value, i.result_flag FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i;
END;
GO