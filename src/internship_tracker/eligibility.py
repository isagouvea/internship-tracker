from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date

from .adapters.base import DiscoveredJob


@dataclass
class Assessment:
    classification: str
    confidence: int
    matching: list[str]
    conflicts: list[str]
    missing: list[str]
    explanation: str

    def serialized(self) -> tuple[str, str, str]:
        return json.dumps(self.matching), json.dumps(self.conflicts), json.dumps(self.missing)


def _known(value) -> bool:
    return value not in (None, "", "unknown", "Unknown")


def assess(job: DiscoveredJob, profile: dict, today: date | None = None) -> Assessment:
    today = today or date.today()
    text = " ".join(filter(None, [job.required_qualifications, job.education_requirement,
                                   job.required_class_standing, job.graduation_date_range,
                                   job.work_authorization_requirement, job.sponsorship_information])).lower()
    matches, conflicts, missing = [], [], []
    school = str(profile.get("academic_status", "")).lower()
    if re.search(r"four[- ]year (college|university|institution)", text):
        if "community-college" in school or "community college" in school:
            conflicts.append("Posting explicitly requires enrollment at a four-year institution")
    elif "currently enrolled" in text or "undergraduate" in text:
        matches.append("Candidate reports current undergraduate enrollment")

    if "bachelor" in text and re.search(r"(completed|required|must have|degree required).{0,30}bachelor|bachelor.{0,30}(completed|required|must have)", text):
        conflicts.append("Posting requires a completed bachelor’s degree before the internship")

    if job.required_major:
        major = str(profile.get("intended_major", "")).lower()
        if major and major in job.required_major.lower():
            matches.append(f"Intended major matches requirement: {job.required_major}")
        elif re.search(r"marketing|business|communications|related", job.required_major, re.I) and major == "marketing":
            matches.append("Marketing intended major fits the listed major family")
        else:
            conflicts.append(f"Intended major may not match required major: {job.required_major}")

    if job.minimum_gpa is not None:
        gpa = profile.get("gpa")
        if not isinstance(gpa, (int, float)):
            missing.append("Current GPA")
        elif float(gpa) >= job.minimum_gpa:
            matches.append(f"GPA meets the {job.minimum_gpa:g} minimum")
        else:
            conflicts.append(f"GPA is below the {job.minimum_gpa:g} minimum")

    if job.required_class_standing:
        standing = profile.get("current_class_standing")
        if not _known(standing):
            missing.append("Current class standing")
        elif str(standing).lower() in job.required_class_standing.lower():
            matches.append("Class standing matches")
        else:
            missing.append(f"Confirm class-standing fit: {job.required_class_standing}")

    if job.graduation_date_range:
        grad = profile.get("expected_bachelors_graduation")
        if not _known(grad):
            missing.append("Expected bachelor’s graduation date")
        elif str(grad).lower() in job.graduation_date_range.lower():
            matches.append("Expected graduation date appears in required range")
        else:
            missing.append(f"Confirm graduation-date fit: {job.graduation_date_range}")

    if re.search(r"(authorized|authorization).{0,50}(united states|u\.s\.)", text):
        auth = str(profile.get("work_authorization", "")).lower()
        if "citizen" in auth or "authorized" in auth:
            matches.append("Candidate reports U.S. work authorization")
        elif not _known(profile.get("work_authorization")):
            missing.append("U.S. work authorization")
        else:
            conflicts.append("Reported work authorization may not meet the requirement")

    if conflicts:
        classification, confidence = "Likely not eligible", min(95, 72 + len(conflicts) * 8)
    elif not text.strip():
        classification, confidence = "Unable to determine", 25
        missing.append("Detailed required qualifications")
    elif missing:
        classification, confidence = "Possibly eligible", max(45, 70 - len(missing) * 5)
    elif matches:
        classification, confidence = "Likely eligible", min(92, 68 + len(matches) * 6)
    else:
        classification, confidence = "Unable to determine", 35
        missing.append("Eligibility-specific requirements")

    parts = []
    if matches: parts.append("Matches: " + "; ".join(matches) + ".")
    if conflicts: parts.append("Conflicts: " + "; ".join(conflicts) + ".")
    if missing: parts.append("Needs confirmation: " + "; ".join(dict.fromkeys(missing)) + ".")
    parts.append("Preferred qualifications are not treated as mandatory.")
    return Assessment(classification, confidence, matches, conflicts, list(dict.fromkeys(missing)), " ".join(parts))

