"""Reads a PBIP folder (or extracts a PBIX) into the in-memory SemanticModel representation."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

from shared.config import PROJECT_ROOT, SCRATCH_DIR
from shared.model import (
    ColumnInfo,
    CopilotConfig,
    MeasureInfo,
    ModelFormat,
    RelationshipInfo,
    RoleInfo,
    SemanticModel,
    TableInfo,
)


def parse(path: str | Path) -> SemanticModel:
    """Parse a PBIP folder or PBIX file and return a SemanticModel."""
    target = Path(path)
    logger.info("Parsing path: %s (exists=%s, is_file=%s, suffix=%s)", target, target.exists(), target.is_file() if target.exists() else "N/A", target.suffix)

    if target.suffix.lower() == ".pbix":
        return _parse_pbix(target)

    if not target.is_dir():
        raise FileNotFoundError(f"Path is not a directory: {target}")

    model_format = _detect_format(target)
    model_name = target.name.removesuffix(".SemanticModel") or target.name

    if model_format == ModelFormat.TMSL:
        return _parse_tmsl(target, model_name)
    else:
        return _parse_tmdl(target, model_name)


def _parse_pbix(pbix_path: Path) -> SemanticModel:
    """Extract model metadata from a PBIX file (zip archive) and parse it.

    Handles three scenarios:
    1. DataModelSchema entry exists -- readable JSON, parse directly
    2. DataModel entry is uncompressed JSON -- parse directly
    3. DataModel entry is XPress9-compressed -- use pbi-tools to extract
    """
    if not pbix_path.exists():
        raise FileNotFoundError(f"PBIX file not found: {pbix_path}")

    model_name = pbix_path.stem

    with zipfile.ZipFile(pbix_path, "r") as zf:
        names = zf.namelist()
        print(f"[parser] PBIX entries: {names}")

        # Scenario 1: DataModelSchema exists (readable JSON)
        if "DataModelSchema" in names:
            raw = zf.read("DataModelSchema")
            print(f"[parser] DataModelSchema: {len(raw)} bytes")
            text = _decode_schema_bytes(raw)
            bim = json.loads(text)
            return _build_model_from_bim(bim, model_name, pbix_path)

        # Scenario 2: DataModel exists
        if "DataModel" in names:
            # Peek at the header to determine if compressed
            raw = zf.read("DataModel")
            if not (raw.startswith(b"This backup") or raw.startswith(b"T\x00h\x00i\x00s\x00")):
                # Uncompressed -- try to parse as JSON
                print(f"[parser] DataModel: {len(raw)} bytes (uncompressed)")
                text = _decode_schema_bytes(raw)
                bim = json.loads(text)
                return _build_model_from_bim(bim, model_name, pbix_path)

            # Scenario 3: XPress9 compressed -- need pbi-tools
            print(f"[parser] DataModel: {len(raw)} bytes (XPress9 compressed)")

        else:
            raise FileNotFoundError(
                f"No DataModelSchema or DataModel found in PBIX. "
                f"Files in archive: {', '.join(names[:10])}"
            )

    # If we reach here, we need pbi-tools for the compressed DataModel
    pbi_tools_path = _find_pbi_tools()
    if pbi_tools_path:
        return _extract_pbix_via_pbitools(pbix_path, model_name, pbi_tools_path)

    raise ValueError(
        "This PBIX file uses XPress9 compression (newer Power BI format). "
        "To analyze it, either:\n"
        "  1. Install pbi-tools (https://pbi.tools) and restart the app, or\n"
        "  2. In Power BI Desktop: File > Save a copy > "
        "change 'Save as type' to 'Power BI Project (*.pbip)' "
        "and drop the .SemanticModel folder here instead."
    )


def _build_model_from_bim(bim: dict, model_name: str, pbix_path: Path) -> SemanticModel:
    """Build a SemanticModel from a parsed model.bim dict."""
    model_def = bim.get("model", bim)
    tables, relationships, roles = _parse_model_def(model_def)
    return SemanticModel(
        name=model_name,
        path=str(pbix_path),
        format=ModelFormat.TMSL,
        tables=tables,
        relationships=relationships,
        roles=roles,
        copilot=CopilotConfig(),
    )


def _parse_model_def(model_def: dict) -> tuple[list[TableInfo], list[RelationshipInfo], list[RoleInfo]]:
    """Extract tables, relationships, and roles from a TMSL model definition dict."""
    tables = []
    for t in model_def.get("tables", []):
        # Detect if table is marked as a date table via annotations
        is_date_table = False
        for ann in t.get("annotations", []):
            if isinstance(ann, dict) and ann.get("name") == "__PBI_TimeIntelligenceEnabled":
                is_date_table = ann.get("value", "").lower() == "true"

        columns = [
            ColumnInfo(
                name=c.get("name", ""),
                table=t.get("name", ""),
                data_type=c.get("dataType", ""),
                description=c.get("description", ""),
                is_hidden=c.get("isHidden", False),
                data_category=c.get("dataCategory", ""),
                summarize_by=c.get("summarizeBy", ""),
                sort_by_column=c.get("sortByColumn", ""),
                display_folder=c.get("displayFolder", ""),
            )
            for c in t.get("columns", [])
        ]
        measures = [
            MeasureInfo(
                name=m.get("name", ""),
                table=t.get("name", ""),
                expression=_normalize_expression(m.get("expression", "")),
                description=m.get("description", ""),
                is_hidden=m.get("isHidden", False),
                display_folder=m.get("displayFolder", ""),
            )
            for m in t.get("measures", [])
        ]
        tables.append(
            TableInfo(
                name=t.get("name", ""),
                description=t.get("description", ""),
                columns=columns,
                measures=measures,
                is_hidden=t.get("isHidden", False),
                is_date_table=is_date_table,
            )
        )

    relationships = [
        RelationshipInfo(
            from_table=r.get("fromTable", ""),
            from_column=r.get("fromColumn", ""),
            to_table=r.get("toTable", ""),
            to_column=r.get("toColumn", ""),
            is_active=r.get("isActive", True),
            cardinality=r.get("fromCardinality", "") + ":" + r.get("toCardinality", ""),
            cross_filter_direction=r.get("crossFilteringBehavior", ""),
        )
        for r in model_def.get("relationships", [])
    ]

    roles = []
    for role in model_def.get("roles", []):
        filter_exprs = []
        for tp in role.get("tablePermissions", []):
            expr = tp.get("filterExpression", "")
            if expr:
                filter_exprs.append(expr)
        roles.append(RoleInfo(name=role.get("name", ""), filter_expressions=filter_exprs))

    return tables, relationships, roles


def _find_pbi_tools() -> str | None:
    """Locate pbi-tools executable: check project tools/ folder, then system PATH."""
    # Check project-local tools folder (fabric-model-readiness/tools/)
    candidates = [
        PROJECT_ROOT / "tools" / "pbi-tools" / "pbi-tools.exe",
        # Also check parent folder (top-level linter team folder)
        PROJECT_ROOT.parent / "tools" / "pbi-tools" / "pbi-tools.exe",
    ]
    for candidate in candidates:
        print(f"[parser] Checking for pbi-tools at: {candidate} (exists={candidate.exists()})")
        if candidate.exists():
            return str(candidate)
    # Check system PATH
    system_path = shutil.which("pbi-tools")
    if system_path:
        return system_path
    return None


def _extract_pbix_via_pbitools(pbix_path: Path, model_name: str, pbi_tools_path: str) -> SemanticModel:
    """Use pbi-tools CLI to extract a compressed PBIX into a readable PBIP folder.

    pbi-tools handles XPress9 decompression and produces a standard folder
    structure with model.bim or Model/ (TMDL) that we can parse.

    Uses a temp directory outside OneDrive to avoid file-lock issues.
    """
    # Use system temp dir to avoid OneDrive sync locks
    temp_base = Path(tempfile.gettempdir()) / "fabric-model-readiness" / "extractions"
    extract_dir = temp_base / model_name

    # Clean up previous extraction if it exists
    if extract_dir.exists():
        try:
            shutil.rmtree(extract_dir)
        except OSError as e:
            print(f"[parser] Warning: could not clean {extract_dir}: {e}")
            # Try an alternative name
            import time
            extract_dir = temp_base / f"{model_name}_{int(time.time())}"

    extract_dir.mkdir(parents=True, exist_ok=True)

    print(f"[parser] Extracting PBIX with pbi-tools to {extract_dir}")
    result = subprocess.run(
        [pbi_tools_path, "extract", str(pbix_path), "-extractFolder", str(extract_dir)],
        capture_output=True,
        text=True,
        timeout=300,
    )

    print(f"[parser] pbi-tools exit code: {result.returncode}")
    if result.stdout.strip():
        print(f"[parser] pbi-tools stdout: {result.stdout.strip()[:500]}")
    if result.stderr.strip():
        print(f"[parser] pbi-tools stderr: {result.stderr.strip()[:500]}")

    if result.returncode != 0:
        raise ValueError(
            f"pbi-tools extract failed (exit code {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )

    # List top-level contents for diagnostics
    if extract_dir.exists():
        contents = list(extract_dir.iterdir())
        print(f"[parser] Extraction contents: {[p.name for p in contents]}")

    # Find the model in the extracted folder -- could be TMSL (model.bim) or TMDL (Model/ folder)
    bim_candidates = list(extract_dir.rglob("model.bim"))
    if bim_candidates:
        bim_path = bim_candidates[0]
        print(f"[parser] Found model.bim at {bim_path}")
        bim = json.loads(bim_path.read_text(encoding="utf-8"))
        model_def = bim.get("model", bim)
        tables, relationships, roles = _parse_model_def(model_def)
        return SemanticModel(
            name=model_name,
            path=str(pbix_path),
            format=ModelFormat.TMSL,
            tables=tables,
            relationships=relationships,
            roles=roles,
            copilot=CopilotConfig(),
        )

    # Check for TMDL format (Model/ folder with .tmdl files)
    model_dir = extract_dir / "Model"
    if model_dir.is_dir():
        tmdl_files = list(model_dir.rglob("*.tmdl"))
        print(f"[parser] Found Model/ dir with {len(tmdl_files)} .tmdl files")
        table_files = list((model_dir / "tables").glob("*.tmdl")) if (model_dir / "tables").is_dir() else []
        print(f"[parser] Table files: {[f.name for f in table_files]}")

        if (model_dir / "model.tmdl").exists():
            return _parse_tmdl_folder(model_dir, model_name, str(pbix_path))

    # Check for .SemanticModel subfolder
    sm_folders = list(extract_dir.rglob("*.SemanticModel"))
    if sm_folders:
        return parse(sm_folders[0])

    # Gather diagnostics for error message
    all_files = list(extract_dir.rglob("*"))
    file_list = [str(f.relative_to(extract_dir)) for f in all_files[:20]]
    raise FileNotFoundError(
        f"pbi-tools extracted but no parseable model found in {extract_dir}. "
        f"Files found: {file_list}"
    )


def _decode_schema_bytes(raw: bytes) -> str:
    """Decode DataModelSchema bytes, trying multiple encodings.

    PBIX files use various encodings for the DataModelSchema entry:
    - UTF-16-LE with BOM (most common in newer files)
    - UTF-16-LE without BOM
    - UTF-8 with BOM
    - UTF-8 without BOM
    We try each encoding and validate by attempting JSON parse.
    """
    # Check for BOM markers first
    if raw[:2] == b"\xff\xfe":
        text = raw.decode("utf-16-le")
        return text.lstrip("\ufeff")
    if raw[:2] == b"\xfe\xff":
        text = raw.decode("utf-16-be")
        return text.lstrip("\ufeff")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8")

    # No BOM -- heuristic: if every other byte is 0x00, it's UTF-16-LE
    # (most ASCII-range JSON will have this pattern)
    if len(raw) >= 4 and raw[1] == 0 and raw[3] == 0:
        try:
            text = raw.decode("utf-16-le")
            return text.lstrip("\ufeff")
        except UnicodeDecodeError:
            pass

    # Try UTF-8
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass

    # Last resort: strip all null bytes (handles UTF-16-LE without BOM
    # even if the decode above failed due to odd-length or trailing bytes)
    cleaned = raw.replace(b"\x00", b"")
    try:
        return cleaned.decode("utf-8")
    except UnicodeDecodeError:
        # Truly last resort: decode as latin-1 (never fails)
        return cleaned.decode("latin-1")


def _normalize_expression(expr) -> str:
    """Handle DAX expressions that may be a list of lines or a single string."""
    if isinstance(expr, list):
        return "\n".join(expr)
    return str(expr) if expr else ""


def _detect_format(folder: Path) -> ModelFormat:
    """Check definition.pbism to determine TMSL vs TMDL."""
    pbism = folder / "definition.pbism"
    if pbism.exists():
        content = json.loads(pbism.read_text(encoding="utf-8"))
        version = content.get("version", "1.0")
        if version.startswith("4"):
            return ModelFormat.TMDL
    # Fall back: if definition/ folder exists, assume TMDL
    if (folder / "definition").is_dir():
        return ModelFormat.TMDL
    return ModelFormat.TMSL


def _parse_tmsl(folder: Path, model_name: str) -> SemanticModel:
    """Parse a TMSL model from model.bim (single JSON file)."""
    bim_path = folder / "model.bim"
    if not bim_path.exists():
        raise FileNotFoundError(f"Expected model.bim at {bim_path}")

    bim = json.loads(bim_path.read_text(encoding="utf-8"))
    model_def = bim.get("model", bim)
    tables, relationships, roles = _parse_model_def(model_def)
    copilot = _parse_copilot_folder(folder)

    return SemanticModel(
        name=model_name,
        path=str(folder),
        format=ModelFormat.TMSL,
        tables=tables,
        relationships=relationships,
        roles=roles,
        copilot=copilot,
    )


def _parse_tmdl(folder: Path, model_name: str) -> SemanticModel:
    """Parse a TMDL model from the definition/ folder structure."""
    # PBIP TMDL uses definition/ subfolder
    tmdl_dir = folder / "definition"
    if tmdl_dir.is_dir():
        model = _parse_tmdl_folder(tmdl_dir, model_name, str(folder))
    else:
        model = SemanticModel(
            name=model_name,
            path=str(folder),
            format=ModelFormat.TMDL,
            tables=[],
            relationships=[],
        )

    model.copilot = _parse_copilot_folder(folder)
    return model


def _parse_tmdl_folder(model_dir: Path, model_name: str, source_path: str) -> SemanticModel:
    """Parse TMDL files from a Model/ or definition/ folder.

    TMDL format uses indentation-based syntax:
    - model.tmdl: model-level settings and table refs
    - relationships.tmdl: relationship definitions
    - tables/*.tmdl: one file per table with columns and measures
    - roles/*.tmdl: security roles
    """
    tables: list[TableInfo] = []
    relationships: list[RelationshipInfo] = []
    roles: list[RoleInfo] = []

    # Parse relationships
    rel_file = model_dir / "relationships.tmdl"
    if rel_file.exists():
        relationships = _parse_tmdl_relationships(rel_file)

    # Parse roles
    roles_dir = model_dir / "roles"
    if roles_dir.is_dir():
        for role_file in roles_dir.glob("*.tmdl"):
            role = _parse_tmdl_role(role_file)
            if role:
                roles.append(role)

    # Parse tables
    tables_dir = model_dir / "tables"
    if tables_dir.is_dir():
        for table_file in tables_dir.glob("*.tmdl"):
            table = _parse_tmdl_table(table_file)
            if table:
                tables.append(table)

    # Check model.tmdl for date table annotation
    model_file = model_dir / "model.tmdl"
    if model_file.exists():
        content = model_file.read_text(encoding="utf-8")
        if "__PBI_TimeIntelligenceEnabled = 1" in content:
            # Mark date-like tables
            for t in tables:
                if "date" in t.name.lower() or "calendar" in t.name.lower():
                    t.is_date_table = True

    return SemanticModel(
        name=model_name,
        path=source_path,
        format=ModelFormat.TMDL,
        tables=tables,
        relationships=relationships,
        roles=roles,
    )


def _parse_tmdl_table(file_path: Path) -> TableInfo | None:
    """Parse a single TMDL table file into a TableInfo."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return None

    lines = content.split("\n")
    if not lines:
        return None

    # First line: table Name or table 'Name With Spaces'
    table_name = _extract_tmdl_name(lines[0], "table")
    if not table_name:
        return None

    columns: list[ColumnInfo] = []
    measures: list[MeasureInfo] = []
    is_hidden = False
    description = ""
    is_date_table = False

    i = 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Table-level properties
        if stripped == "isHidden":
            is_hidden = True
        elif stripped.startswith("description:"):
            description = stripped.split(":", 1)[1].strip().strip("'\"")

        # Column block
        elif stripped.startswith("column "):
            col, end_i = _parse_tmdl_column(lines, i, table_name)
            if col:
                columns.append(col)
            i = end_i
            continue

        # Measure block
        elif stripped.startswith("measure "):
            measure, end_i = _parse_tmdl_measure(lines, i, table_name)
            if measure:
                measures.append(measure)
            i = end_i
            continue

        # Date table annotation
        elif "__PBI_TimeIntelligenceEnabled" in stripped and "= 1" in stripped:
            is_date_table = True

        i += 1

    return TableInfo(
        name=table_name,
        description=description,
        columns=columns,
        measures=measures,
        is_hidden=is_hidden,
        is_date_table=is_date_table,
    )


def _parse_tmdl_column(lines: list[str], start: int, table_name: str) -> tuple[ColumnInfo | None, int]:
    """Parse a column block from TMDL lines. Returns (ColumnInfo, next_line_index)."""
    col_name = _extract_tmdl_name(lines[start].strip(), "column")
    if not col_name:
        return None, start + 1

    data_type = ""
    description = ""
    is_hidden = False
    summarize_by = ""
    sort_by_column = ""
    display_folder = ""
    data_category = ""

    indent = _get_indent(lines[start])
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        cur_indent = _get_indent(line)
        # If we've dedented back to same or less indent, this block is done
        if cur_indent <= indent and line.strip():
            break

        stripped = line.strip()
        if stripped.startswith("dataType:"):
            data_type = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("description:"):
            description = stripped.split(":", 1)[1].strip().strip("'\"")
        elif stripped == "isHidden":
            is_hidden = True
        elif stripped.startswith("summarizeBy:"):
            summarize_by = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("sortByColumn:"):
            sort_by_column = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("displayFolder:"):
            display_folder = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("dataCategory:"):
            data_category = stripped.split(":", 1)[1].strip()
        i += 1

    return ColumnInfo(
        name=col_name,
        table=table_name,
        data_type=data_type,
        description=description,
        is_hidden=is_hidden,
        summarize_by=summarize_by,
        sort_by_column=sort_by_column,
        display_folder=display_folder,
        data_category=data_category,
    ), i


def _parse_tmdl_measure(lines: list[str], start: int, table_name: str) -> tuple[MeasureInfo | None, int]:
    """Parse a measure block from TMDL lines. Returns (MeasureInfo, next_line_index)."""
    stripped = lines[start].strip()
    # measure 'Name' = EXPRESSION or measure Name = EXPRESSION
    parts = stripped.split("=", 1)
    if len(parts) < 2:
        return None, start + 1

    name_part = parts[0].strip()
    measure_name = _extract_tmdl_name(name_part, "measure")
    if not measure_name:
        return None, start + 1

    expression_parts = [parts[1].strip()]

    description = ""
    is_hidden = False
    display_folder = ""

    indent = _get_indent(lines[start])
    i = start + 1
    # Check if expression continues on next lines (indented more)
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        cur_indent = _get_indent(line)
        if cur_indent <= indent and line.strip():
            break

        s = line.strip()
        if s.startswith("description:"):
            description = s.split(":", 1)[1].strip().strip("'\"")
        elif s == "isHidden":
            is_hidden = True
        elif s.startswith("displayFolder:"):
            display_folder = s.split(":", 1)[1].strip()
        elif s.startswith("formatString:") or s.startswith("annotation ") or s.startswith("changedProperty"):
            pass  # skip known non-expression properties
        else:
            # Could be continuation of multi-line expression
            if not any(s.startswith(k) for k in ("formatString", "annotation", "changedProperty", "lineageTag")):
                expression_parts.append(s)
        i += 1

    expression = "\n".join(expression_parts).strip()

    return MeasureInfo(
        name=measure_name,
        table=table_name,
        expression=expression,
        description=description,
        is_hidden=is_hidden,
        display_folder=display_folder,
    ), i


def _parse_tmdl_relationships(file_path: Path) -> list[RelationshipInfo]:
    """Parse relationships.tmdl file."""
    content = file_path.read_text(encoding="utf-8")
    relationships: list[RelationshipInfo] = []

    lines = content.split("\n")
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("relationship "):
            from_table = from_col = to_table = to_col = ""
            is_active = True
            cross_filter = ""
            cardinality = ""

            indent = _get_indent(lines[i])
            i += 1
            while i < len(lines):
                line = lines[i]
                if not line.strip():
                    i += 1
                    continue
                cur_indent = _get_indent(line)
                if cur_indent <= indent and line.strip():
                    break

                s = line.strip()
                if s.startswith("fromColumn:"):
                    ref = s.split(":", 1)[1].strip()
                    from_table, from_col = _split_tmdl_column_ref(ref)
                elif s.startswith("toColumn:"):
                    ref = s.split(":", 1)[1].strip()
                    to_table, to_col = _split_tmdl_column_ref(ref)
                elif s.startswith("isActive:"):
                    is_active = s.split(":", 1)[1].strip().lower() != "false"
                elif s == "isActive: false":
                    is_active = False
                elif s.startswith("crossFilteringBehavior:"):
                    cross_filter = s.split(":", 1)[1].strip()
                elif s.startswith("fromCardinality:") or s.startswith("toCardinality:"):
                    cardinality += s.split(":", 1)[1].strip() + ":"
                i += 1

            if from_table and to_table:
                relationships.append(RelationshipInfo(
                    from_table=from_table,
                    from_column=from_col,
                    to_table=to_table,
                    to_column=to_col,
                    is_active=is_active,
                    cardinality=cardinality.rstrip(":"),
                    cross_filter_direction=cross_filter,
                ))
            continue
        i += 1

    return relationships


def _parse_tmdl_role(file_path: Path) -> RoleInfo | None:
    """Parse a single TMDL role file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return None

    lines = content.split("\n")
    if not lines:
        return None

    role_name = _extract_tmdl_name(lines[0].strip(), "role")
    if not role_name:
        return None

    filters: list[str] = []
    for line in lines:
        s = line.strip()
        if s.startswith("filterExpression:"):
            filters.append(s.split(":", 1)[1].strip())

    return RoleInfo(name=role_name, filter_expressions=filters)


def _extract_tmdl_name(line: str, keyword: str) -> str:
    """Extract the object name from a TMDL declaration line like 'table Customer' or 'table \\'Name\\'.'"""
    if not line.startswith(keyword + " "):
        return ""
    rest = line[len(keyword) + 1:].strip()
    # Remove trailing = ... (for measures)
    if " = " in rest and keyword == "measure":
        rest = rest.split(" = ")[0].strip()
    # Strip quotes
    if rest.startswith("'") and rest.endswith("'"):
        return rest[1:-1]
    return rest


def _split_tmdl_column_ref(ref: str) -> tuple[str, str]:
    """Split a TMDL column reference like 'Fact - Sales'.CustomerKey into (table, column)."""
    # Format: 'Table Name'.ColumnName or TableName.ColumnName
    if "." not in ref:
        return ref, ""
    if ref.startswith("'"):
        # 'Table Name'.Column
        end_quote = ref.index("'", 1)
        table = ref[1:end_quote]
        col = ref[end_quote + 2:]  # skip '.
    else:
        parts = ref.split(".", 1)
        table = parts[0]
        col = parts[1] if len(parts) > 1 else ""
    return table, col


def _get_indent(line: str) -> int:
    """Count leading tabs in a line."""
    count = 0
    for ch in line:
        if ch == "\t":
            count += 1
        else:
            break
    return count


def _parse_copilot_folder(folder: Path) -> CopilotConfig:
    """Read Copilot/ subfolder contents."""
    copilot_dir = folder / "Copilot"
    config = CopilotConfig()

    if not copilot_dir.is_dir():
        return config

    # schema.json
    schema_path = copilot_dir / "schema.json"
    if schema_path.exists():
        config.schema_json_exists = True
        config.schema_json = json.loads(schema_path.read_text(encoding="utf-8"))

    # Instructions
    instructions_path = copilot_dir / "Instructions" / "instructions.md"
    if instructions_path.exists():
        config.instructions_exist = True
        config.instructions_content = instructions_path.read_text(encoding="utf-8")

    # Verified answers
    va_dir = copilot_dir / "VerifiedAnswers" / "definitions"
    if va_dir.is_dir():
        for answer_dir in va_dir.iterdir():
            if answer_dir.is_dir():
                defn_path = answer_dir / "definition.json"
                if defn_path.exists():
                    config.verified_answers.append(
                        json.loads(defn_path.read_text(encoding="utf-8"))
                    )

    # Settings
    settings_path = copilot_dir / "settings.json"
    if settings_path.exists():
        config.settings = json.loads(settings_path.read_text(encoding="utf-8"))

    return config
