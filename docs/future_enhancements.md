# AKAI Community Hospital LIS
## Future Enhancements

### Audit Log Improvements

- [x] Ensure seed data assigns `user_id` to all audit records
- [ ] Evaluate enforcing `audit_log.user_id` as NOT NULL in db schema (constraint)
- [ ] Add dedicated `system` user account for automated processes
- [ ] Ensure all audit events are attributable to either:
  - Human User
  - System Process (In a lab, sometimes a system updates overnight without a user input)
- [ ] Review audit trail design against healthcare compliance best practices

### Audit Reporting

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
