"""Severity classification and routing.

Classification is plain Python on purpose. The assignment says to compare the
value against its reference range, and keeping it out of the LLM means the same
input always produces the same status. The LLM only explains the status that
was already decided here.
"""

from dataclasses import dataclass

from reference_data import translate_term

NORMAL = "NORMAL"
WARNING = "WARNING"
CRITICAL = "CRITICAL"
# Used when we cannot classify at all (no reference data, unusable value).
# It is not a severity, so it is routed after the real ones.
UNKNOWN = "UNKNOWN"

# A result outside the reference range is CRITICAL if either rule fires,
# otherwise it is a WARNING.
#
# Two rules are needed because one alone gets a whole class of tests wrong.
# Measuring the deviation in "range widths" works for a narrow range like
# Hemoglobin 12-15, but Ferritin's range is 15-150, so a width of 135 means a
# ferritin of 5 scores 0.07 and no low ferritin could ever be critical. The
# second rule compares the deviation against the limit it crossed instead,
# which catches exactly those cases.
#
# The dataset gives no clinical critical limits for any test, so these are
# application rules for the assignment - not medical guidelines.
CRITICAL_RANGE_WIDTHS = 1.0
CRITICAL_BOUNDARY_FRACTION = 0.5

# Urine strip results are graded 1+ to 4+. The only abnormal row in the dataset
# is Eritrosit (Strip) = 1+, and its recommended follow-up is just "repeat the
# urine test", so a low grade is a WARNING rather than CRITICAL.
CRITICAL_STRIP_GRADES = {"3+", "4+"}

# Critical first, because that is the order the results have to be shown in.
SEVERITY_ORDER = {CRITICAL: 0, WARNING: 1, NORMAL: 2, UNKNOWN: 3}


@dataclass
class Classification:
    """One classified lab result, before the LLM adds its explanation."""

    test_name: str
    value: object
    unit: str
    reference_range: str
    status: str
    reason: str

    # Kept so the frontend can draw where the value sits on its range. Only
    # numeric tests have them.
    min_reference: float | None = None
    max_reference: float | None = None

    # The laboratory's routine follow-up for this test, from the dataset.
    # Passed to the LLM as grounding for the suggested next step.
    recommended_followup: str | None = None


def format_number(number):
    """Keep numbers readable - plain float maths gives things like 3.90000004."""
    return f"{number:g}"


def normalize_unit(unit):
    """Units only need to match loosely, so ignore case and the micro sign."""
    if not unit:
        return ""
    return unit.strip().lower().replace("µ", "u")


def parse_value(value):
    """Return the value as a float, or None if it is not a number."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_numeric(value, reference):
    """Compare a numeric result against its min/max reference limits."""
    # Some tests (pH, Dansite) have "-" as their unit, which would read as
    # "1.010-1.030 -" if it were appended.
    unit_text = "" if reference.unit in ("", "-") else reference.unit
    range_text = f"{reference.reference_range} {unit_text}".strip()

    # Boundary values count as normal, so this uses <= on both sides.
    if reference.min_reference <= value <= reference.max_reference:
        return NORMAL, (
            f"{format_number(value)} is inside the reference range {range_text}."
        )

    if value < reference.min_reference:
        direction = "below"
        limit_name = "lower"
        boundary = reference.min_reference
        deviation = reference.min_reference - value
    else:
        direction = "above"
        limit_name = "upper"
        boundary = reference.max_reference
        deviation = value - reference.max_reference

    range_width = reference.max_reference - reference.min_reference

    # Both ratios are guarded, since a zero-width range or a limit of 0 would
    # divide by zero. No test in the dataset has either, but a bad CSV could.
    widths_out = deviation / range_width if range_width > 0 else 0
    boundary_fraction = deviation / boundary if boundary > 0 else 0

    if widths_out > CRITICAL_RANGE_WIDTHS:
        detail = f"more than the full width of the range ({format_number(range_width)})"
    elif boundary_fraction > CRITICAL_BOUNDARY_FRACTION:
        detail = (
            f"more than half of the {limit_name} reference limit "
            f"({format_number(boundary)})"
        )
    else:
        return WARNING, (
            f"{format_number(value)} is {direction} the reference range "
            f"{range_text} by {format_number(deviation)}."
        )

    return CRITICAL, (
        f"{format_number(value)} is {direction} the reference range {range_text} "
        f"by {format_number(deviation)}, which is {detail}."
    )


def classify_categorical(value, reference):
    """Compare a text result (Negative, 1+, ...) against its expected value."""
    # The dataset is Turkish and the API may be sent English, so both sides go
    # through the same translation before they are compared. Without this,
    # "Negative" would not match the dataset's "Negatif".
    result = translate_term(str(value)).lower()
    expected = translate_term(reference.reference_range).lower()

    if result == expected:
        return NORMAL, (
            f"The result is {reference.reference_range}, which is the expected "
            f"value for this test."
        )

    if result in CRITICAL_STRIP_GRADES:
        return CRITICAL, (
            f"The result is {value}, a high grade where {reference.reference_range} "
            f"is expected."
        )

    return WARNING, (
        f"The result is {value}, where {reference.reference_range} is expected."
    )


def classify_lab_result(test_name, value, unit, reference):
    """Classify one lab result.

    The reference is passed in rather than looked up here, because the agent
    resolves it through the MCP server before calling this.
    """
    if reference is None:
        return Classification(
            test_name=test_name,
            value=value,
            unit=unit or "",
            reference_range="",
            status=UNKNOWN,
            reason=(
                "No reference range is available for this test, so it cannot be "
                "classified."
            ),
        )

    if value is None or str(value).strip() == "":
        return Classification(
            test_name=reference.test_name,
            value=value,
            unit=unit or reference.unit,
            reference_range=reference.reference_range,
            status=UNKNOWN,
            reason="No result value was supplied for this test.",
        )

    # A value in the wrong unit means something completely different, so it is
    # safer to refuse than to compare it against the range anyway.
    if unit and normalize_unit(unit) != normalize_unit(reference.unit):
        return Classification(
            test_name=reference.test_name,
            value=value,
            unit=unit,
            reference_range=reference.reference_range,
            status=UNKNOWN,
            reason=(
                f"The supplied unit '{unit}' does not match the expected unit "
                f"'{reference.unit}' for this test."
            ),
        )

    if reference.is_numeric:
        number = parse_value(value)
        if number is None:
            return Classification(
                test_name=reference.test_name,
                value=value,
                unit=unit or reference.unit,
                reference_range=reference.reference_range,
                status=UNKNOWN,
                reason=(
                    f"'{value}' is not a number, but this test expects a numeric "
                    f"result."
                ),
            )
        status, reason = classify_numeric(number, reference)
        value = number
    else:
        status, reason = classify_categorical(value, reference)

    return Classification(
        test_name=reference.test_name,
        value=value,
        unit=unit or reference.unit,
        reference_range=reference.reference_range,
        status=status,
        reason=reason,
        min_reference=reference.min_reference,
        max_reference=reference.max_reference,
        recommended_followup=reference.recommended_followup,
    )


def route_by_severity(classifications):
    """Order results critical first, then warning, then normal.

    sorted() is stable, so results with the same status stay in the order they
    were sent in.
    """
    return sorted(classifications, key=lambda item: SEVERITY_ORDER[item.status])


def summarize(classifications):
    """Count each status for the summary shown above the results."""
    summary = {"critical": 0, "warning": 0, "normal": 0, "unknown": 0}
    for item in classifications:
        summary[item.status.lower()] += 1
    return summary
