"""Pydantic models describing the shape of our data.

They serve three purposes:
1. Validation  - if a JSON file has a missing/wrong field we get a clear error.
2. Documentation - FastAPI shows these shapes in Swagger UI.
3. Structured output - MCP tools can return them so AI clients see typed fields.
"""

from typing import Literal

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str = Field(description="Product ID (the website handle), e.g. '9-oz-jar'")
    name: str
    product_line: str = Field(description="Candle, Reed Diffuser, Room Spray, Body Lotion, Sample, Bulk Liquid ...")
    collection: str = Field(description="Website collection the product belongs to")
    size: str | None = Field(None, description="Container size, e.g. '9 oz', when stated on the website")
    pack_quantity: int = Field(1, description="Units included in one order of this product")
    pack_unit: str = Field("unit", description="What pack_quantity counts: unit, pcs, gallons ...")
    unit_price: float | None = Field(None, description="Price per single unit / gallon in USD")
    price_min: float = Field(description="Lowest price for one order (pack) in USD, across options")
    price_max: float = Field(description="Highest price for one order (pack) in USD, across options")
    currency: str = "USD"
    prices_as_of: str = Field(description="Date the prices were copied from the website (YYYY-MM-DD)")
    options: dict[str, list[str]] = Field(default_factory=dict, description="Choosable options, e.g. Jar Color")
    description: str = ""
    status: Literal["available", "coming_soon", "unavailable"] = "available"
    url: str
    image_url: str | None = None


class Faq(BaseModel):
    id: str
    category: str
    question: str
    answer: str
    tags: list[str] = []


class Fragrance(BaseModel):
    number: int = Field(description="Fragrance number in the library, e.g. 10 for '#10 Santal'")
    name: str
    notes: list[str] = Field(default_factory=list, description="Scent notes, e.g. ['Leather', 'Sandalwood', 'Amber']")
    notes_text: str = Field("", description="Notes as written on the website")
    categories: list[str] = Field(default_factory=list, description="Scent families, e.g. Woodsy, Floral")
    top_seller: bool = False
    is_new: bool = False
    inspired_by: str | None = Field(None, description="Well-known scent this fragrance is inspired by, if stated")
    remarks: str | None = None
    url: str


class DocumentMatch(BaseModel):
    filename: str = Field(description="Document the passage comes from, e.g. product_catalogue.pdf")
    page: int | None = Field(None, description="PDF page number (1-based); None for TXT files")
    snippet: str = Field(description="The matching passage of text")
    score: int = Field(description="Relevance score; higher is better")


class Contact(BaseModel):
    email: str
    phone: str | None = None
    other_emails: dict[str, str] = Field(default_factory=dict, description="Purpose -> email, e.g. design")
    address: str | None = None
    business_hours: str | None = None
    contact_page: str | None = None


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
    industries_served: list[str] = []
    services: list[str] = []
    standard_lead_time: str | None = None
    note: str | None = None
