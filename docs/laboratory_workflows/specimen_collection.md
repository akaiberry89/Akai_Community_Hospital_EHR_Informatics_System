# Specimen Collection Workflow

## Purpose

This workflow describes how a specimen enters the laboratory system.

## Process

1. Provider orders laboratory testing.

2. Patient arrives for collection.

3. Specimen label is generated and printed.

4. Phlebotomist or MLT/MLS collects specimen.

5. Specimen is verified against patient identity and order information.

6. Specimen is transported to the laboratory.

7. Specimen is received and accessioned.

## Database Workflow Mapping

```text
Patient
    ↓
Order Created
    ↓
Specimen Label Generated
    ↓
Specimen Collected
    ↓
Specimen Received & Accessioned
    ↓
Laboratory Testing
    ↓
Result Reported
```

## Related Tables

- patients
- orders
- specimens

## Future Workflow Enhancements

- [ ] Add `uncollected` specimen status
- [ ] Model label-printing workflow prior to specimen collection
- [ ] Expand specimen lifecycle tracking
- [ ] Differentiate collection time from laboratory receipt time

### Future Workflow Concept

```text
Patient
    ↓
Order Created
    ↓
Specimen Label Generated
    ↓
Uncollected
    ↓
Specimen Collected
    ↓
Specimen Received & Accessioned
    ↓
Laboratory Testing
    ↓
Result Reported
```
