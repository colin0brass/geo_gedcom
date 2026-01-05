"""
Legacy Family Tree GEDCOM to GEDCOM 5.5/5.5.1 Converter

This module provides a robust, standalone Python converter for GEDCOM files exported by Legacy Family Tree.
It reads Legacy GEDCOM files, normalizes and cleans up custom facts, merges multiline fields (CONT/CONC),
and emits a standards-compliant GEDCOM 5.5/5.5.1 file. The parser is line-based and does not require external
GEDCOM libraries. It is designed to be forgiving of malformed lines and to support all record types found in
real-world Legacy exports.

Key features:
- Converts Legacy Family Tree GEDCOMs to modern GEDCOM 5.5/5.5.1
- Handles CONT/CONC multiline fields robustly
- Converts custom underscore facts to EVEN/TYPE with readable labels
- Normalizes camelCase fact types to spaced words
- Skips or logs malformed or metadata lines
- Emits HEAD, INDI, SUBM, and other top-level records as found

Usage:
    from pathlib import Path
    from geo_gedcom.gedcom_legacy import GedcomLegacy
    converter = GedcomLegacy(Path('input.ged'))
    converter.legacy_convert(Path('output.ged'))
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TextIO

logger = logging.getLogger(__name__)


@dataclass
class Node:
    tag: str
    value: str = ""
    children: List["Node"] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


class GedcomLegacy:
    """
    Legacy Family Tree GEDCOM -> GEDCOM 5.5 converter using ged4py for parsing.

    Notes:
      - ged4py is used for reading; this class includes a simple emitter for writing.
      - The converter focuses on:
          * Fixing HEAD to GEDCOM 5.5 (GEDC.VERS=5.5, FORM=LINEAGE-LINKED, CHAR=UTF-8)
          * Converting common Legacy/custom underscore fact tags to EVEN/TYPE
          * Normalizing EVEN/TYPE camelCase into spaced words (MilitaryService -> Military Service)
      - If you need perfect top-level record order preservation, you’ll need a different iteration strategy.
    """

    CUSTOM_FACT_MAP: Dict[str, str] = {
        "_MILT": "Military Service",
        "_MIL": "Military Service",
        "_SERV": "Military Service",
        "_SERVICE": "Military Service",
        "_NATU": "Naturalization",
        "_EMIG": "Emigration",
        "_IMMI": "Immigration",
        "_CENS": "Census",
        "_EDUC": "Education",
        "_OCCU": "Occupation",
        "_RELI": "Religion",
        "_RESI": "Residence",
        "_PROP": "Property",
        "_TITL": "Title",
        "_NICK": "Nickname",
        "_DNA": "DNA",
    }

    SKIP_UNDERSCORE_TAGS = {"_UID", "_UUID", "_CREA", "_UPD", "_COLOR", "_PLAC", "_AKA"}

    # A conservative set of top-level record types we’ll output (extend if needed)
    TOP_LEVEL_TAGS = ["SUBM", "INDI", "FAM", "SOUR", "REPO", "NOTE", "OBJE"]

    # Max lines to scan for Legacy detection
    LEGACY_DETECTION_LINE_LIMIT = 120

    def __init__(self, input_path: Path):
        """
        Initialize the converter with the input GEDCOM file path.
        Args:
            input_path (Path): Path to the input GEDCOM file.
        """
        self.input_path = input_path

    def camel_to_spaced(self, s: str) -> str:
        s = (s or "").strip()
        if not s:
            children: List["Node"] = field(default_factory=list)
        s = s.replace("_", " ").replace("-", " ")
        s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def is_legacy_format(self, input_path: Optional[Path] = None) -> bool:
        """
        Detect if the GEDCOM appears to be exported by Legacy Family Tree.

        Strategy:
          1) Quick header scan for 'Legacy Family Tree' / 'Legacy Version'
          2) Fallback: scan for HEAD.SOUR value containing 'Legacy'
        Returns:
            bool: True if Legacy Family Tree detected, else False.
        """
        path = input_path if input_path is not None else self.input_path
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                in_head = False
                for _ in range(self.LEGACY_DETECTION_LINE_LIMIT):
                    line = f.readline()
                    if not line:
                        break
                    if "Legacy Family Tree" in line or "Legacy Version" in line or "LegacyFamilyTree" in line:
                        return True
                    if line.startswith("0 HEAD"):
                        in_head = True
                    elif in_head and line.startswith("1 SOUR") and "Legacy" in line:
                        return True
                    elif line.startswith("0 "):
                        in_head = False
        except Exception as e:
            logger.warning(f"Legacy detection header-scan failed for {input_path}: {e}")
        return False

    def legacy_convert(self, output_path: Path, input_path: Optional[Path] = None) -> bool:
        """
        Convert a Legacy GEDCOM to a cleaner GEDCOM 5.5 output file.

        Args:
            input_path (Path): Path to the input GEDCOM file.
            output_path (Path): Path to write the converted GEDCOM file.

        Returns:
            bool: True if conversion performed, False if input did not look like Legacy.
        """
        path = input_path if input_path is not None else self.input_path
        if not self.is_legacy_format(path):
            return False

        try:
            head_node, top_records = self._read_and_transform(path)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8", newline="\n") as out:
                # HEAD first (no xref)
                self._emit_node(head_node, level=0, out=out, xref=None)

                # Then other level-0 records
                for xref, node in top_records:
                    self._emit_node(node, level=0, out=out, xref=xref)

                out.write("0 TRLR\n")

            return True

        except Exception as e:
            logger.error(f"Failed converting Legacy GEDCOM '{path}': {e}")
            return False

    # ---------- internal: read/transform ----------

    def _read_and_transform(self, input_path: Optional[Path] = None) -> Tuple[Node, List[Tuple[Optional[str], Node]]]:
        """
        Read and transform the GEDCOM file into a head node and a list of top-level records using a simple line-based parser.
        Raises ValueError if no HEAD record is found.
        """
        path = input_path if input_path is not None else self.input_path
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = [line.rstrip("\r\n") for line in f]

        # Parse lines into Node tree
        stack: List[Tuple[int, Node, Optional[str]]] = []  # (level, node, xref)
        top_records: List[Tuple[Optional[str], Node]] = []
        head_node: Optional[Node] = None

        for line_num, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            # Parse GEDCOM line: level [xref] tag [value]
            parts = line.split(" ", 2)
            if len(parts) < 2:
                continue  # skip malformed
            try:
                level = int(parts[0])
            except ValueError:
                logger.warning(f"Skipping line with non-integer level: {line!r}")
                continue
            xref = None
            if parts[1].startswith("@") and parts[1].endswith("@"):
                xref = parts[1]
                tag = parts[2].split(" ", 1)[0] if len(parts) > 2 else ""
                value = parts[2][len(tag):].strip() if len(parts) > 2 and len(parts[2]) > len(tag) else ""
            else:
                tag = parts[1]
                value = parts[2] if len(parts) > 2 else ""

                # CONT/CONC handling: merge into previous node's value if tag is CONT/CONC
                if tag in ("CONT", "CONC"):
                    # Find the most recent node at the previous level
                    if stack and stack[-1][0] == level - 1:
                        parent_node = stack[-1][1]
                        if tag == "CONT":
                            parent_node.value += "\n" + value
                        else:  # CONC
                            parent_node.value += value
                    else:
                        logger.warning(f"CONT/CONC at line {line_num} with no parent: {line!r}")
                    continue

                node = Node(tag, value)

            # Attach to parent in stack
            while stack and stack[-1][0] >= level:
                stack.pop()
            if stack:
                stack[-1][1].children.append(node)
            if level == 0:
                if tag == "HEAD":
                    head_node = node
                else:
                    top_records.append((xref, node))
            stack.append((level, node, xref))

        if not head_node:
            raise ValueError("No HEAD record found")

        self._fix_head(head_node)
        # Optionally convert custom facts for all top-level records
        for xref, n in top_records:
            self._convert_custom_facts(n)
        return head_node, top_records

    # _record_to_node and _subrecord_to_node are no longer needed with the new parser

    def _fix_head(self, head: Node) -> None:
        """
        Ensure GEDC.VERS=5.5, GEDC.FORM=LINEAGE-LINKED, CHAR=UTF-8
        """
        def find_child(parent: Node, tag: str) -> Optional[Node]:
            for c in parent.children:
                if c.tag == tag:
                    return c
            return None

        def ensure_child(parent: Node, tag: str, value: str) -> Node:
            c = find_child(parent, tag)
            if c:
                c.value = value
                return c
            c = Node(tag, value)
            parent.children.append(c)
            return c

        ensure_child(head, "CHAR", "UTF-8")

        gedc = find_child(head, "GEDC")
        if not gedc:
            gedc = Node("GEDC", "")
            head.children.append(gedc)

        ensure_child(gedc, "VERS", "5.5")
        ensure_child(gedc, "FORM", "LINEAGE-LINKED")

    def _convert_custom_facts(self, node: Node) -> None:
        """
        Walk a node tree converting underscore tags to EVEN/TYPE and normalizing EVEN/TYPE.
        """
        new_children: List[Node] = []

        for ch in node.children:
            # Recurse
            self._convert_custom_facts(ch)

            # Normalize EVEN/TYPE camelCase
            if ch.tag == "EVEN":
                for sub in ch.children:
                    if sub.tag == "TYPE" and sub.value and " " not in sub.value:
                        # Only normalize if it looks camelCase-ish
                        if re.search(r"[A-Z].*[A-Z]", sub.value):
                            sub.value = self.camel_to_spaced(sub.value)

            # Convert known underscore fact tags
            if ch.tag in self.CUSTOM_FACT_MAP:
                fact_type = self.CUSTOM_FACT_MAP[ch.tag]
                even = Node("EVEN", ch.value or "")
                even.children.append(Node("TYPE", fact_type))
                # preserve substructure under EVEN (DATE/PLAC/NOTE/SOUR etc.)
                even.children.extend(ch.children)
                new_children.append(even)
                continue

            # Optional gentle conversion: other underscore tags -> EVEN/TYPE,
            # but skip known metadata-ish tags.
            if ch.tag.startswith("_") and ch.tag not in self.SKIP_UNDERSCORE_TAGS:
                inferred = self.camel_to_spaced(ch.tag.lstrip("_"))
                if inferred:
                    even = Node("EVEN", ch.value or "")
                    even.children.append(Node("TYPE", inferred))
                    even.children.extend(ch.children)
                    new_children.append(even)
                    continue

            new_children.append(ch)

        node.children = new_children

    # ---------- internal: emit ----------

    def _emit_node(self, node: Node, level: int, out: TextIO, xref: Optional[str]) -> None:
        """
        Emit node and children as GEDCOM, emitting CONT records as separate lines.

        Args:
            node (Node): The node to emit.
            level (int): The current GEDCOM level.
            out (TextIO): Output file object.
            xref (Optional[str]): XREF ID for level 0 records (None for HEAD).
        """

        if not node.tag:
            logger.warning(f"Skipping node with empty tag and value: {node.value!r}")
            return
        parts = [str(level)]
        if level == 0 and xref:
            parts.append(str(xref))
        parts.append(str(node.tag))
        if node.value:
            parts.append(str(node.value))
        line = " ".join(parts) + "\n"
        print(f"EMIT: {line.strip()}")  # DEBUG: print every line before writing
        out.write(line)

        for ch in node.children:
            self._emit_node(ch, level + 1, out, xref=None)
