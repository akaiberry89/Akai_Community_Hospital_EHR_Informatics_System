import streamlit as st
import sqlite3
import pandas as pd
import random
from datetime import datetime, timedelta

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Akai Community Hospital - LIS Portal",
    page_icon="🏥",
    layout="wide"
)

# --- 2. SELF-CONTAINED DATABASE INITIALIZATION ---
@st.cache_resource
def init_portfolio_db():
    """
    Builds an in-memory SQLite database mimicking the PostgreSQL/T-SQL DDL schema.
    Applies native SQLite database triggers to automate HIPAA Compliance Audit Logs.
    
    Temporal behavior:
    - Database resets every Sunday at midnight (UTC)
    - 500 baseline patients, +50 per day of the week
    - All timestamps are historical (never in the future)
    - Realistic progression: patient registration → order → specimen → results
    """
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    cursor = conn.cursor()
    
    # Enable foreign keys inside the database engine
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # TABLES DEFINITION (DDL ACCORDING TO REPOSITORY ARCHITECTURE)
    cursor.execute('''
        CREATE TABLE patients (
          patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
          mrn TEXT UNIQUE NOT NULL,
          first_name TEXT,
          last_name TEXT,
          dob TEXT,
          sex TEXT CHECK (sex IN ('M', 'F', 'U')),
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE users (
          user_id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT UNIQUE NOT NULL,
          display_name TEXT,
          role TEXT CHECK (role IN ('technician', 'clinician', 'admin')),
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE orders (
          order_id INTEGER PRIMARY KEY AUTOINCREMENT,
          patient_id INT NOT NULL REFERENCES patients(patient_id),
          ordering_provider TEXT,
          order_datetime TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'ordered' CHECK (status IN ('ordered', 'active', 'received', 'completed', 'canceled')),
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE specimens (
          specimen_id INTEGER PRIMARY KEY AUTOINCREMENT,
          order_id INT NOT NULL REFERENCES orders(order_id),
          accession_number TEXT UNIQUE NOT NULL,
          specimen_type TEXT NOT NULL,
          collection_datetime TEXT,
          received_datetime TEXT,
          accessioned_datetime TEXT,
          rejection_reason TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE loinc_map (
          loinc_code TEXT PRIMARY KEY,
          test_name TEXT NOT NULL,
          units TEXT,
          ref_range TEXT
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE lab_results (
          result_id INTEGER PRIMARY KEY AUTOINCREMENT,
          specimen_id INT NOT NULL REFERENCES specimens(specimen_id),
          loinc_code TEXT NOT NULL REFERENCES loinc_map(loinc_code), 
          status TEXT NOT NULL DEFAULT 'final' CHECK (status IN ('preliminary', 'final', 'corrected', 'amended')),
          result_value TEXT,
          result_flag TEXT CHECK (result_flag IN ('normal', 'abnormal', 'critical')),
          result_datetime TEXT,
          reported_datetime TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE audit_log (
          audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INT REFERENCES users(user_id),
          object_type TEXT,
          object_id INT,
          action TEXT,
          action_time TEXT DEFAULT CURRENT_TIMESTAMP,
          detail TEXT
        );
    ''')

    # NATIVE SQLITE TRIGGERS (REPLICATING YOUR POSTGRESQL PL/pgSQL LOGIC)
    cursor.execute('''
        CREATE TRIGGER trg_audit_insert_patients AFTER INSERT ON patients
        BEGIN
            INSERT INTO audit_log (user_id, object_type, object_id, action, detail)
            VALUES (1, 'patients', NEW.patient_id, 'CREATE', '{"event_description": "Record automatically provisioned via system process"}');
        END;
    ''')
    
    cursor.execute('''
        CREATE TRIGGER trg_audit_insert_orders AFTER INSERT ON orders
        BEGIN
            INSERT INTO audit_log (user_id, object_type, object_id, action, detail)
            VALUES (1, 'orders', NEW.order_id, 'CREATE', '{"event_description": "Record automatically provisioned via system process"}');
        END;
    ''')
    
    cursor.execute('''
        CREATE TRIGGER trg_audit_insert_specimens AFTER INSERT ON specimens
        BEGIN
            INSERT INTO audit_log (user_id, object_type, object_id, action, detail)
            VALUES (1, 'specimens', NEW.specimen_id, 'CREATE', '{"event_description": "Record automatically provisioned via system process"}');
        END;
    ''')
    
    cursor.execute('''
        CREATE TRIGGER trg_audit_insert_results AFTER INSERT ON lab_results
        BEGIN
            INSERT INTO audit_log (user_id, object_type, object_id, action, detail)
            VALUES (1, 'lab_results', NEW.result_id, 'CREATE', '{"event_description": "Record automatically provisioned via system process"}');
        END;
    ''')

    # SEED DATA INGESTION ENGINE
    loinc_data = [
        ('2345-7', 'Glucose [Mass/volume] in Serum or Plasma', 'mg/dL', '70-99'),
        ('4544-3', 'Hematocrit [Volume Fraction] of Blood', '%', '37.0-51.0'),
        ('718-7', 'Hemoglobin [Mass/volume] in Blood', 'g/dL', '12.0-17.5'),
        ('6690-2', 'Leukocytes [#/volume] in Blood', '10*3/uL', '4.5-11.0'),
        ('17861-6', 'Calcium [Mass/volume] in Serum or Plasma', 'mg/dL', '8.5-10.2')
    ]
    cursor.executemany("INSERT OR IGNORE INTO loinc_map VALUES (?, ?, ?, ?);", loinc_data)

    cursor.execute("INSERT INTO users (username, display_name, role) VALUES ('sys_hl7_interface', 'HL7 Core Inbound Interface', 'admin');")
    
    providers = ["Dr. Evelyn Martinez, MD", "Dr. Marcus Vance, MD", "Dr. Sarah Lin, DO"]
    specimen_types = ["Whole Blood", "Serum", "Plasma", "Random Urine"]
    flags = ['normal', 'normal', 'normal', 'abnormal', 'critical']
    rejection_reasons = ['Hemolyzed', 'Quantity Not Sufficient (QNS)', 'Unlabeled Specimen', 'Incorrect Container Type']
    status_options = ['completed', 'ordered', 'received', 'active', 'canceled']
    status_weights = [70, 15, 8, 5, 2]

    from faker import Faker
    fake = Faker()

    # --- TEMPORAL ENGINE: RESET EVERY SUNDAY ---
    now = datetime.now()
    days_since_monday = now.weekday()  # Monday=0, Sunday=6
    start_of_week = now - timedelta(days=days_since_monday)
    
    # Dynamic patient count: 500 baseline + 50 per day
    patients_to_generate = 500 + (days_since_monday * 50)
    
    # Seed for reproducibility
    random.seed(int(now.strftime("%Y%m%d")))
    fake.seed_instance(int(now.strftime("%Y%m%d")))

    # Generate patients distributed across the week
        # Generate patients distributed across the week
    for idx in range(1, patients_to_generate + 1):
        day_offset = random.randint(0, days_since_monday)
        hour_offset = random.randint(6, 22)
        minute_offset = random.randint(0, 59)
        
        patient_created_time = start_of_week + timedelta(
            days=day_offset, hours=hour_offset, minutes=minute_offset
        )
        
        if patient_created_time > now:
            patient_created_time = now - timedelta(hours=random.randint(2, 8))
        
        patient_created_str = patient_created_time.strftime("%Y-%m-%d %H:%M:%S")
        
        mrn = f"MRN{fake.unique.random_number(digits=8, fix_len=True)}"
        sex = random.choice(['M', 'F'])
        first = fake.first_name_male() if sex == 'M' else fake.first_name_female()
        last = fake.last_name()
        dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%Y-%m-%d")
        
        cursor.execute(
            "INSERT INTO patients (mrn, first_name, last_name, dob, sex, created_at) VALUES (?, ?, ?, ?, ?, ?);",
            (mrn, first, last, dob, sex, patient_created_str)
        )
        
        # 25% chance this patient has an associated order sequence to simulate realistic hospital workflows
        if random.random() < 0.25:
            prov = random.choice(providers)
            order_time = patient_created_time + timedelta(minutes=random.randint(15, 120))
            order_time_str = order_time.strftime("%Y-%m-%d %H:%M:%S")
            status = random.choices(status_options, weights=status_weights, k=1)[0]
            
            cursor.execute(
                "INSERT INTO orders (patient_id, ordering_provider, order_datetime, status, created_at) VALUES (?, ?, ?, ?, ?);",
                (idx, prov, order_time_str, status, order_time_str)
            )
            
            if status in ['received', 'active', 'completed']:
                acc = f"ACC-{fake.unique.random_number(digits=6, fix_len=True)}"
                spec_type = random.choice(specimen_types)
                coll_time = order_time + timedelta(minutes=random.randint(5, 30))
                rec_time = coll_time + timedelta(minutes=random.randint(20, 60))
                
                cursor.execute(
                    "INSERT INTO specimens (order_id, accession_number, specimen_type, collection_datetime, received_datetime, status) VALUES (?, ?, ?, ?, ?, ?);",
                    (idx, acc, spec_type, coll_time.strftime("%Y-%m-%d %H:%M:%S"), rec_time.strftime("%Y-%m-%d %H:%M:%S"), status)
                )
                
                if status == 'completed':
                    loinc = random.choice(loinc_data)[0]
                    res_val = str(random.randint(75, 115)) if loinc == '2345-7' else f"{random.uniform(12.0, 16.5):.1f}"
                    flag = random.choice(['normal', 'normal', 'abnormal'])
                    res_time = rec_time + timedelta(minutes=random.randint(15, 45))
                    
                    cursor.execute(
                        "INSERT INTO lab_results (specimen_id, loinc_code, status, result_value, result_flag, result_datetime) VALUES (?, ?, ?, ?, ?, ?);",
                        (idx, loinc, 'final', res_val, flag, res_time.strftime("%Y-%m-%d %H:%M:%S"))
                    )

    conn.commit()
    return conn

