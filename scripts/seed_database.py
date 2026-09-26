#!/usr/bin/env python3
"""
Simple seed script for Akai_Community_Hospital_EHR_Informatics_System
- Matches the provided CREATE TABLE schema
- Uses rejection_reason in specimens
- Inserts lightweight audit_log entries for important actions
- Keeps result_value as TEXT to match your schema
- Supports command-line arguments for patients, orders, and database resets

Run examples:
  python3 scripts/seed_database.py --patients 10 --max-orders 1
  python3 scripts/seed_database.py --patients 100 --max-orders 5 --reset
"""
import os
import logging
import random
import json
import argparse
from datetime import timedelta, timezone

import psycopg2
import psycopg2.extras as extras
from faker import Faker

fake = Faker()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# DB config via environment
DB_NAME = os.getenv("DB_NAME", "akai_lis")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YOUR_PASSWORD_HERE")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")


def make_aware(dt):
    """Attach UTC tzinfo if naive. Keep as-is if already tz-aware."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def main():
    # --- Step 1: Set up Argparse command-line arguments ---
    parser = argparse.ArgumentParser(
        description="Synthetic Data Generator for AKAI Community Hospital LIS"
    )
    parser.add_argument(
        "--patients", 
        type=int, 
        default=50, 
        help="Number of patient records to generate (default: 50)"
    )
    parser.add_argument(
        "--max-orders", 
        type=int, 
        default=3, 
        help="Maximum number of lab orders to generate per patient (default: 3)"
    )
    parser.add_argument(
        "--reset", 
        action="store_true", 
        help="Wipe all existing database records before seeding new data"
    )
    args = parser.parse_args()

    conn = None
    cur = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        cur = conn.cursor()
        logging.info("Connected to %s", DB_NAME)

        # --- Step 2: Conditional Truncate (Reordered safely for Foreign Key constraints) ---
        if args.reset:
            cur.execute(
                "TRUNCATE audit_log, lab_results, specimens, orders, users, patients, loinc_map RESTART IDENTITY CASCADE;"
            )
            logging.info("RESET FLAG DETECTED: Truncated all tables and reset identity sequences.")
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
                "INSERT INTO loinc_map (loinc_code, test_name, units, ref_range) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;",
                (code, name, units, ref),
            )
        logging.info("Seeded loinc_map (%d rows)", len(loinc_data))

        # 2) Seed users
        user_ids = []
        if args.reset:
            # Enforce core system profile first so it automatically takes User ID 1
            cur.execute(
                "INSERT INTO users (username, display_name, role) VALUES (%s, %s, %s) RETURNING user_id;",
                ('sys_hl7_interface', 'HL7 Core Inbound Interface', 'admin'),
            )
            sys_uid = cur.fetchone()[0]
            user_ids.append(sys_uid)
            cur.execute(
                "INSERT INTO audit_log (user_id, object_type, object_id, action, detail) VALUES (%s, %s, %s, %s, %s);",
                (sys_uid, 'users', sys_uid, 'create', extras.Json({'username': 'sys_hl7_interface', 'role': 'admin'})),
            )
            
            roles = ['technician', 'clinician', 'admin']
            for _ in range(5):
                username = f"user_{fake.user_name()}"
                display_name = fake.name()
                role = random.choice(roles)
                cur.execute(
                    "INSERT INTO users (username, display_name, role) VALUES (%s, %s, %s) RETURNING user_id;",
                    (username, display_name, role),
                )
                uid = cur.fetchone()[0]
                user_ids.append(uid)
                cur.execute(
                    "INSERT INTO audit_log (user_id, object_type, object_id, action, detail) VALUES (%s, %s, %s, %s, %s);",
                    (uid, 'users', uid, 'create', extras.Json({'username': username, 'role': role})),
                )
            logging.info("Seeded users (%d)", len(user_ids))
        else:
            # Append mode safety: Ensure system user account exists at ID 1 if missing
            cur.execute("SELECT user_id FROM users WHERE user_id = 1;")
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO users (username, display_name, role) VALUES (%s, %s, %s);",
                    ('sys_hl7_interface', 'HL7 Core Inbound Interface', 'admin'),
                )
            
            # Fetch existing users from the database if not resetting
            cur.execute("SELECT user_id FROM users;")
            user_ids = [row[0] for row in cur.fetchall()]
            logging.info("Loaded existing users for append mode (%d users available)", len(user_ids))

        # 3) Seed patients
        patient_ids = []
        for _ in range(args.patients):
            mrn = f"MRN{fake.unique.random_number(digits=8, fix_len=True)}"
            sex = random.choice(['M', 'F'])
            first_name = fake.first_name_male() if sex == 'M' else fake.first_name_female()
            last_name = fake.last_name()
            dob = fake.date_of_birth(minimum_age=18, maximum_age=90)

            # Change 1: Added ON CONFLICT clause
            cur.execute(
                "INSERT INTO patients (mrn, first_name, last_name, dob, sex) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (mrn) DO NOTHING RETURNING patient_id;",
                (mrn, first_name, last_name, dob, sex),
            )
            result = cur.fetchone()
            
            # Change 3: Wrapped in an IF block to check for skipped duplicates
            if result is not None:
                pid = result[0]
                patient_ids.append(pid)
            else:
                skipped_patients += 1
            
            # Change 2: The manual cur.execute for audit_log has been completely removed from here!

        if skipped_patients > 0:
            logging.info("Idempotent Pattern: Safely bypassed %d pre-existing patient rows.", skipped_patients)
        logging.info("Seeded patients (%d)", len(patient_ids))

        # 4) Seed orders, specimens, lab_results (Controlled by --max-orders)
        flags = ['normal', 'normal', 'normal', 'abnormal', 'critical']
        rejection_reasons = [
            'Hemolyzed',
            'Quantity Not Sufficient (QNS)',
            'Unlabeled Specimen',
            'Incorrect Container Type',
            'Clotted Specimen'
        ]

        status_options = [
            'completed',
            'ordered',
            'received',
            'active',
            'canceled',
        ]

        status_weights = [70, 15, 8, 5, 2]  # Weighted probabilities for status selection
        

        total_orders_created = 0
        for p_id in patient_ids:
            num_orders = random.randint(1, max(1, args.max_orders))
            for _ in range(num_orders):
                total_orders_created += 1
                
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
                    "INSERT INTO orders (patient_id, ordering_provider, order_datetime, status) VALUES (%s, %s, %s, %s) RETURNING order_id;",
                    (p_id, provider, order_time, order_status),
                )
                order_id = cur.fetchone()[0]
                
                num_specimens = random.choices(
                    [1, 2, 3],
                    weights=[70, 20, 10],
                    k=1
                ) [0]

                for _ in range(num_specimens):


                    coll_time = make_aware(order_time + timedelta(minutes=random.randint(15, 60)))
                    rec_time = make_aware(coll_time + timedelta(minutes=random.randint(30, 90)))
                    accessioned_time = make_aware(rec_time + timedelta(minutes=random.randint(1, 10)))

                    # Specimen arrives in lab and gets accessioned
                    acc_num = f"ACC{fake.unique.random_number(digits=10, fix_len=True)}"

                    # Choose a randomized specimen type with weights (blood more common)
                    specimen_type = random.choices(
                        ['blood', 'urine', 'serum', 'plasma'],
                        weights=[70, 20, 7, 3],
                        k=1
                    )[0]

                    is_rejected = random.random() < 0.10
                    rejection_reason = random.choice(rejection_reasons) if is_rejected else None

                    # Fixed: properly pass SQL and params as separate arguments and use randomized specimen_type
                    cur.execute(
                        "INSERT INTO specimens (order_id, accession_number, specimen_type, collection_datetime, received_datetime, accessioned_datetime, rejection_reason) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING specimen_id;",
                        (order_id, acc_num, specimen_type, coll_time, rec_time, accessioned_time, rejection_reason)
                    )
                    specimen_id = cur.fetchone()[0]

                    if not is_rejected:
                        loinc = random.choice(loinc_data)
                        flag = random.choice(flags)

                        # Rule-based flag logic for Glucose vs. random for other tests
                        if loinc[0] == '2345-7':
                            numeric_value = random.randint(65, 180)
                            result_value = str(numeric_value)

                            if numeric_value > 170:
                                flag = 'critical'
                            elif numeric_value > 140:
                                flag = 'abnormal'
                            else:
                                flag = 'normal'
                        else:
                            result_value = str(round(random.uniform(3.5, 18.0), 1))
                            flag = random.choice(['normal', 'normal', 'abnormal'])

                        result_time = make_aware(accessioned_time + timedelta(minutes=random.randint(45, 120)))

                        result_status = ('preliminary' if order_status == 'received' else 'final')

                        # Updated: Normalized SQL insert matches your new schema
                        cur.execute(
                            """INSERT INTO lab_results (
                                specimen_id, loinc_code, status, result_value, 
                                result_flag, result_datetime, reported_datetime
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING result_id;""",
                            (specimen_id, loinc[0], result_status, result_value, flag, result_time, result_time),
                        )
                        result_id = cur.fetchone()[0]

        logging.info("Seeded orders, specimens, and lab_results (%d orders total)", total_orders_created)

        # Finalize
        conn.commit()
        logging.info("Seeding complete. Committed changes.")

    except Exception as e:
        if conn:
            conn.rollback()
        logging.exception("Error while seeding database: %s", e)
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        try:
            fake.unique.clear()
        except Exception:
            pass


if __name__ == "__main__":
    main()
