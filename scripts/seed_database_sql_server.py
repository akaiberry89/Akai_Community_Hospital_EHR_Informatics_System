#!/usr/bin/env python3
"""
Synthetic Data Generator for AKAI Community Hospital LIS (MS SQL Server Version)
- Matches the schema_sql_server.sql architecture
- Uses pyodbc to connect natively to Microsoft SQL Server environments
- Keeps result_value as VARCHAR/TEXT to match your schema
- Supports command-line arguments for patients, orders, and database resets
"""

import os
import logging
import random
import json
import argparse
from datetime import timedelta, timezone
import pyodbc
from faker import Faker

fake = Faker()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# DB config via environment variables
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_NAME = os.getenv("DB_NAME", "akai_lis")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YOUR_PASSWORD_HERE")
DB_DRIVER = os.getenv("DB_DRIVER", "{ODBC Driver 17 for SQL Server}")

def make_aware(dt):
    """Attach UTC tzinfo if naive. Keep as-is if already tz-aware."""
    if dt is None: return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def main():
    # --- Step 1: Set up Argparse command-line arguments ---
    parser = argparse.ArgumentParser(
        description="Synthetic Data Generator for AKAI Community Hospital LIS (MS SQL Server)"
    )
    parser.add_argument(
        "--patients", type=int, default=50, help="Number of patient records to generate (default: 50)"
    )
    parser.add_argument(
        "--max-orders", type=int, default=3, help="Maximum number of lab orders to generate per patient (default: 3)"
    )
    parser.add_argument(
        "--reset", action="store_true", help="Wipe all existing database records before seeding new data"
    )
    args = parser.parse_args()

    conn = None
    cur = None

    try:
        conn_str = f"SERVER={DB_SERVER};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD};DRIVER={DB_DRIVER};"
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()
        logging.info("Connected to MS SQL Server: %s", DB_NAME)

        # --- Step 2: Conditional Truncate (SQL Server strict deletion order) ---
        if args.reset:
            # SQL Server requires manual sequential deletion since CASCADE is absent on drops
            cur.execute("DELETE FROM audit_log;")
            cur.execute("DELETE FROM lab_results;")
            cur.execute("DELETE FROM specimens;")
            cur.execute("DELETE FROM orders;")
            cur.execute("DELETE FROM users;")
            cur.execute("DELETE FROM patients;")
            cur.execute("DELETE FROM loinc_map;")
            
            # Reset identity counting sequences back to 0
            tables = ['patients', 'users', 'orders', 'specimens', 'lab_results', 'audit_log']
            for table in tables:
                cur.execute(f"DBCC CHECKIDENT ('{table}', RESEED, 0);")
            logging.info("RESET FLAG DETECTED: Cleared all tables and reset identity sequences.")
        else:
            logging.info("APPEND MODE: Appending new records to existing database tables.")

        # 1) Seed loinc_map
        loinc_data = [
            ('2345-7', 'Glucose [Mass/volume] in Serum or Plasma', 'mg/dL', '70-99'),
            ('4544-3', 'Hematocrit [Volume Fraction] of Blood', '%', '37.0-51.0'),
            ('718-7', 'Hemoglobin [Mass/volume] in Blood', 'g/dL', '12.0-17.5'),
            ('6690-2', 'Leukocytes [#/volume] in Blood', '10*3/uL', '4.5-11.0'),
            ('17861-6', 'Calcium [Mass/volume] in Serum or Plasma', 'mg/dL', '8.5-10.2')
        ]
        for code, name, units, ref in loinc_data:
            cur.execute(
                """
                IF NOT EXISTS (SELECT 1 FROM loinc_map WHERE loinc_code = ?)
                INSERT INTO loinc_map (loinc_code, test_name, units, ref_range) VALUES (?, ?, ?, ?);
                """,
                (code, code, name, units, ref),
            )
        logging.info("Seeded loinc_map (%d rows verified)", len(loinc_data))

        # 2) Seed users
        user_ids = []
        if args.reset:
            roles = ['technician', 'clinician', 'admin']
            for _ in range(5):
                username = f"user_{fake.user_name()}"
                display_name = fake.name()
                role = random.choice(roles)
                
                cur.execute(
                    "INSERT INTO users (username, display_name, role) OUTPUT inserted.user_id VALUES (?, ?, ?);",
                    (username, display_name, role),
                )
                uid = cur.fetchone()[0]
                user_ids.append(uid)
                
                audit_detail = json.dumps({'username': username, 'role': role})
                cur.execute(
                    "INSERT INTO audit_log (user_id, object_type, object_id, action, detail) VALUES (?, ?, ?, ?, ?);",
                    (uid, 'users', uid, 'create', audit_detail),
                )
            logging.info("Seeded users (%d)", len(user_ids))
        else:
            cur.execute("SELECT user_id FROM users;")
            user_ids = [row[0] for row in cur.fetchall()]
            
            if not user_ids:
                cur.execute(
                    "INSERT INTO users (username, display_name, role) OUTPUT inserted.user_id VALUES (?, ?, ?);",
                    ("sys_admin", "System Admin", "admin"),
                )
                user_ids.append(cur.fetchone()[0])
            logging.info("Loaded existing users for append mode (%d users available)", len(user_ids))

        # 3) Seed patients
        patient_ids = []
        for _ in range(args.patients):
            mrn = f"MRN{fake.unique.random_number(digits=8, fix_len=True)}"
            sex = random.choice(['M', 'F'])
            first_name = fake.first_name_male() if sex == 'M' else fake.first_name_female()
            last_name = fake.last_name()
            dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime('%Y-%m-%d')
            
            cur.execute(
                "INSERT INTO patients (mrn, first_name, last_name, dob, sex) OUTPUT inserted.patient_id VALUES (?, ?, ?, ?, ?);",
                (mrn, first_name, last_name, dob, sex),
            )
            pid = cur.fetchone()[0]
            patient_ids.append(pid)
            
            audit_detail = json.dumps({'mrn': mrn, 'name': f"{first_name} {last_name}"})
            cur.execute(
                "INSERT INTO audit_log (user_id, object_type, object_id, action, detail) VALUES (?, ?, ?, ?, ?);",
                (random.choice(user_ids), 'patients', pid, 'create', audit_detail),
            )
        logging.info("Seeded patients (%d)", len(patient_ids))

        # 4) Seed orders, specimens, lab_results (Controlled by --max-orders)
        rejection_reasons = [
            'Hemolyzed', 'Quantity Not Sufficient (QNS)', 'Unlabeled Specimen', 'Incorrect Container Type', 'Clotted Specimen'
        ]

        status_options = [
            'completed',
            'ordered',
            'received',
            'active',
            'canceled',
]

        status_weights = [70, 15, 8, 5, 2]

        total_orders_created = 0
        
        for p_id in patient_ids:
            num_orders = random.randint(1, max(1, args.max_orders))
            for _ in range(num_orders):
                total_orders_created += 1
                acc_num = f"ACC{fake.unique.random_number(digits=10, fix_len=True)}"
                
                # Simulate unsigned or incomplete orders.
                # Approximately 10% of orders will not yet have
                # an ordering provider assigned.
                provider = (
                    None
                    if random.random() < 0.10
                    else f"Dr. {fake.last_name()}"
                )
                order_time = make_aware(fake.date_time_between(start_date='-30d', end_date='now'))

                order_status = random.choices(status_options, weights=status_weights, k=1)[0]
                
                cur.execute(
                    "INSERT INTO orders (patient_id, ordering_provider, order_datetime, status) OUTPUT inserted.order_id VALUES (?, ?, ?, ?);",
                    (p_id, provider, order_time, order_status),
                )
                order_id = cur.fetchone()[0]
                
                audit_detail = json.dumps({'patient_id': p_id, 'ordering_provider': provider})
                cur.execute(
                    "INSERT INTO audit_log (user_id, object_type, object_id, action, detail) VALUES (?, ?, ?, ?, ?);",
                    (random.choice(user_ids), 'orders', order_id, 'create', audit_detail),
                )
                
                coll_time = make_aware(order_time + timedelta(minutes=random.randint(15, 60)))
                rec_time = make_aware(coll_time + timedelta(minutes=random.randint(30, 90)))
                is_rejected = random.random() < 0.10
                rejection_reason = random.choice(rejection_reasons) if is_rejected else None
                
                # Choose a randomized specimen type with weights (blood more common)
                specimen_type = random.choices(
                    ['blood', 'urine', 'serum', 'plasma'],
                    weights=[70, 20, 7, 3],
                    k=1
                )[0]
                
                cur.execute(
                    """
                    INSERT INTO specimens (order_id, accession_number, specimen_type, collection_datetime, received_datetime, rejection_reason) 
                    OUTPUT inserted.specimen_id VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (order_id, acc_num, specimen_type, coll_time, rec_time, rejection_reason),
                )
                specimen_id = cur.fetchone()[0]
                
                audit_detail = json.dumps({'order_id': order_id, 'accession_number': acc_num, 'rejection_reason': rejection_reason})
                cur.execute(
                    "INSERT INTO audit_log (user_id, object_type, object_id, action, detail) VALUES (?, ?, ?, ?, ?);",
                    (random.choice(user_ids), 'specimens', specimen_id, 'create', audit_detail),
                )
                
                if not is_rejected:
                    loinc = random.choice(loinc_data)
                    
                    if loinc[0] == '2345-7':

                        # Rule-based flag logic for Glucose vs. random for other tests             
                        numeric_value = random.randint(65,180)
                        result_value = str(numeric_value)

                        if numeric_value > 170:
                            flag = 'critical'
                        elif numeric_value > 140:
                            flag = 'abnormal'
                        else:
                            flag = 'normal'

                    else:

                        result_value = str(round(random.uniform(3.5, 18.0), 1))

                        flag = random.choice(
                            ['normal', 'normal', 'normal', 'abnormal'], 
                        )                   
                       
                    result_time = make_aware(rec_time + timedelta(minutes=random.randint(45, 120)))

                    result_status = ('preliminary' if order_status == 'received' else 'final')
                    
                    cur.execute(
                        """
                        INSERT INTO lab_results (specimen_id, loinc_code, status, result_value, result_flag, result_datetime, reported_datetime) 
                        OUTPUT inserted.result_id VALUES (?, ?, ?, ?, ?, ?, ?);
                        """,
                        (specimen_id, loinc[0], result_value, result_status, flag, result_status, result_time, result_time),
                    )
                    result_id = cur.fetchone()[0]
                    
                    audit_detail = json.dumps({'specimen_id': specimen_id, 'loinc_code': loinc[0], 'value': result_value})
                    cur.execute(
                        "INSERT INTO audit_log (user_id, object_type, object_id, action, detail) VALUES (?, ?, ?, ?, ?);",
                        (random.choice(user_ids), 'lab_results', result_id, 'create', audit_detail),
                    )
                    
        logging.info("Seeded orders, specimens, and lab_results (%d orders total)", total_orders_created)
        conn.commit()
        logging.info("Seeding complete. Committed changes.")

    except Exception as e:
        if conn: conn.rollback()
        logging.exception("Error while seeding database: %s", e)
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()
        try:
            fake.unique.clear()
        except Exception:
            pass

if __name__ == "__main__":
    main()
