from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Locator(BaseModel):
    css: Optional[str] = None
    xpath: Optional[str] = None
    aria: Optional[str] = None
    data_testid: Optional[str] = None
    nth: Optional[str] = None


class FormField(BaseModel):
    field_id: str
    name: Optional[str] = None
    label: Optional[str] = None
    placeholder: Optional[str] = None
    type: str
    required: bool = False
    options: List[str] = Field(default_factory=list)
    locators: Locator = Field(default_factory=Locator)
    meta: Dict[str, Any] = Field(default_factory=dict)


class FormSection(BaseModel):
    title: Optional[str] = None
    fields: List[FormField] = Field(default_factory=list)


class ATSInfo(BaseModel):
    identified_ATS: Optional[str] = None
    signals: Dict[str, Any] = Field(default_factory=dict)


class Validity(BaseModel):
    is_valid_job_application_form: bool
    confidence: float
    meta: Dict[str, Any] = Field(default_factory=dict)


class FormSchema(BaseModel):
    url: Optional[str] = None
    ats: Optional[str] = None
    sections: List[FormSection] = Field(default_factory=list)
    validity: Validity


