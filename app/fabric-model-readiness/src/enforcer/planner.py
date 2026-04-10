"""Reads Scout findings and generates a prioritized list of change proposals.

Uses template-based fix generation -- no LLM API key required.
"""

from __future__ import annotations

import re

from shared.model import (
    Category,
    ChangeProposal,
    ChangePlan,
    Finding,
    ScanReport,
    Severity,
)

SEVERITY_ORDER = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]


def build_change_plan(report: ScanReport) -> ChangePlan:
    """Convert a scan report into a change plan with concrete proposals."""
    proposals: list[ChangeProposal] = []

    sorted_findings = sorted(
        report.findings,
        key=lambda f: SEVERITY_ORDER.index(f.severity),
    )

    for finding in sorted_findings:
        proposal = _finding_to_proposal(finding)
        if proposal:
            proposals.append(proposal)

    return ChangePlan(
        model_name=report.model_path,
        scan_id=report.scan_id,
        pre_score=report.summary.score,
        proposals=proposals,
    )


def _finding_to_proposal(finding: Finding) -> ChangeProposal | None:
    """Convert a single finding into a change proposal."""
    title = finding.message.split(".")[0]
    why = _generate_why(finding)
    change_description = finding.recommendation or finding.message
    proposed_value = None

    if finding.auto_fixable:
        proposed_value = _generate_fix(finding)

    impact = None
    if finding.check in ("column_naming", "table_naming", "measure_naming"):
        impact = "May break existing DAX measures or report visuals. Review dependencies first."

    return ChangeProposal(
        finding_id=finding.id,
        category=finding.category,
        severity=finding.severity,
        object=finding.object,
        object_type=finding.object_type,
        title=title,
        why=why,
        change_description=change_description,
        impact=impact,
        auto_fixable=finding.auto_fixable,
        proposed_value=proposed_value,
    )


def _generate_why(finding: Finding) -> str:
    """Explain the 'why' in terms of Copilot/AI impact."""
    why_map = {
        "table_descriptions": "Copilot uses the first 200 chars of table descriptions to understand what data a table contains. Without this, Copilot may misinterpret or ignore the table.",
        "column_descriptions": "Column descriptions help Copilot match natural language questions to the correct field.",
        "measure_descriptions": "Measure descriptions tell Copilot when and how to use each calculation.",
        "synonyms": "Synonyms enable Copilot to match varied natural language phrasing to columns.",
        "ai_schema_configured": "Without an AI schema, Copilot has no field selection guidance and may use irrelevant columns.",
        "ai_instructions_present": "AI instructions provide business context that shapes how Copilot generates DAX.",
        "noise_fields_excluded": "ID, sort, and key columns clutter the AI schema and confuse natural language matching.",
        "default_summarization": "Incorrect default summarization causes Copilot to produce wrong aggregations (e.g., SUM of Year).",
        "missing_relationships": "Copilot cannot traverse disconnected tables. Orphaned tables are invisible to AI.",
    }
    return why_map.get(finding.check, finding.message)


# ---------------------------------------------------------------------------
# Template-based fix generation (no LLM required)
# ---------------------------------------------------------------------------

# Common suffixes that hint at column purpose
_KEY_PATTERN = re.compile(r"(Key|Id|ID|Code)$", re.IGNORECASE)
_DATE_PATTERN = re.compile(r"(Date|Dt|Time|Timestamp)$", re.IGNORECASE)
_NAME_PATTERN = re.compile(r"(Name|Title|Label|Desc)$", re.IGNORECASE)
_AMOUNT_PATTERN = re.compile(r"(Amount|Amt|Price|Cost|Revenue|Sales|Total|Sum|Value)$", re.IGNORECASE)
_COUNT_PATTERN = re.compile(r"(Count|Cnt|Qty|Quantity|Number|Num)$", re.IGNORECASE)
_FLAG_PATTERN = re.compile(r"(Flag|Is|Has|Can|Should|Active|Enabled|Deleted)$", re.IGNORECASE)
_FACT_PATTERN = re.compile(r"(Fact|Fct|f_)", re.IGNORECASE)


def _humanize(name: str) -> str:
    """Convert CamelCase/snake_case/PascalCase to readable text."""
    # Handle snake_case
    name = name.replace("_", " ")
    # Handle CamelCase: insert space before uppercase letters
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    # Clean up extra spaces
    return re.sub(r"\s+", " ", name).strip()


def _generate_table_description(table_name: str) -> str:
    """Generate a description for a table based on its name."""
    readable = _humanize(table_name)

    if _FACT_PATTERN.search(table_name):
        core = _FACT_PATTERN.sub("", readable).strip(" -_")
        return (
            f"Fact table recording {core.lower()} transactions. "
            f"Contains measures and foreign keys linking to related dimension tables."
        )

    if "measure" in table_name.lower():
        return (
            f"Dedicated measure table containing calculated DAX measures. "
            f"This table has no data rows and exists solely to organize business calculations."
        )

    if "date" in table_name.lower() or "calendar" in table_name.lower():
        return (
            f"Date dimension table providing calendar attributes for time-based analysis. "
            f"Used for filtering and grouping by year, quarter, month, and day."
        )

    return (
        f"Dimension table containing {readable.lower()} attributes. "
        f"Used to filter and group related fact data in reports and Copilot queries."
    )


