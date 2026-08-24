# Akai Community Hospital EHR & Informatics System
Clinical Informatics and Healthcare Systems portfolio demonstrating clinical workflows, HL7 interoperability, SQL database design, healthcare analytics, and EHR architecture through the Akai Community Hospital project. Each phase is connected to the classes I take in my Informatics program.


## 🎯 Overarching Project Mission

Akai Community Hospital EHR & Informatics System is an end-to-end Laboratory Information System (LIS) and EHR application architecture portfolio designed to answer two critical questions:
1. **Operational:** *How can a healthcare organization capture, secure, model, and analyze clinical data to improve patient care and executive decision-making?*
2. **Technical:** *How should healthcare data be collected, stored, secured, organized, and reported so the right people get the right information at the right time?*

---

## 🏗️ Entity Relationship Diagram

![AKAI Community Hospital ERD

## 🗺️ Curriculum Mapping & Architecture Deliverables

### Phase 1: HL7 Interface Engineering & Logic Validation (INFM 109 & SDEV 120)
* **Core Question:** *How are external laboratory instrument interfaces validated, and how is raw clinical data ingested securely into the EHR?*
* **What I'm Building:** End-to-end interface validation workflows simulating an EHR inbound engine. This includes parsing and validating inbound HL7 `ORM^O01` (Laboratory Order) and `ORU^R01` (Observation Result) messages. It focuses on validating Patient Identification `PID`, Common Order `ORC`, and Observation Request `OBR` segments to eliminate interface parsing faults before they hit clinical environments.

### Phase 2: Clinical Data Dictionary & Relational Architecture (DBMS 110 & DBMS 130)
* **Core Question:** *How are complex laboratory master files, specimen records, and clinical dictionaries structured to ensure data integrity?*
* **What I'm Building:** Normalized PostgreSQL database schema managing `Patients`, `Specimens`, `Orders`, and `LOINC_Map` `Lab_Results`, and audit logging for clinical data integrity.

### Phase 3: Security, Audit & Compliance (HIMT 104 & CSIA 105)
* **Core Question:** *How is patient data secured and audited for HIPAA compliance?*
* **What I'm Building:** Role-Based Access Control (RBAC) concepts and `audit_log` architecture designed to support HIPAA-aligned monitoring of Protected Health Information (PHI).

### Phase 4: Clinical Systems Reporting & Performance Analytics (INFM 219 & CPIN 269)
* **Core Question:** *How does data drive operational efficiency and patient outcomes?*
* **What I'm Building:** Power BI executive dashboards tracking laboratory turnaround times (TAT), specimen rejection rates, and critical flag alerts.

## 🚀 How to Run and Setup the LIS Database Locally

Follow these steps to clone this repository, construct the relational schema, and seed the database with synthetic clinical records.

### 1. Prerequisites
Ensure you have the following installed on your local machine:
* **Python 3.10+**
* **Git**
* **Database Engine:** PostgreSQL (with pgAdmin 4) OR Microsoft SQL Server (with Azure Data Studio / SSMS)

### 2. Clone the Repository
Open your terminal and run the following commands to pull the master files:
```bash
git clone https://github.com
cd Akai_Community_Hospital_EHR_Informatics_System
```

### 3. Install Dependencies
Install the required database drivers and the data generation library (`Faker`) using pip:
```bash
# For PostgreSQL environments (Mac/Linux/Windows local setups)
pip install psycopg2-binary faker

# For Microsoft SQL Server environments (School/Windows setups)
pip install pyodbc mssql faker
```

### 4. Build the Database Schema
Create a blank database named `akai_lis`, open your database tool's Query Window, and execute the corresponding architectural script:

* **If using PostgreSQL:** Execute the table definitions found in `database/schema.sql`.
* **If using Microsoft SQL Server:** Execute the table definitions found in `database/schema_sql_server.sql`.

### 5. Seed Synthetic Clinical Data
Run the correct automated Python engine that matches your database platform to populate empty tables with realistic patient demographics, lab orders, and results:

```bash
# For PostgreSQL (Native Mac setup)
python3 scripts/seed_database.py --patients 50 --max-orders 3

# For Microsoft SQL Server (School/Windows setup)
python3 scripts/seed_database_sql_server.py --patients 50 --max-orders 3
```
*Note: To wipe existing data and start a fresh simulation run, append the `--reset` flag to the command.*

### 6. Verify Analytical Outputs
Once seeded, open and run the pre-built reporting queries saved inside the `sql/` workspace directory to review clinical KPIs, processing turnaround times, and audit trails.

