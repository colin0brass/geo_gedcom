"""
gedcom_date.py - Date normalization utilities for GEDCOM processing.

Provides the GedcomDate class for parsing, normalizing, and converting GEDCOM date formats using ged4py.
Supports:
    - Normalization of ged4py DateValue to GregorianDate or string
    - Parsing of date phrases, ranges, ordinals, and free-text
    - Extraction of year, month, and day information
    - Range simplification policies ('first', 'last', 'none')

Author: @colin0brass
Last updated: 2025-12-06
"""


import re
from typing import Optional, Union
from ged4py.date import DateValue
from ged4py.calendar import GregorianDate
import logging
from functools import total_ordering

logger = logging.getLogger(__name__)

@total_ordering
class GedcomDate:
    """
    Utility class for normalizing and parsing GEDCOM date values.

    Wraps ged4py DateValue, GregorianDate, or string date representations and provides normalization to GregorianDate or string for various GEDCOM date formats.
    Handles ranges, phrases, and ordinal/fallback date parsing from free-text. Uses __slots__ for memory optimization.

    Attributes:
        original: The original date value (DateValue, GregorianDate, str, or GedcomDate).
        date: The parsed date value (DateValue, GregorianDate, str, or None).
        simplify_range_policy: Policy for range simplification ('first', 'last', or 'none').
    """
    __slots__ = [
        'original',
        'date',
        'simplify_range_policy'
    ]

    def __init__(self, date: Union[DateValue, str, "GedcomDate", None], simplify_range_policy: str = 'first'):
        """
        Initialize a GedcomDate instance.
        Args:
            date: The original date value (DateValue, GregorianDate, str, GedcomDate, or None).
            simplify_range_policy: Policy for range simplification ('first', 'last', or 'none').
        """
        self.original: Union[DateValue, str, "GedcomDate", None] = date
        self.date = self._parse(date)
        self.simplify_range_policy: str = simplify_range_policy

    def parse_str_year(self, year_str: str) -> Optional[int]:
        """
        Parse a year string into an integer.

        Args:
            year_str (str): The year string to parse.

        Returns:
            int or None: The parsed year as an integer, or None if parsing fails.
        """
        match = re.search(r'(-?\d{3,4})', year_str)
        if match:
            return int(match.group(1))
        else:
            logger.warning('GedcomDate: parse_str_year: unable to parse year string: "%s"', year_str)
            return None
        
    def looks_like_year(self, num: int, min_year: int = 1000, max_year: int = 2100) -> bool:
        """Return True if num is plausibly a year."""
        return isinstance(num, int) and min_year <= num <= max_year

    def _parse(self, date: Union[DateValue, str, "GedcomDate", None]) -> Union[DateValue, str, None]:
        """
        Parse the input date into a DateValue, or return the string as is.
        Handles BCE/BC and calendar prefixes for GEDCOM v7.
        """
        if isinstance(date, GedcomDate):
            return date.date
        elif isinstance(date, DateValue) or date is None:
            return date
        elif isinstance(date, str):
            # Preprocess for BCE/BC and calendar prefixes
            s = date.strip()
            calendar = None
            # Extract calendar prefix if present
            calendar_match = re.match(r'^(JULIAN|GREGORIAN|FRENCH_R|HEBREW)\s+', s, re.I)
            if calendar_match:
                calendar = calendar_match.group(1).upper()
                s = s[calendar_match.end():].strip()
            # Handle BCE/BC (convert to negative year)
            # Replace each BCE/BC year with its own negative value
            def bce_repl(match):
                return str(-int(match.group(1)))
            s = re.sub(r'(\d{1,4})\s*(BCE|BC)', bce_repl, s, flags=re.I)
            # Re-add calendar prefix if present (for fallback)
            s_for_parse = s
            if calendar:
                # Only pass through if Gregorian/Julian, fallback for others
                if calendar in ("GREGORIAN", "JULIAN"):
                    s_for_parse = f"{calendar} {s}"
                else:
                    # For unsupported calendars, just return the string
                    return f"{calendar} {s}"
            try:
                return DateValue.parse(s_for_parse)
            except Exception as e:
                logger.warning(f"Failed to parse date string '{date}' (preprocessed: '{s_for_parse}'): {e}")
                # If the string looks like a range phrase, try phrase parsing for BCE/BC support
                if s_for_parse.strip().upper().startswith('BET '):
                    phrase_result = self._date_from_phrase(s_for_parse)
                    if phrase_result is not None:
                        return phrase_result
                return date
        elif isinstance(date, int):
            if self.looks_like_year(date):
                return DateValue.parse(str(date))
            else:
                logger.warning(f"GedcomDate: _parse: integer '{date}' does not look like a valid year")
                return None
        else:
            raise TypeError(f"Unsupported date type: {type(date)}")

    def update(self, date: Optional[Union[DateValue, str, "GedcomDate", None]], simplify_range_policy: Optional[str] = None) -> None:
        """
        Update the GedcomDate instance with a new date value and/or range policy.

        Args:
            date: The new date value (DateValue, str, GedcomDate, or None).
            simplify_range_policy: Optional new range simplification policy.
        """
        if date is not None:
            self.original = date
        if simplify_range_policy is not None:
            self.simplify_range_policy = simplify_range_policy
        self.date = self._parse(self.original)

    @property
    def resolved(self) -> Optional[Union[GregorianDate, str]]:
        """
        Resolve the date to a GregorianDate or string.

        For ranges, returns first or last date based on simplify_range_policy.
        For phrases, parses and resolves the phrase.

        Returns:
            GregorianDate, str, tuple, or None: The resolved date value.
        """
        if not self.date:
            return None
        kind = getattr(self.date, 'kind', None)
        if kind is None:
            # If the date is a string and looks like a range phrase, try phrase parsing
            if isinstance(self.date, str) and self.simplify_range_policy == 'none':
                phrase_result = self._date_from_phrase()
                if isinstance(phrase_result, tuple):
                    return phrase_result
            return None
        if kind.name in ("RANGE", "PERIOD"):
            date1 = getattr(self.date, 'date1', None)
            date2 = getattr(self.date, 'date2', None)
            if self.simplify_range_policy == "last":
                logger.info(f"Simplifying date range {self.date} to last date: {date2}")
                return date2
            elif self.simplify_range_policy == "first":
                logger.info(f"Simplifying date range {self.date} to first date: {date1}")
                return date1
            else: # none
                return (date1, date2)
        elif kind.name == "PHRASE":
            return self._date_from_phrase()
        else: # SIMPLE, ABOUT, AFTER, BEFORE, etc.
            if isinstance(self.date, str):
                # If the fallback phrase returns a tuple, return it (for BCE ranges)
                fallback = self._parse_fallback_phrase(self.date)
                if self.simplify_range_policy == 'none' and isinstance(fallback, tuple):
                    return fallback
                return fallback
            else:
                return self.date.date

    @property
    def single(self) -> Optional[Union[GregorianDate, str]]:
        """
        Return a single date representation.

        For ranges, returns first or last date based on simplify_range_policy.
        For phrases, parses and resolves the phrase.

        Returns:
            GregorianDate, str, or None: The single date value.
        """
        date = self.resolved
        if isinstance(date, tuple):
            if self.simplify_range_policy == "last":
                return date[1]
            elif self.simplify_range_policy == "first":
                return date[0]
            else:
                return None
        return date

    @property
    def year_num(self) -> Optional[int]:
        """
        Return the year as an integer, if possible.

        For ranges, returns first or last year based on simplify_range_policy.
        For phrases, attempts to extract year from phrase.

        Returns:
            int or None: The year value, or None if not found.
        """
        single_date = self.single
        if hasattr(single_date, 'year'):
            year = getattr(single_date, 'year', None)
            return int(year) if year is not None else None
        else:
            match = re.search(r'(-?\d{3,4})', str(single_date))
            if match:
                return int(match.group(1))
            else:
                logger.warning('GedcomDate: year_num: unable to parse single date: "%s"', single_date)
                return None

    @property
    def year_str(self) -> Optional[str]:
        """
        Return the year as a string, if possible.

        Returns:
            str or None: The year as a string, or None if not found.
        """
        if isinstance(self.date, str):
            return self.date
        else:
            kind = getattr(self.date, 'kind', None)
            date_single = self.single
            if kind:
                if hasattr(date_single, 'year_str'):
                    return date_single.year_str
                elif isinstance(date_single, str):
                    return self.parse_str_year(date_single)
                else:
                    return None
            else:
                return None

    def _date_from_phrase(self, phrase: str = None) -> Optional[Union[GregorianDate, str, tuple]]:
        """
        Extract and normalize a date from a GEDCOM date phrase.

        Returns a GregorianDate if possible, else the best string representation.
        Supports ranges like 'BET JUL AND SEP 1913' and single dates.
        For ranges, returns a tuple (start, end) of GregorianDate objects.

        Returns:
            GregorianDate, str, tuple, or None: The normalized date value.
        """
        if phrase is None:
            phrase = getattr(self.date, 'phrase', None)
        if not phrase:
            logger.warning('GedcomDate: _date_from_phrase: no phrase available on date.value')
            return None
        if not isinstance(phrase, str):
            return None

        result = self._parse_range_phrase(phrase)
        if result is not None:
            return result

        result = self._parse_ordinal_phrase(phrase)
        if result is not None:
            return result

        result = self._parse_fallback_phrase(phrase)
        return result

    def _parse_range_phrase(self, phrase: str) -> Optional[tuple]:
        """
        Parse a GEDCOM range phrase (e.g., 'BET JUL AND SEP 1913', 'BET 50 BCE AND 44 BCE', 'BET 1 JAN 44 BCE AND 15 MAR 44 BCE').
        """
        s = phrase.strip()
        # Remove calendar prefix if present
        calendar_match = re.match(r'^(JULIAN|GREGORIAN|FRENCH_R|HEBREW)\s+', s, re.I)
        if calendar_match:
            s = s[calendar_match.end():].strip()
        # Try full date range: 'BET 1 JAN 44 BCE AND 15 MAR 44 BCE'
        full_range_re = re.compile(r'^BET\s+(\d{1,2})\s+([A-Za-z]{3,9})\s+(-?\d{1,4}|\d{1,4}\s*(?:BCE|BC))\s+AND\s+(\d{1,2})\s+([A-Za-z]{3,9})\s+(-?\d{1,4}|\d{1,4}\s*(?:BCE|BC))$', re.I)
        m = full_range_re.match(s)
        if m:
            d1, m1, y1, d2, m2, y2 = m.groups()
            def parse_y(y):
                bce = re.search(r'(\d{1,4})\s*(BCE|BC)', y, re.I)
                return -int(bce.group(1)) if bce else int(y)
            start = GregorianDate(year=parse_y(y1), month=m1.upper()[:3], day=int(d1))
            end = GregorianDate(year=parse_y(y2), month=m2.upper()[:3], day=int(d2))
            return (start, end)
        # Try month range: 'BET JUL AND SEP 1913'
        month_range_re = re.compile(r'^BET\s+([A-Za-z]{3,9})\s+AND\s+([A-Za-z]{3,9})\s+(-?\d{1,4}|\d{1,4}\s*(?:BCE|BC))$', re.I)
        m = month_range_re.match(s)
        if m:
            m1, m2, y = m.groups()
            bce = re.search(r'(\d{1,4})\s*(BCE|BC)', y, re.I)
            year = -int(bce.group(1)) if bce else int(y)
            start = GregorianDate(year=year, month=m1.upper()[:3])
            end = GregorianDate(year=year, month=m2.upper()[:3])
            return (start, end)
        # Try year range: 'BET 50 BCE AND 44 BCE' or 'BET -50 AND -44'
        year_range_re = re.compile(r'^BET\s+(-?\d{1,4})\s*(BCE|BC)?\s+AND\s+(-?\d{1,4})\s*(BCE|BC)?$', re.I)
        m = year_range_re.match(s)
        if m:
            y1, bce1, y2, bce2 = m.groups()
            # If BCE/BC present, force negative, else use as-is (already negative if BCE replaced)
            if bce1 or bce2:
                y1 = -int(y1.lstrip('-'))
                y2 = -int(y2.lstrip('-'))
            else:
                y1 = int(y1)
                y2 = int(y2)
            return (GregorianDate(year=y1), GregorianDate(year=y2))
        return None

    def _parse_ordinal_phrase(self, phrase: str) -> Optional[GregorianDate]:
        """
        Parse an ordinal date phrase (e.g., '15 JUL 1913', '15 MAR 44 BCE', 'JULIAN 1 JAN 44 BCE') and return a GregorianDate object.
        """
        # Remove calendar prefix if present
        s = phrase.strip()
        calendar_match = re.match(r'^(JULIAN|GREGORIAN|FRENCH_R|HEBREW)\s+', s, re.I)
        if calendar_match:
            s = s[calendar_match.end():].strip()
        # Match day, month, year (year can be negative or BCE/BC)
        ordinal_date_re = re.compile(r'^(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\s+(-?\d{1,4}|\d{1,4}\s*(?:BCE|BC))$', re.I)
        m = ordinal_date_re.match(s)
        if m:
            day, month, year = m.groups()
            # Handle BCE/BC
            bce = re.search(r'(\d{1,4})\s*(BCE|BC)', year, re.I)
            if bce:
                y = -int(bce.group(1))
            else:
                y = int(year)
            return GregorianDate(year=y, month=month.upper()[:3], day=int(day))
        return None

    def _parse_fallback_phrase(self, phrase: str) -> Optional[Union[GregorianDate, str]]:
        """
        Parse a fallback date phrase and return a GregorianDate or string if possible.
        Handles BCE/BC, calendar prefixes, and partial dates.
        """
        if not phrase or not isinstance(phrase, str):
            return None
        s = phrase.strip()
        # Remove calendar prefix for fallback parse
        calendar_match = re.match(r'^(JULIAN|GREGORIAN|FRENCH_R|HEBREW)\s+', s, re.I)
        if calendar_match:
            calendar = calendar_match.group(1).upper()
            s = s[calendar_match.end():].strip()
            if calendar not in ("GREGORIAN", "JULIAN"):
                return f"{calendar} {s}"
        # Handle BCE/BC (convert to negative year)
        bce_match = re.search(r'(\d{1,4})\s*(BCE|BC)', s, re.I)
        year = None
        if bce_match:
            year = -int(bce_match.group(1))
            s = re.sub(r'(\d{1,4})\s*(BCE|BC)', str(year), s, flags=re.I)
        # Now try to extract year, month, day
        YEAR_RE = re.compile(r'(?<!\d)(-?\d{1,4})(?!\d)')
        MONTH_RE = re.compile(r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JUNE|JULY|SEPTEMBER|OCTOBER|DECEMBER|AUGUST|NOVEMBER|MARCH|FEBRUARY|MAY|APRIL)', re.I)
        DAY_RE = re.compile(r'(?<!\d)(\d{1,2})(?=\s+[A-Z]{3,9})')

        year_match = YEAR_RE.search(s)
        if year is None and year_match:
            year = int(year_match.group(1))
        month_match = MONTH_RE.search(s)
        month = month_match.group(1) if month_match else None
        month_str = month.upper()[:3] if month else None
        day_match = DAY_RE.search(s)
        day = int(day_match.group(1)) if day_match else None
        if year is not None:
            return GregorianDate(year=year, month=month_str, day=day)
        if month or day:
            parts = []
            if day:
                parts.append(str(day))
            if month:
                parts.append(month)
            return " ".join(parts)
        return phrase

    def __eq__(self, other):
        if not isinstance(other, GedcomDate):
            return NotImplemented
        a = self.year_num
        b = other.year_num
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        return a == b

    def __lt__(self, other):
        if not isinstance(other, GedcomDate):
            return NotImplemented
        a = self.year_num
        b = other.year_num
        if a is None and b is None:
            return False  # or return NotImplemented
        if a is None:
            return False  # None is considered greater (sorts last)
        if b is None:
            return True   # Any int is less than None (None sorts last)
        return a < b

    def __hash__(self):
        # Adjust attributes as appropriate for your class
        return hash((self.year_num, getattr(self, 'month_num', None), getattr(self, 'day_num', None)))
