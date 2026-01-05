
from pathlib import Path
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class GedcomFix:
    LINE_RE = re.compile(
        r'^(\d+)\s+(?:@[^@]+@\s+)?([A-Z0-9_]+)(.*)$'
    )
    
    def __init__(self, input_path: Path):
        """
        Initialize with the path to the GEDCOM file to be fixed.

        Args:
            input_path (Path): Path to the input GEDCOM file.
        """
        self.input_path = input_path

    def fix_gedcom_levels(self, output_path: Path) -> bool:
        """
        Fix common GEDCOM issues and write to output path.

        Args:
            output_path (Path): Path to write the fixed GEDCOM file.
        Returns:
            bool: Whether the GEDCOM file was changed.
        """
        if self.input_path is None:
            return None
        changed = self.fix_gedcom_conc_cont_levels(self.input_path, output_path)
        return changed
    
    def fix_gedcom_conc_cont_levels(self, input_path: Path, temp_path: Path) -> bool:
        """
        Fixes GEDCOM continuity and structure levels.
        These types of GEDCOM issues have been seen from Family Tree Maker exports.
        If not fixed, they can cause failure to parse the GEDCOM file correctly.
        """

        cont_level = None
        changed = False

        try:
            with open(input_path, 'r', encoding='utf-8', newline='', errors="replace") as infile, \
                open(temp_path, 'w', encoding='utf-8', newline='') as outfile:
                for raw in infile:
                    line = raw.rstrip('\r\n')
                    m = self.LINE_RE.match(line)
                    if not m:
                        outfile.write(raw)
                        continue

                    level_s, tag, rest = m.groups()
                    level = int(level_s)

                    if tag in ('CONC', 'CONT'):
                        fixed_level = cont_level if cont_level is not None else level
                        outfile.write(f"{fixed_level} {tag}{rest}\n")
                        if fixed_level != level:
                            changed = True
                    else:
                        cont_level = level + 1
                        outfile.write(raw)
        except IOError as e:
            logger.error(f"Failed to fix GEDCOM file {input_path}: {e}")
        return changed
    