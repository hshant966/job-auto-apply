"""Data models for JobAutoApply."""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class Gender(str, enum.Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class Category(str, enum.Enum):
    GENERAL = "General"
    OBC = "OBC"
    SC = "SC"
    ST = "ST"
    EWS = "EWS"


class ApplicationStatus(str, enum.Enum):
    DISCOVERED = "discovered"
    DRAFT = "draft"
    APPLYING = "applying"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SELECTED = "selected"
    FAILED = "failed"


class PersonalInfo(BaseModel):
    full_name: str = ""
    dob: date = Field(default_factory=lambda: date(2000, 1, 1))
    gender: Gender = Gender.MALE
    father_name: str = ""
    mother_name: str = ""
    aadhaar_last4: str = Field(default="", max_length=4)
    pan_number: str = ""
    nationality: str = "Indian"
    marital_status: str = ""

    @field_validator("aadhaar_last4")
    @classmethod
    def validate_aadhaar4(cls, v: str) -> str:
        if v and (not v.isdigit() or len(v) != 4):
            raise ValueError("aadhaar_last4 must be exactly 4 digits")
        return v


class Address(BaseModel):
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    country: str = "India"


class ContactInfo(BaseModel):
    email: str = ""
    phone: str = ""
    alternate_phone: str = ""
    address: Address = Field(default_factory=Address)


class Education(BaseModel):
    degree: str = ""
    university: str = ""
    institution: str = ""
    year_of_passing: int = 0
    percentage: float = 0.0
    specialization: str = ""


class Experience(BaseModel):
    organisation: str = ""
    designation: str = ""
    from_date: date = Field(default_factory=date.today)
    to_date: Optional[date] = None
    is_current: bool = False
    description: str = ""


class Documents(BaseModel):
    photo_path: str = ""
    signature_path: str = ""
    certificates: list[str] = Field(default_factory=list)
    resume_path: str = ""
    caste_certificate_path: str = ""
    ews_certificate_path: str = ""
    pwd_certificate_path: str = ""


class SalaryRange(BaseModel):
    min_salary: int = 0
    max_salary: int = 0
    currency: str = "INR"


class JobPreferences(BaseModel):
    desired_roles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    salary_range: SalaryRange = Field(default_factory=SalaryRange)
    remote_ok: bool = False
    govt_only: bool = False


class UserProfile(BaseModel):
    personal: PersonalInfo = Field(default_factory=PersonalInfo)
    contact: ContactInfo = Field(default_factory=ContactInfo)
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    category: Category = Category.GENERAL
    documents: Documents = Field(default_factory=Documents)
    skills: list[str] = Field(default_factory=list)
    preferences: JobPreferences = Field(default_factory=JobPreferences)

    def completeness(self) -> dict[str, bool]:
        return {
            "personal": bool(self.personal.full_name),
            "contact": bool(self.contact.email or self.contact.phone),
            "education": len(self.education) > 0,
            "experience": len(self.experience) > 0,
            "documents": bool(self.documents.photo_path),
            "skills": len(self.skills) > 0,
            "preferences": bool(self.preferences.desired_roles),
        }

    def completeness_pct(self) -> float:
        checks = self.completeness()
        if not checks:
            return 0.0
        return round(sum(checks.values()) / len(checks) * 100, 1)


class Job(BaseModel):
    id: Optional[int] = None
    title: str = ""
    portal: str = ""
    url: str = ""
    department: str = ""
    qualification: str = ""
    last_date: Optional[date] = None
    salary: str = ""
    location: str = ""
    category_eligible: list[Category] = Field(default_factory=list)
    description: str = ""
    discovered_at: datetime = Field(default_factory=datetime.now)
    match_score: int = 0
    screening_questions: list[str] = Field(default_factory=list)

    @property
    def is_expired(self) -> bool:
        if self.last_date is None:
            return False
        return date.today() > self.last_date


class Application(BaseModel):
    id: Optional[int] = None
    job_id: int = 0
    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    applied_date: Optional[datetime] = None
    reference_id: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    job: Optional[Job] = None
