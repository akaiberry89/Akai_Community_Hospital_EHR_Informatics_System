# AKAI Community Hospital LIS
## Future Enhancements

I have over 10 years of professional laboratory experience.

As I continue building this project, there will be times when real-world laboratory workflows and experiences find their way into the design.

Some enhancements may blur the line between an academic project and the reality of how laboratory systems operate.

Bear with me as I learn how to translate what I've seen in the laboratory into healthcare informatics solutions.

### Audit Logging & Reporting

#### Audit Data Integrity

- [x] Ensure seed data assigns `user_id` to all audit records
- [ ] Evaluate enforcing `audit_log.user_id` as NOT NULL in db schema
- [ ] Add dedicated `system` user account for automated processes
- [ ] Ensure all audit events are attributable to either:
  - Human User
  - System Process
- [ ] Review audit trail design against healthcare compliance best practices

#### Audit Reports

- [ ] Create report showing actions by user
- [ ] Create report showing actions by object type
- [ ] Create report showing actions by date/time
- [ ] Create report showing most active users

### Database Enhancements

- [x] Investigate additional indexes for reporting queries
- [ ] Review normalization opportunities
- [ ] Add more realistic workflow statuses
- [x] Expand specimen lifecycle tracking (Collected, Received > Collected, Received, Accessioned)

#### Specimen Workflow Enhancements

- [ ] Add `uncollected` specimen status
- [ ] Model label-printing workflow prior to specimen collection
- [ ] Simulate specimen lifecycle:
  - Uncollected
  - Collected
  - Received
  - Rejected
- [x] Add accessioning step
- [x] Support multiple specimens per order
- [ ] Simulate workflow delays for accessioning and result reporting analytics

#### Specimen Data Realism

- [x] Generate multiple specimen types
  - Blood
  - Urine
  - Serum
  - Plasma
- [x] Create realistic specimen type distribution
- [ ] Expand specimen type catalog
  - CSF
  - Sputum
  - Stool
  - Tissue

### HL7 Enhancements

- [ ] Simulate ORM^O01 order messages
- [ ] Simulate ORU^R01 result messages
- [ ] Add HL7 message logging table
- [ ] Create HL7 interface monitoring dashboard queries

### Security & Compliance

- [ ] Review role-based access concepts
- [ ] Evaluate audit retention requirements
- [ ] Add support for update/delete audit events
- [ ] Document security assumptions

### Documentation

- [ ] Update ERD screenshots
- [ ] Document foreign key relationships
- [ ] Create workflow diagrams
- [ ] Write database architecture overview

### Learning Topics

- [ ] Revisit `information_schema`
- [ ] Learn metadata queries
- [ ] Explore PostgreSQL system catalogs
- [ ] Learn indexes and query plans
- [ ] Learn database views
- [ ] Learn stored procedures and triggers

## Project Evolution History

### August 2026 - Project Foundation

- Created initial AKAI Community Hospital LIS schema
- Developed automated PostgreSQL synthetic data generator
- Added workflow documentation and specimen intake specifications
- Introduced SQL query portfolio for reporting and analysis exercises
- Implemented GitHub Actions workflow for automated database testing
- Added command-line support for seed script customization

### August 2026 - Schema Normalization and Workflow Redesign

- Replaced `accession_orders` table with normalized `orders` table
- Refactored schema to align with laboratory order and specimen workflows
- Unified LOINC integration design and reporting structure
- Added clinical data integrity check constraints
- Updated seed scripts to support normalized relationships

### August 2026 - Healthcare Reporting Portfolio

- Created healthcare-focused SQL reporting portfolio
- Added patient laboratory result reports
- Added LOINC integration reports
- Added patient order volume reporting
- Developed operational and analytics-oriented SQL exercises

### August 2026 - SQL Server Expansion

- Added full Microsoft SQL Server implementation
- Created SQL Server schema equivalent to PostgreSQL design
- Developed SQL Server synthetic data generator
- Synchronized PostgreSQL and SQL Server seed logic

### August 2026 - Specimen Workflow Realism Enhancements

- Added support for multiple specimen types:
  - Blood
  - Urine
  - Serum
  - Plasma
- Implemented realistic specimen type distribution
- Made specimen type mandatory in schema
- Added accessioned specimen workflow stage
- Extended workflow documentation and diagrams

### August 2026 - Laboratory Lifecycle Improvements

- Added result lifecycle status support:
  - Preliminary
  - Final
  - Corrected
  - Amended
- Added weighted workflow simulation for realistic order states
- Introduced optional ordering provider assignment to simulate incomplete clinical workflows
- Expanded status tracking for orders and laboratory results

### August 2026 - Multi-Specimen Workflow Redesign

- Redesigned LIS model to support multiple specimens per order
- Added `accessioned_datetime` to specimen lifecycle tracking
- Updated PostgreSQL and SQL Server schemas
- Updated PostgreSQL and SQL Server seed generators
- Added indexes supporting order and specimen reporting
- Improved realism of laboratory collection, receipt, accessioning, and reporting workflows

### September 2026 - Operational Analytics Expansion

- Added repeat-test identification reporting
- Added specimen rejection analysis reports
- Added workflow delay analysis reports
- Began design planning for simulated workflow delays to support operational performance analytics
- Developed workflow-analysis reports using lifecycle timestamps (receipt, accessioning, result, reporting)
