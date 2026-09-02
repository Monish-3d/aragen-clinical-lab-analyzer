"""Loads the Kaggle lab dataset and looks up reference ranges by test name."""

import csv
from dataclasses import dataclass
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "lab_test_results_public.csv"

# The dataset is Turkish, but only a handful of words actually appear in the
# reference and status columns, so a small lookup is enough to show English.
TURKISH_TERMS = {
    "negatif": "Negative",
    "normal": "Normal",
    "yüksek": "High",
}

# The dataset's Recommended_Followup column only ever holds these five phrases,
# so a small lookup covers all of it. Anything unexpected is passed through
# untranslated rather than dropped.
FOLLOWUP_TERMS = {
    "rutin kontrol": "Routine check-up",
    "takip gerekmez": "No follow-up needed",
    "mevcut düzeni koruma": "Maintain current routine",
    "demir açısından zengin beslenme": "Iron-rich diet",
    "tekrar idrar tahlili önerilir": "Repeat urine test recommended",
}


@dataclass
class ReferenceInfo:
    """Reference information for one lab test, taken from the dataset."""

    test_name: str
    unit: str
    reference_range: str
    is_numeric: bool
    min_reference: float | None = None
    max_reference: float | None = None

    # What the laboratory suggests for this test as routine follow-up. Comes
    # from the dataset, so the LLM has something real to base a next step on
    # instead of inventing one.
    recommended_followup: str | None = None


def translate_term(value):
    """Turn a Turkish reference/status word into English if we know it."""
    value = value.strip()
    return TURKISH_TERMS.get(value.lower(), value)


def translate_followup(value):
    """Same idea for the follow-up column, which holds phrases not words."""
    value = value.strip()
    if not value:
        return None
    return FOLLOWUP_TERMS.get(value.lower(), value)


def normalize_test_name(test_name):
    """Key used for lookups, so casing and stray spaces don't matter."""
    # Turkish "İ" does not lowercase to a plain "i" in Python - it becomes "i"
    # plus a combining dot. Replacing it first means a user typing "insülin"
    # still matches the dataset's "İnsülin".
    return test_name.replace("İ", "i").strip().lower()


def parse_number(value):
    """Dataset numbers are strings, and categorical rows leave them blank."""
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_reference_data(csv_path=DATA_FILE):
    """Read the dataset into a dict keyed by normalized test name.

    Lookup is an exact match on purpose. The dataset contains both "Lökosit"
    and "Lökosit (Strip)" (same for "Eritrosit"), which are different tests
    with different reference ranges, so substring matching would mix them up.
    """
    reference = {}

    # The file is saved with a BOM, so it needs utf-8-sig. With plain utf-8 the
    # BOM stays glued to the first column name and row["Date"] blows up.
    with open(csv_path, encoding="utf-8-sig", newline="") as csv_file:
        for row in csv.DictReader(csv_file):
            test_name = row["Test_Name"].strip()
            if not test_name:
                continue

            min_reference = parse_number(row["Min_Reference"])
            max_reference = parse_number(row["Max_Reference"])

            # Only treat a test as numeric when both limits are usable,
            # otherwise it is a categorical test like "Protein (Strip)".
            is_numeric = min_reference is not None and max_reference is not None

            reference[normalize_test_name(test_name)] = ReferenceInfo(
                test_name=test_name,
                unit=row["Unit"].strip(),
                reference_range=translate_term(row["Reference_Range"]),
                is_numeric=is_numeric,
                min_reference=min_reference,
                max_reference=max_reference,
                recommended_followup=translate_followup(
                    row.get("Recommended_Followup", "")
                ),
            )

    return reference


REFERENCE_DATA = load_reference_data()


def lookup_reference(test_name):
    """Return ReferenceInfo for a test, or None if the dataset has no entry."""
    if not test_name:
        return None
    return REFERENCE_DATA.get(normalize_test_name(test_name))


def known_test_names():
    """Test names we have reference data for, used in 'unknown test' errors."""
    return sorted(info.test_name for info in REFERENCE_DATA.values())
