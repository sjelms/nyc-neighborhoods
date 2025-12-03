# Data Model: Neighborhood Profile

**Date**: 2025-12-02

This document outlines the data structures used to represent a neighborhood profile, which will be serialized into the final Markdown output.

## Main Entity: `NeighborhoodProfile`

This is the top-level entity representing a single neighborhood's profile.

| Attribute | Type | Description |
|---|---|---|
| `version` | string | Version of the profile document. |
| `ratified_date` | string | Date the profile was initially created (ISO format: YYYY-MM-DD). |
| `last_amended_date` | string | Date the profile was last updated (ISO format: YYYY-MM-DD). |
| `neighborhood_name` | string | The name of the neighborhood. |
| `summary` | string | A short, one-paragraph summary of the neighborhood. |
| `key_details` | `KeyDetails` | A nested object containing key descriptive points. |
| `around_the_block` | string | A 1-2 paragraph narrative about the neighborhood. |
| `neighborhood_facts` | `NeighborhoodFacts` | A nested object containing factual data about the neighborhood. |
| `transit_accessibility` | `TransitAccessibility` | A nested object describing transit options. |
| `commute_times` | List[`CommuteTime`] | (Optional) A list of commute times to various destinations. |
| `sources` | List[string] | A list of source URLs used to generate the profile. |
| `generation_date` | datetime | The timestamp when the profile was generated (ISO 8601 format). |
| `warnings` | List[string] | A list of any warnings encountered during data scraping or generation. |

## Nested Entity: `KeyDetails`

| Attribute | Type | Description |
|---|---|---|
| `what_to_expect` | string | A description of the general vibe and characteristics. |
| `unexpected_appeal` | string | Hidden gems or surprising aspects of the neighborhood. |
| `the_market` | string | A summary of the local real estate market (e.g., housing types, price points). |

## Nested Entity: `NeighborhoodFacts`

| Attribute | Type | Description |
|---|---|---|
| `population` | integer | Total population count. |
| `population_density` | number | Population per square mile/kilometer. |
| `area` | number | Total area of the neighborhood. |
| `boundaries` | `Boundaries` | A nested object describing the neighborhood's geographical boundaries. |
| `zip_codes` | List[string] | A list of ZIP codes covering the neighborhood. |

## Nested Entity: `Boundaries`

| Attribute | Type | Description |
|---|---|---|
| `east_to_west` | string | Description of the east-west boundaries. |
| `north_to_south` | string | Description of the north-south boundaries. |
| `adjacent_neighborhoods` | List[string] | A list of neighboring areas. |

## Nested Entity: `TransitAccessibility`

| Attribute | Type | Description |
|---|---|---|
| `nearest_subways` | List[string] | A list of subway lines serving the area. |
| `major_stations` | List[string] | A list of key subway/train stations. |
| `bus_routes` | List[string] | A list of bus routes serving the area. |
| `rail_freight_other` | List[string] | Other transit like LIRR, Metro-North, or freight lines. |
| `highways_major_roads`| List[string] | Major vehicular routes. |

## Nested Entity: `CommuteTime` (Optional)

| Attribute | Type | Description |
|---|---|---|
| `destination` | string | The name of the commute destination (e.g., "Midtown Manhattan"). |
| `subway` | string | Estimated commute time via subway. |
| `drive` | string | Estimated commute time via car. |
