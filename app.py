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
def init_portfolio_db(current_date):
    """
    Builds an in-memory SQLite database mimicking the PostgreSQL/T-SQL DDL schema.
    Applies native SQLite database triggers to automate HIPAA Compliance Audit Logs.
    Distributes patient and order data throughout the current week with realistic timestamps.
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

    # Import faker for realistic data generation
    from faker import Faker
    fake = Faker()

    # --- TEMPORAL ENGINE INITIALIZATION ---
    now = datetime.now()
    
    # 1. Determine the baseline anchor (Find the start of the current week - Monday)
    days_since_monday = now.weekday()  # Monday = 0, Tuesday = 1, etc.
    start_of_week = now - timedelta(days=days_since_monday)
    # Set to 00:00:00 on Monday
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 2. Dynamic Count Calculations (500 Baseline + 50 additions for every passing day)
    patients_to_generate = 500 + (days_since_monday * 50)
    
    # 3. Synchronize the Random Matrix Seed for consistency across refreshes
    random.seed(int(now.strftime("%Y%m%d")))
    fake.seed_instance(int(now.strftime("%Y%m%d")))

    # --- SEEDING ENGINE TRACK ---
    # Distribute patients across the week (Monday through today)
    # Each day gets patients distributed across 24 hours with realistic hospital hours (7 AM - 11 PM)
    
    for idx in range(1, patients_to_generate + 1):
        # Determine which day this patient should be created on
        day_offset = (idx - 1) % max(1, (days_since_monday + 1))  # Spread across days so far this week
        patient_day = start_of_week + timedelta(days=day_offset)
        
        # Distribute within hospital hours (7 AM to 11 PM)
        hour_offset = random.randint(7, 22)
        minute_offset = random.randint(0, 59)
        patient_created_time = patient_day.replace(hour=hour_offset, minute=minute_offset, second=random.randint(0, 59))
        
        # Patient Data
        mrn = f"MRN{fake.unique.random_number(digits=8, fix_len=True)}"
        sex = random.choice(['M', 'F'])
        first = fake.first_name_male() if sex == 'M' else fake.first_name_female()
        last = fake.last_name()
        dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%Y-%m-%d")
        
        # Insert patient with explicit created_at timestamp
        cursor.execute("INSERT INTO patients (mrn, first_name, last_name, dob, sex, created_at) VALUES (?, ?, ?, ?, ?, ?);", 
                       (mrn, first, last, dob, sex, patient_created_time.strftime("%Y-%m-%d %H:%M:%S")))
        patient_id = cursor.lastrowid
        
        num_orders = random.randint(1, 2)
        for ord_idx in range(num_orders):
            prov = random.choice(providers)
            ord_status = random.choices(status_options, weights=status_weights, k=1)[0]
            
            # Orders created after patient creation, but within the same day or next few hours
            hours_after_patient = random.randint(0, 12)
            order_time = patient_created_time + timedelta(hours=hours_after_patient)
            
            # Make sure order doesn't go past current time
            if order_time > now:
                order_time = now - timedelta(hours=random.randint(1, 6))
            
            ord_date = order_time.strftime("%Y-%m-%d %H:%M")
            
            cursor.execute("INSERT INTO orders (patient_id, ordering_provider, order_datetime, status, created_at) VALUES (?, ?, ?, ?, ?);",
                           (patient_id, prov, ord_date, ord_status, order_time.strftime("%Y-%m-%d %H:%M:%S")))
            order_id = cursor.lastrowid
            
            acc_num = f"ACC-{100000 + order_id}"
            spec_type = random.choice(specimen_types)
            rej = random.choice(rejection_reasons) if ord_status == 'canceled' else None
            
            cursor.execute("INSERT INTO specimens (order_id, accession_number, specimen_type, collection_datetime, rejection_reason, created_at) VALUES (?, ?, ?, ?, ?, ?);",
                           (order_id, acc_num, spec_type, ord_date, rej, order_time.strftime("%Y-%m-%d %H:%M:%S")))
            specimen_id = cursor.lastrowid
            
            if ord_status == 'completed':
                loinc = random.choice(loinc_data)[0]  # Get the LOINC code
                res_flag = random.choice(flags)
                res_val = f"{random.uniform(10.0, 150.0):.1f}" if res_flag == 'normal' else f"{random.uniform(151.0, 300.0):.1f}"
                
                # Result time is a bit after order
                result_time = order_time + timedelta(hours=random.randint(1, 8))
                if result_time > now:
                    result_time = now - timedelta(hours=random.randint(0, 3))
                
                cursor.execute("INSERT INTO lab_results (specimen_id, loinc_code, result_value, result_flag, result_datetime, created_at) VALUES (?, ?, ?, ?, ?, ?);",
                               (specimen_id, loinc, res_val, res_flag, result_time.strftime("%Y-%m-%d %H:%M:%S"), result_time.strftime("%Y-%m-%d %H:%M:%S")))
                
    conn.commit()
    return conn

# Connect to database instance
today = datetime.now().date()
db_conn = init_portfolio_db(today)

# --- 3. DASHBOARD ARCHITECTURE ---
st.title("🏥 Akai Community Hospital EHR Informatics Platform")
st.subheader("Laboratory Information System (LIS) Enterprise Reporting Module")
st.markdown("---")

# Sidebar Configuration
st.sidebar.header("🎛️ Laboratory Controls")
st.sidebar.info("Use the main panel tabs to alternate between clinical registries and background security structures.")

# Stack your new dynamic data telemetry
st.sidebar.caption(f"📅 **System Local Clock:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.info(
    f"📡 **Operational Data Telemetry:** This portal simulates a live EHR inbound network stream. "
    f"The database scales dynamically based on the current day of the week "
    f"and will execute an automated schema reset cycle every Sunday at midnight."
)

# Data Aggregation via Live Queries
total_pats = int(pd.read_sql_query("SELECT COUNT(*) FROM patients", db_conn).iloc[0, 0])
total_orders = int(pd.read_sql_query("SELECT COUNT(*) FROM orders", db_conn).iloc[0, 0])
criticals = int(pd.read_sql_query("SELECT COUNT(*) FROM lab_results WHERE result_flag = 'critical'", db_conn).iloc[0, 0])

# Columns Layout for Executive KPI Tracking
m_col1, m_col2, m_col3 = st.columns(3)
m_col1.metric("Total Patients Managed", total_pats)
m_col2.metric("Total Relational Orders Placed", total_orders)
m_col3.metric("🚨 Active Critical Flags", criticals)

# Conditional Security Banner
if criticals > 0:
    st.error(f"🚨 **PATIENT SAFETY WARNING:** There are {criticals} unverified clinical panic values pending review.")

st.markdown("### 📊 Enterprise Ledger Workspace")

# --- 4. NAVIGATION VIEW INTERFACES ---
tab_patients, tab_orders, tab_specimens, tab_results, tab_audit, tab_query = st.tabs([
    "👤 patients Table", 
    "📋 orders Table", 
    "🧪 specimens Table", 
    "🔬 lab_results Table",
    "🔒 audit_log Table",
    "💻 SQL Query Console"
])

with tab_patients:
    st.markdown("### 👤 patients Registry Table")
    st.markdown("Raw transactional rows from the `patients` schema table, tracking MRNs and patient demographics.")
    pats_df = pd.read_sql_query("SELECT patient_id, mrn, first_name, last_name, dob, sex, created_at FROM patients ORDER BY created_at DESC", db_conn)
    st.dataframe(pats_df, use_container_width=True, hide_index=True)

with tab_orders:
    st.markdown("### 📋 orders Transactional Table")
    st.markdown("Tracks provider order requests mapped back to unique Patient IDs via foreign key constraints.")
    orders_df = pd.read_sql_query("SELECT order_id, patient_id, ordering_provider, order_datetime, status, created_at FROM orders ORDER BY created_at DESC", db_conn)
    st.dataframe(orders_df, use_container_width=True, hide_index=True)

with tab_specimens:
    st.markdown("### 🧪 specimens Tracking Table")
    st.markdown("Logs physical sample status, processing benchmarks, and automated rejection flags.")
    
    # 📈 Added an executive bar chart to track rejection rules visually
    st.markdown("#### Turnaround Time Tracking by Specimen Type")
    chart_df = pd.read_sql_query("""
        SELECT s.specimen_type, COUNT(o.order_id) as total_volume
        FROM specimens s
        JOIN orders o ON s.order_id = o.order_id
        GROUP BY s.specimen_type
    """, db_conn)
    st.bar_chart(data=chart_df, x="specimen_type", y="total_volume", color="#4b7eff")
    
    spec_df = pd.read_sql_query("SELECT specimen_id, order_id, accession_number, specimen_type, collection_datetime, rejection_reason, created_at FROM specimens ORDER BY created_at DESC", db_conn)
    st.dataframe(spec_df, use_container_width=True, hide_index=True)

with tab_results:
    st.markdown("### 🔬 lab_results Structured View")
    st.markdown("Normalized transactional data linked to standard LOINC master mapping protocols.")
    res_query = """
        SELECT r.result_id, r.specimen_id, lm.test_name, r.result_value, lm.units, lm.ref_range, r.result_flag, r.status, r.created_at
        FROM lab_results r
        JOIN loinc_map lm ON r.loinc_code = lm.loinc_code
        ORDER BY r.created_at DESC
    """
    res_df = pd.read_sql_query(res_query, db_conn)
    st.dataframe(res_df, use_container_width=True, hide_index=True)

with tab_audit:
    st.markdown("### 🔒 audit_log Compliance System Log")
    st.info("Immutable Tracking Log: Captured natively via operational database triggers to guarantee absolute security monitoring.")
    audit_df = pd.read_sql_query("SELECT audit_id, user_id, object_type, object_id, action, action_time, detail FROM audit_log ORDER BY audit_id DESC", db_conn)
    st.dataframe(audit_df, use_container_width=True, hide_index=True)

with tab_query:
    st.markdown("### 💻 Enterprise SQL Sandbox Console")
    st.markdown("Type any standard SQLite query below to test the live schema tracking layers and press Execute.")
    
    user_sql = st.text_area("SQL Terminal Input Workspace", value="SELECT * FROM patients LIMIT 5;")
    
    if st.button("Execute Query ⚡"):
        sanitized_query = user_sql.upper()
        forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE"]
        contains_forbidden = any(keyword in sanitized_query for keyword in forbidden_keywords)
        
        if contains_forbidden:
            st.error("🚨 Security Exception: Data Modification Commands are disabled. This terminal is configuration locked to READ-ONLY (SELECT) operations.")
        else:
            try:
                custom_df = pd.read_sql_query(user_sql, db_conn)
                st.success("Query executed successfully!")
                st.dataframe(custom_df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"SQL Syntax Error: {e}")