def _generate_column_description(col_name: str, table_name: str) -> str:
    """Generate a description for a column based on its name and table context."""
    readable_col = _humanize(col_name)
    readable_tbl = _humanize(table_name)

    if _KEY_PATTERN.search(col_name):
        base = _KEY_PATTERN.sub("", readable_col).strip()
        if base.lower() == readable_tbl.lower() or not base:
            return f"Unique identifier for each {readable_tbl.lower()} record. Primary key."
        return f"Foreign key linking to the {base} dimension table."

    if _DATE_PATTERN.search(col_name):
        base = _DATE_PATTERN.sub("", readable_col).strip()
        action = base.lower() if base else "transaction"
        return f"The date when the {action} occurred. Use for time-based filtering and analysis."

    if _NAME_PATTERN.search(col_name):
        base = _NAME_PATTERN.sub("", readable_col).strip()
        entity = base.lower() if base else readable_tbl.lower()
        return f"The display name of the {entity}. Primary text field for labels and slicers."

    if _AMOUNT_PATTERN.search(col_name):
        return f"{readable_col} value. Numeric field typically used in sum/average aggregations."

    if _COUNT_PATTERN.search(col_name):
        return f"{readable_col}. Numeric count field for aggregation."

    if _FLAG_PATTERN.search(col_name):
        return f"Boolean indicator: {readable_col.lower()}. Use for filtering records."

    return f"{readable_col} attribute in the {readable_tbl} table."


def _generate_measure_description(measure_name: str, table_name: str) -> str:
    """Generate a description for a measure based on its name."""
    readable = _humanize(measure_name)

    if "total" in measure_name.lower() or "sum" in measure_name.lower():
        return f"Calculates the total {readable.lower().replace('total', '').strip()}."
    if "count" in measure_name.lower():
        return f"Counts the number of {readable.lower().replace('count', '').replace('of', '').strip()} records."
    if "avg" in measure_name.lower() or "average" in measure_name.lower():
        return f"Calculates the average {readable.lower().replace('average', '').replace('avg', '').strip()}."
    if "%" in measure_name or "pct" in measure_name.lower() or "percent" in measure_name.lower():
        return f"Calculates the {readable.lower()} as a percentage."
    if "ytd" in measure_name.lower():
        return f"Year-to-date calculation for {readable.lower().replace('ytd', '').strip()}."
    if "ly" in measure_name.lower() or "last year" in measure_name.lower():
        return f"Prior year comparison: {readable.lower()}."

    return f"Calculated measure: {readable}. Defined in the {_humanize(table_name)} table."


def _generate_synonyms(col_name: str, table_name: str) -> list[str]:
    """Generate synonym suggestions from column name patterns."""
    readable = _humanize(col_name).lower()
    synonyms: set[str] = set()

    # Add the readable form
    synonyms.add(readable)

    # Add common abbreviation expansions
    abbrevs = {
        "qty": "quantity", "amt": "amount", "desc": "description",
        "num": "number", "cnt": "count", "dt": "date",
        "addr": "address", "tel": "telephone", "phn": "phone",
        "mgr": "manager", "dept": "department", "cat": "category",
        "prod": "product", "cust": "customer", "emp": "employee",
        "inv": "invoice", "txn": "transaction", "acct": "account",
    }
    words = readable.split()
    expanded = [abbrevs.get(w, w) for w in words]
    if expanded != words:
        synonyms.add(" ".join(expanded))

    # Add without common suffixes like "key", "id"
    stripped = _KEY_PATTERN.sub("", col_name).strip("_ ")
    if stripped and stripped.lower() != col_name.lower():
        synonyms.add(_humanize(stripped).lower())

    # Remove the original column name if it snuck in unchanged
    synonyms.discard(col_name.lower())

    return sorted(synonyms)[:4]  # Cap at 4 synonyms


def _generate_fix(finding: Finding) -> str | list[str] | None:
    """Generate a concrete proposed value using templates (no LLM needed)."""
    if finding.check == "table_descriptions":
        return _generate_table_description(finding.object)

    if finding.check == "column_descriptions":
        parts = finding.object.split(".")
        if len(parts) == 2:
            return _generate_column_description(parts[1], parts[0])
        return _generate_column_description(finding.object, "")

    if finding.check == "measure_descriptions":
        parts = finding.object.split(".")
        if len(parts) == 2:
            return _generate_measure_description(parts[1], parts[0])
        return _generate_measure_description(finding.object, "")

    if finding.check == "synonyms":
        parts = finding.object.split(".")
        if len(parts) == 2:
            return _generate_synonyms(parts[1], parts[0])
        return _generate_synonyms(finding.object, "")

    if finding.check == "default_summarization":
        return "None (Don't Summarize)"

    if finding.check == "noise_fields_excluded":
        return "Hide from AI schema"

    if finding.check == "helper_measures_exposed":
        return "Set isHidden = true"

    return None
