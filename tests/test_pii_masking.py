"""
tests/test_pii_masking.py — PII masking tests for pii_guard.py

Verifies that mask_pii() suppresses all six PII categories and does not
alter text that contains no PII.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pii_guard import mask_pii


def test_ssn_dashes():
    result = mask_pii("Patient SSN: 123-45-6789")
    assert "123-45-6789" not in result
    assert "[SSN]" in result or "***" in result or "REDACTED" in result.upper()

def test_mrn_masked():
    result = mask_pii("MRN: 9876543")
    assert "9876543" not in result

def test_mrn_label_medical_record():
    result = mask_pii("medical record 1234567")
    assert "1234567" not in result

def test_dob_slash_format():
    result = mask_pii("DOB: 05/22/1965")
    assert "05/22/1965" not in result

def test_dob_iso_format():
    result = mask_pii("date of birth 1965-05-22")
    assert "1965-05-22" not in result

def test_patient_name_masked():
    result = mask_pii("Patient Jane Doe admitted today")
    assert "Jane Doe" not in result

def test_patient_name_mixed_case():
    result = mask_pii("patient John Smith in eMAR")
    assert "John Smith" not in result

def test_no_pii_unchanged():
    clean = "How does eMAR handle medication administration records?"
    assert mask_pii(clean) == clean

def test_multiple_pii_types():
    text = "Patient John Smith, DOB 01/01/1970, MRN 1234567, SSN 111-22-3333"
    result = mask_pii(text)
    assert "John Smith" not in result
    assert "01/01/1970" not in result
    assert "1234567" not in result
    assert "111-22-3333" not in result

def test_titled_name_masked():
    result = mask_pii("Mrs. Johnson needs medication review")
    assert "Mrs. Johnson" not in result
