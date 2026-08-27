-- Cleanup old indexes (safe to rerun)
DROP INDEX IF EXISTS idx_orders_order_datetime;
DROP INDEX IF EXISTS idx_specimens_collection_datetime;
DROP INDEX IF EXISTS idx_specimens_accession_number;
DROP INDEX IF EXISTS idx_results_result_datetime;
DROP INDEX IF EXISTS idx_results_loinc_code;
DROP INDEX IF EXISTS idx_results_flag;

-- Cleanup old tables (including legacy table name)
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS loinc_map CASCADE;
DROP TABLE IF EXISTS lab_results CASCADE;
DROP TABLE IF EXISTS specimens CASCADE;
DROP TABLE IF EXISTS accession_orders CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS patients CASCADE;

-- Patients
CREATE TABLE patients (
  patient_id SERIAL PRIMARY KEY,
  mrn VARCHAR(32) UNIQUE NOT NULL,
  first_name TEXT,
  last_name TEXT,
  dob DATE,
  sex CHAR(1) CHECK (sex IN ('M', 'F', 'U')),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Users (lab staff / clinicians)
CREATE TABLE users (
  user_id SERIAL PRIMARY KEY,
  username VARCHAR(64) UNIQUE NOT NULL,
  display_name TEXT,
  role VARCHAR(32) CHECK (role IN ('technician', 'clinician', 'admin')),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Orders (orders placed for lab tests)
CREATE TABLE orders (
  order_id SERIAL PRIMARY KEY,
  patient_id INT NOT NULL REFERENCES patients(patient_id),
  ordering_provider VARCHAR(128),
  order_datetime TIMESTAMPTZ NOT NULL,
  status VARCHAR(32) DEFAULT 'ordered' CHECK (status IN ('ordered', 'active', 'received', 'completed', 'canceled')),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Specimens collected for an order (one order may have multiple specimens)
CREATE TABLE specimens (
  specimen_id SERIAL PRIMARY KEY,
  order_id INT NOT NULL REFERENCES orders(order_id),
  accession_number VARCHAR(64) UNIQUE NOT NULL,
  specimen_type VARCHAR(64) NOT NULL, -- e.g., blood, urine
  collection_datetime TIMESTAMPTZ,
  received_datetime TIMESTAMPTZ,
  rejection_reason TEXT, -- NULL if not rejected
  created_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT chk_specimen_received_after_collection CHECK (received_datetime >= collection_datetime)
);

-- LOINC mapping / lookup master directory
CREATE TABLE loinc_map (
  loinc_code VARCHAR(32) PRIMARY KEY,
  test_name TEXT NOT NULL,
  units TEXT,
  ref_range TEXT
);

-- Lab results (Normalized: Holds transactional data linked to loinc_map)
CREATE TABLE lab_results (
  result_id SERIAL PRIMARY KEY,
  specimen_id INT NOT NULL REFERENCES specimens(specimen_id),
  
  -- Relational key linked directly to loinc_map(loinc_code)
  loinc_code VARCHAR(32) NOT NULL REFERENCES loinc_map(loinc_code), 
  
  status VARCHAR(32) DEFAULT 'final' CHECK (status IN ('preliminary', 'final', 'corrected', 'amended')),

  result_value TEXT,
  result_flag VARCHAR(16) CHECK (result_flag IN ('normal', 'abnormal', 'critical')),
  result_datetime TIMESTAMPTZ, -- when result finalized
  reported_datetime TIMESTAMPTZ, -- when result delivered/available
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Simple audit log for PHI access/actions
CREATE TABLE audit_log (
  audit_id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(user_id),
  object_type VARCHAR(64), -- patients/orders/specimens/results
  object_id INT,
  action VARCHAR(64), -- read/create/update/delete
  action_time TIMESTAMPTZ DEFAULT now(),
  detail JSONB
);

-- Indexes for optimized relational query performance
CREATE INDEX IF NOT EXISTS idx_orders_order_datetime
ON orders(order_datetime);
CREATE INDEX IF NOT EXISTS idx_specimens_collection_datetime
ON specimens(collection_datetime);
CREATE INDEX IF NOT EXISTS idx_specimens_accession_number
ON specimens(accession_number);
CREATE INDEX IF NOT EXISTS idx_results_result_datetime
ON lab_results(result_datetime);
CREATE INDEX IF NOT EXISTS idx_results_loinc_code
ON lab_results(loinc_code);
CREATE INDEX IF NOT EXISTS idx_results_flag
ON lab_results(result_flag);