# --- 3. RE-INITIALIZE DATABASE FRAMEWORK ---
now = datetime.now()
days_since_monday = now.weekday()
conn = init_portfolio_db(now)
cursor = conn.cursor()

# --- 4. RENDER DASHBOARD TABS ---
# Appending your custom HL7 tab directly into the horizontal alignment array
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "👤 patients Table", 
    "📋 orders Table", 
    "🧪 specimens Table", 
    "📊 lab_results Table", 
    "📟 HL7 Interface Monitor"
])

with tab1:
    st.subheader("Patients Ledger (Read-Only)")
    st.dataframe(pd.read_sql_query("SELECT * FROM patients ORDER BY created_at DESC", conn), use_container_width=True)

with tab2:
    st.subheader("Orders Log")
    st.dataframe(pd.read_sql_query("SELECT * FROM orders", conn), use_container_width=True)

with tab3:
    st.subheader("Specimens Ledger")
    st.dataframe(pd.read_sql_query("SELECT * FROM specimens", conn), use_container_width=True)

with tab4:
    st.subheader("Verified Results")
    st.dataframe(pd.read_sql_query("SELECT * FROM lab_results", conn), use_container_width=True)

# 🚀 YOUR NEW INTERACTIVE HL7 TAB SCRIPT 🚀
with tab5:
    st.header("📟 HL7 Interface Dashboard & Monitor")
    st.markdown("Simulating streaming clinical transactions aligned with our database temporal framework.")
    
    # 1. DYNAMIC METRICS: Connected directly to your current patient load
    total_messages = 150 + (days_since_monday * 225)
    faults = int(total_messages * 0.005) + 1
    successes = total_messages - faults
    
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Weekly Transaction Volume", f"{total_messages:,}", f"+225/day")
    m_col2.metric("Successful Ingestions (99.5%)", f"{successes:,}")
    m_col3.metric("Validation Exceptions", f"{faults}", delta="-0.5% rate", delta_color="inverse")
    
    # 2. RUN REAL-TIME DATA QUERY TO EXTRACT PATIENT FOR THE SANDBOX
    try:
        last_pt = cursor.execute("SELECT mrn, first_name, last_name FROM patients ORDER BY patient_id DESC LIMIT 1").fetchone()
        sim_mrn = last_pt[0]
        sim_last = last_pt[2]
        sim_first = last_pt[1]
    except Exception:
        sim_mrn = "MRN12976560"
        sim_last = "Zimmerman"
        sim_first = "Amber"

    # 3. INTERACTIVE PARSER SANDBOX
    st.subheader("🧪 Inbound Message Parser Sandbox")
    st.caption("ℹ️ **Analyst Guide:** HL7 v2 records separate blocks into **Segments** (lines) and values into **Fields** using vertical pipes (`|`). The patient identification is located in the `PID` segment, where the patient name lives specifically at field index `PID-5` by tracking empty field positions.")
    
    raw_sample = (
        f"MSH|^~\\&|LAB_SYSTEM|ACME_HOSP|LIS|RECEIVING|{now.strftime('%Y%m%d%H%M%S')}||ORU^R01|MSG123456|P|2.5|\n"
        f"PID|1||{sim_mrn}||{sim_last}^{sim_first}|SMITH|19800515|M||\n"
        f"OBR|1|ORD789|ACC-100123|2345-7^GLUCOSE||{now.strftime('%Y%m%d%H%M%S')}|||||||||||||||F||\n"
        f"OBX|1|NM|2345-7^GLUCOSE^LN||95|mg/dL|70-99|N|||F"
    )
    
    user_input = st.text_area("Inbound Transaction String Container (Editable)", raw_sample, height=180)
    
    if st.button("Parse & Map to Database Parameters"):
        lines = user_input.split('\n')
        parsed_data = []
        
        for line in lines:
            if line.startswith('PID'):
                f = line.split('|')
                if len(f) > 3: parsed_data.append({"HL7 Position": "PID-3", "Field Name": "Patient Identifier (MRN)", "Extracted Value": f[3], "Data Type": "CX (Composite ID)", "Database Target": "patients.mrn"})
                if len(f) > 5: parsed_data.append({"HL7 Position": "PID-5", "Field Name": "Patient Full Name", "Extracted Value": f[5].replace('^', ', '), "Data Type": "XPN (Person Name)", "Database Target": "patients.last_name / first_name"})
            if line.startswith('OBR'):
                f = line.split('|')
                if len(f) > 3: parsed_data.append({"HL7 Position": "OBR-3", "Field Name": "LIS Accession ID", "Extracted Value": f[3], "Data Type": "EI (Entity Identifier)", "Database Target": "specimens.accession_number"})
            if line.startswith('OBX'):
                f = line.split('|')
                if len(f) > 3: parsed_data.append({"HL7 Position": "OBX-3", "Field Name": "Observation Identifier", "Extracted Value": f[3], "Data Type": "CE (Coded Element)", "Database Target": "lab_results.loinc_code"})
                if len(f) > 5: parsed_data.append({"HL7 Position": "OBX-5", "Field Name": "Observation Result Value", "Extracted Value": f[5], "Data Type": "ST (String / Numeric)", "Database Target": "lab_results.result_value"})
        
        st.success("🎉 Transaction string broken down successfully! Visual parsing schema populated below.")
        st.dataframe(pd.DataFrame(parsed_data), use_container_width=True)

    # 4. HISTORICAL PROCESSING EXCEPTIONS LOG
    st.subheader("⚠️ Interface Error Processing Logs")
    err_data = [
        {"Timestamp": "2026-09-30 14:23:45", "Segment": "PID-3", "Severity": "Critical", "Clinical Description": "Inbound message rejected: Missing required Patient Identifier (MRN) placeholder. Cannot map to patients.mrn."},
        {"Timestamp": "2026-09-30 13:15:22", "Segment": "OBR-4", "Severity": "High", "Clinical Description": "Validation fault: LOINC code \"9999-9\" is not in reference master. Accession ACC-100089 held pending reconciliation."},
        {"Timestamp": "2026-09-30 12:07:38", "Segment": "OBX-5", "Severity": "Medium", "Clinical Description": "Result value truncated: Expected numeric value, received text string \"Pending\". Stored as preliminary result."}
    ]
    st.dataframe(pd.DataFrame(err_data), use_container_width=True)
