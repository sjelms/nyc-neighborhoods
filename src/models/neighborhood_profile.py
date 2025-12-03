from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import date, datetime

class KeyDetails(BaseModel):
    what_to_expect: str = Field(..., description="A description of the general vibe and characteristics.")
    unexpected_appeal: str = Field(..., description="Hidden gems or surprising aspects of the neighborhood.")
    the_market: str = Field(..., description="A summary of the local real estate market (e.g., housing types, price points).")

class Boundaries(BaseModel):
    east_to_west: str = Field(..., description="Description of the east-west boundaries.")
    north_to_south: str = Field(..., description="Description of the north-to-south boundaries.")
    adjacent_neighborhoods: List[str] = Field(..., description="A list of neighboring areas.")

class NeighborhoodFacts(BaseModel):
    population: str = Field(..., description="Total population count.")
    population_density: str = Field(..., description="Population per square mile/kilometer.")
    area: str = Field(..., description="Total area of the neighborhood.")
    boundaries: Boundaries
    zip_codes: List[str] = Field(..., description="A list of ZIP codes covering the neighborhood.")

class TransitAccessibility(BaseModel):
    nearest_subways: List[str] = Field(..., description="A list of subway lines serving the area.")
    major_stations: List[str] = Field(..., description="A list of key subway/train stations.")
    bus_routes: List[str] = Field(..., description="A list of bus routes serving the area.")
    rail_freight_other: List[str] = Field(..., description="Other transit like LIRR, Metro-North, or freight lines.")
    highways_major_roads: List[str] = Field(..., description="Major vehicular routes.")

class CommuteTime(BaseModel):
    destination: str = Field(..., description="The name of the commute destination (e.g., 'Midtown Manhattan').")
    subway: str = Field(..., description="Estimated commute time via subway.")
    drive: str = Field(..., description="Estimated commute time via car.")

class NeighborhoodProfile(BaseModel):
    version: str = Field(..., description="Version of the profile document.")
    ratified_date: date = Field(..., description="Date the profile was initially created (ISO format: YYYY-MM-DD).")
    last_amended_date: date = Field(..., description="Date the profile was last updated (ISO format: YYYY-MM-DD).")
    neighborhood_name: str = Field(..., description="The name of the neighborhood.")
    borough: str = Field(..., description="The borough the neighborhood belongs to.") # Added borough field
    summary: str = Field(..., description="A short, one-paragraph summary of the neighborhood.")
    key_details: KeyDetails
    around_the_block: str = Field(..., description="A 1-2 paragraph narrative about the neighborhood.")
    neighborhood_facts: NeighborhoodFacts
    transit_accessibility: TransitAccessibility
    commute_times: Optional[List[CommuteTime]] = Field(None, description="(Optional) A list of commute times to various destinations.")
    sources: List[str] = Field(..., description="A list of source URLs used to generate the profile.")
    generation_date: datetime = Field(..., description="The timestamp when the profile was generated (ISO 8601 format).")
    warnings: List[str] = Field(..., description="A list of any warnings encountered during data scraping or generation.")

    @property
    def unique_id(self) -> str:
        """Generates a unique identifier for the neighborhood profile."""
        return f"{self.neighborhood_name.lower().replace(' ', '-')}-{self.borough.lower().replace(' ', '-')}"