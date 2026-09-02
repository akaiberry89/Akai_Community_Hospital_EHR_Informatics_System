-- ============================================================================
-- AKAI LIS SQL QUERY PORTFOLIO
-- AUTHOR: Theophilus K. Akai
-- PURPOSE:
-- Healthcare Informatics, LIS Operations, Quality Assurance,
-- and Clinical Reporting Queries
-- ============================================================================

-- ============================================================================
-- QUERY 001: Rejected Specimen Investigation
-- BUSINESS QUESTION:
-- Which patients had a rejected specimen and why was it rejected?
--
-- SKILLS:
-- INNER JOIN
-- WHERE
-- ORDER BY
-- Healthcare Quality Assurance Reporting

SELECT
    p.first_name,
    p.last_name,
    s.accession_number,
    s.rejection_reason
FROM patients p
JOIN orders o
    ON p.patient_id = o.patient_id
JOIN specimens s
    ON o.order_id = s.order_id
WHERE s.rejection_reason IS NOT NULL
ORDER BY s.accession_number ASC;

-- ============================================================================
-- QUERY 002: Human-Readable Laboratory Results
-- BUSINESS QUESTION:
-- Show laboratory results using human-readable test name rather than LOINC code.
--
-- SKILLS:
-- Normalization
-- LOINC Integration
-- JOINs
-- Clinical terminology

SELECT
    lr.result_id,
    lm.test_name,
    lr.result_value
FROM lab_results lr
JOIN loinc_map lm
    ON lr.loinc_code = lm.loinc_code;

-- ============================================================================
-- QUERY 003: Patient Laboratory Result Report
-- BUSINESS QUESTION:
-- Show patient names, test names, and laboratory result values.
--
-- SKILLS:
-- 5-table JOIN
-- LOINC Integration
-- Clinical workflow reporting
-- Relational data

SELECT
    p.first_name,
    p.last_name,
    lm.test_name,
    lr.result_value
FROM patients p
JOIN orders o
    ON p.patient_id = o.patient_id
JOIN specimens s
    ON o.order_id = s.order_id
JOIN lab_results lr
    ON s.specimen_id = lr.specimen_id
JOIN loinc_map lm
    ON lr.loinc_code = lm.loinc_code;

-- ============================================================================
-- QUERY 004: Patient Order Volume Report
-- BUSINESS QUESTION:
-- How many lab orders has each patient received?
--
-- SKILLS:
-- INNER JOIN
-- COUNT Aggregate Function
-- GROUP BY
-- ORDER BY
-- Healthcare Operational Analytics

SELECT
    p.first_name || ' ' || p.last_name AS patient_name,
    COUNT(o.order_id) AS total_orders
FROM patients p
JOIN orders o
    ON p.patient_id = o.patient_id
GROUP BY
    p.patient_id,
    p.first_name,
    p.last_name
ORDER BY total_orders DESC;

-- ============================================================================
-- QUERY 005: Identifying High-Volume Patients Through Order and Specimen Analysis
-- BUSINESS QUESTION: 
-- The Laboratory Director wants a report showing:
        Patient full name
        MRN
        Total number of orders
        Total number of specimens
        Only include patients who have:
        More specimens than orders
        Sort by:
        Largest difference between specimen count and order count
        Then highest specimen count
        Return one row per patient.

-- SKILLS:
-- SELECT
-- JOIN
-- GROUP BY
-- HAVING
-- ORDER BY
-- Aggregate functions

SELECT
	CONCAT(p.first_name, ' ', p.last_name) AS patient_name,
	p.mrn,
	COUNT(DISTINCT o.order_id) AS total_number_of_orders,
	COUNT(s.specimen_id) AS total_number_of_specimens
FROM specimens s
JOIN orders o
	ON s.order_id = o.order_id
JOIN patients p
	ON o.patient_id = p.patient_id
GROUP BY p.patient_id
HAVING COUNT(s.specimen_id) > COUNT(DISTINCT o.order_id)
ORDER BY 
	(COUNT(s.specimen_id) - COUNT(DISTINCT o.order_id)) DESC,
	total_number_of_specimens DESC;   

-- ============================================================================
-- QUERY 006: Identifying patients who have received the same test multiple times
-- BUSINESS QUESTION: 
-- "Can you help me identify patients who appear to be receiving the same test more than once so we can review whether the repeat testing was clinically necessary?"

SELECT
	p.patient_id,
	CONCAT(p.first_name, ' ', p.last_name) AS patient_name,
	lr.loinc_code,
	COUNT(lr.loinc_code) AS test_count
FROM lab_results lr
JOIN specimens s
	ON lr.specimen_id = s.specimen_id
JOIN orders o
	ON s.order_id = o.order_id
JOIN patients p 
	ON o.patient_id = p.patient_id
GROUP BY 
	p.patient_id,
	p.first_name,
	p.last_name,
	lr.loinc_code
HAVING COUNT(lr.loinc_code) > 1
ORDER BY test_count DESC;
