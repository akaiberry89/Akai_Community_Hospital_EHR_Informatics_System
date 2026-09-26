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

    # SEED DATA INGESTION ENGINE (MIGRATED FROM YOUR SEED TRACKS)
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

    # Ensure faker is imported at the top of this block
    from faker import Faker
    fake = Faker()

    # Generate 50 Patients using your original randomized logic parameters
    base_time = datetime.now() - timedelta(days=5)
    for idx in range(1, 51):
        # Patient Data - Restoring your authentic random name & details structure
        mrn = f"MRN{fake.unique.random_number(digits=8, fix_len=True)}"
        sex = random.choice(['M', 'F'])
        first = fake.first_name_male() if sex == 'M' else fake.first_name_female()
        last = fake.last_name()
        dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%Y-%m-%d")
        
        cursor.execute("INSERT INTO patients (mrn, first_name, last_name, dob, sex) VALUES (?, ?, ?, ?, ?);", 
                       (mrn, first, last, dob, sex))
        patient_id = cursor.lastrowid
        
        num_orders = random.randint(1, 2)
        for ord_idx in range(num_orders):
            prov = random.choice(providers)
            ord_status = random.choices(status_options, weights=status_weights, k=1)[0]
            ord_date = (base_time + timedelta(hours=random.randint(1, 48))).strftime("%Y-%m-%d %H:%M")
            
            cursor.execute("INSERT INTO orders (patient_id, ordering_provider, order_datetime, status) VALUES (?, ?, ?, ?);",
                           (patient_id, prov, ord_date, ord_status))
            order_id = cursor.lastrowid
            
            acc_num = f"ACC-{100000 + order_id}"
            spec_type = random.choice(specimen_types)
            rej = random.choice(rejection_reasons) if ord_status == 'canceled' else None
            
            cursor.execute("INSERT INTO specimens (order_id, accession_number, specimen_type, collection_datetime, rejection_reason) VALUES (?, ?, ?, ?, ?);",
                           (order_id, acc_num, spec_type, ord_date, rej))
            specimen_id = cursor.lastrowid
            
            if ord_status == 'completed':
                loinc = random.choice(loinc_data) [0]  # Get the LOINC code
                res_flag = random.choice(flags)
                res_val = f"{random.uniform(10.0, 150.0):.1f}" if res_flag == 'normal' else f"{random.uniform(151.0, 300.0):.1f}"
                
                cursor.execute("INSERT INTO lab_results (specimen_id, loinc_code, result_value, result_flag, result_datetime) VALUES (?, ?, ?, ?, ?);",
                               (specimen_id, loinc, res_val, res_flag, ord_date))
                
    conn.commit()
    return conn

# Connect to database instance
db_conn = init_portfolio_db()

# --- 3. DASHBOARD ARCHITECTURE ---
st.title("🏥 Akai Community Hospital EHR Informatics Platform")
st.subheader("Laboratory Information System (LIS) Enterprise Reporting Module")
st.markdown("---")

# Sidebar Configuration
st.sidebar.header("🎛️ Laboratory Controls")
st.sidebar.info("Use the main panel tabs to alternate between clinical registries and background security structures.")

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
tab_registry, tab_audit, tab_query = st.tabs([
    "📝 Clinical Order Registry", 
    "🔒 Immutable HIPAA Audit Logs",
    "💻 SQL Query Workspace"
])

with tab_registry:
    st.markdown("#### Active Clinical Patient Worklist")
    
    # Dynamic Search Filter Inputs
    search_col1, search_col2 = st.columns(2)
    search_name = search_col1.text_input("🔍 Search by Patient Last Name", "")
    search_acc = search_col2.text_input("🆔 Search by Accession Number (e.g., ACC-100003)", "")
    
    registry_query = """
        SELECT o.order_id, p.last_name || ', ' || p.first_name AS patient_name, 
               s.accession_number, s.specimen_type, lm.test_name, r.result_value, r.result_flag, o.status
        FROM orders o
        JOIN patients p ON o.patient_id = p.patient_id
        JOIN specimens s ON o.order_id = s.order_id
        LEFT JOIN lab_results r ON s.specimen_id = r.specimen_id
        LEFT JOIN loinc_map lm ON r.loinc_code = lm.loinc_code
        WHERE 1=1
    """
    
    query_params = []
    if search_name:
        registry_query += " AND p.last_name LIKE ?"
        query_params.append(f"%{search_name}%")
    if search_acc:
        registry_query += " AND s.accession_number = ?"
        query_params.append(search_acc.strip())
        
    reg_df = pd.read_sql_query(registry_query, db_conn, params=query_params)
    st.dataframe(
        reg_df,
        column_config={
            "order_id": st.column_config.NumberColumn("Order ID"),
            "patient_name": st.column_config.TextColumn("Patient Name"),
            "accession_number": st.column_config.TextColumn("Accession Number"),
            "specimen_type": st.column_config.TextColumn("Specimen Type"),
            "test_name": st.column_config.TextColumn("Lab Panel Ordered"),
            "result_value": st.column_config.TextColumn("Observed Value"),
            "result_flag": st.column_config.TextColumn("Severity Flag"),
            "status": st.column_config.TextColumn("Process Status")
        },
        use_container_width=True,
        hide_index=True
    )

with tab_audit:
    st.markdown("#### HIPAA Audit Trail System Log (`audit_log`)")
    st.warning("⚠️ **Compliance Assurance Tracker:** The entries below were generated automatically via native database trigger hooks when the synthetic pipeline executed inserts.")
    
    audit_df = pd.read_sql_query("SELECT audit_id, user_id, object_type, object_id, action, action_time FROM audit_log ORDER BY audit_id DESC", db_conn)
    st.dataframe(audit_df, use_container_width=True, hide_index=True)

with tab_query:
    st.markdown("### 💻 Custom SQL Query Console")
    st.markdown("Type any standard SQLite query below to test the live schema tracking layers and press Execute.")

    # 🗺️ Schema Data Map Cheat Sheet
    with st.expander("🗺️ View Database Schema Cheat Sheet"):
        st.code("""
        patients    (patient_id, mrn, first_name, last_name, dob, sex)
        orders      (order_id, patient_id, ordering_provider, status)
        specimens   (specimen_id, order_id, accession_number, specimen_type)
        lab_results (result_id, specimen_id, loinc_code, result_value, result_flag)
        audit_log   (audit_id, user_id, object_type, object_id, action)
        """)
    
    # Open Text Box Input Window
    user_sql = st.text_area("SQL Terminal Input Workspace", value="SELECT * FROM patients LIMIT 5;")
    
    if st.button("Execute Query ⚡"):
        # 1. Convert input to uppercase to catch 'drop', 'Drop', or 'DROP'
        sanitized_query = user_sql.upper()
        
        # 2. Establish a security boundary wall against dangerous data commands
        forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE"]
        
        # 3. Scan the query text for infractions
        contains_forbidden = any(keyword in sanitized_query for keyword in forbidden_keywords)
        
        if contains_forbidden:
            st.error("🚨 Security Exception: Data Modification Commands (DDL/DML updates) are disabled. This terminal is strictly configuration locked to READ-ONLY (SELECT) operations.")
        else:
            try:
                custom_df = pd.read_sql_query(user_sql, db_conn)
                st.success("Query executed successfully!")
                st.dataframe(custom_df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"SQL Syntax Error: {e}")