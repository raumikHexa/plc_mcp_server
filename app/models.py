"""Pydantic models describing the shape of our data.

They serve three purposes:
1. Validation  - if a JSON file has a missing/wrong field we get a clear error.
2. Documentation - FastAPI shows these shapes in Swagger UI.
3. Structured output - MCP tools can return them so AI clients see typed fields.
"""

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str = Field(description="Unique product ID, e.g. PND-001")
    name: str
    category: str
    materials: list[str]
    finishes: list[str] = []
    dimensions: dict[str, float] = Field(description="Sizes in millimetres, weight in kg")
    description: str
    specifications: dict[str, str]
    suitable_for: list[str] = []


class Faq(BaseModel):
    id: str
    category: str
    question: str
    answer: str
    tags: list[str] = []


class Contact(BaseModel):
    email: str
    support_email: str | None = None
    projects_email: str | None = None
    phone: str | None = None
    address: str | None = None
    business_hours: str | None = None


class Company(BaseModel):
    name: str
    tagline: str | None = None
    description: str
    industry: str
    founded: int | None = None
    headquarters: str | None = None
    website: str
    contact: Contact
    product_categories: list[str]
    services: list[str] = []
    note: str | None = None
