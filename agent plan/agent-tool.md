# Agent Builder Implementation Plan — Automated Neighborhood Profile Generator

## 1. Overview

Use OpenAI Agent Builder to create an agent that:
- Accepts a **neighborhood name** as input
- Retrieves information from **Wikipedia** and **NYC Open Data**  
- Extracts demographic, transit, boundary, and historical information
- Writes descriptive sections using LLM reasoning (e.g., "Around the Block")
- Outputs a **fully formatted Markdown file** following your template
- Includes a metadata header:
  **Version** | **Ratified** | **Last Amended**

---

## 2. Data Sources

### Primary:
- **Wikipedia neighborhood page**
  - Agent will read the page & extract:
    - Summary paragraph
    - Demographics
    - Boundaries
    - ZIP codes
    - Transit (subway, bus, rail, roads)

### Secondary:
- **NYC Open Data**
  - For:
    - Community district number  
    - Optional zoning or land-use datasets  
  - Agent can call NYC Open Data API endpoints directly when needed.

---

## 3. Input Format

Neighborhood list provided as:
- `.csv` **or**
- `.json` **or**
- A simple text list inside the Agent Builder UI

CSV recommended:
```
neighborhood,borough
Maspeth,Queens
Sunset Park,Brooklyn
Williamsburg,Brooklyn
...
```

---

## 4. Output Format

Each neighborhood becomes its own `.md` file.

Template:

~~~markdown
**Version**: [VERSION] | **Ratified**: [RATIFIED_DATE] | **Last Amended**: [LAST_AMENDED_DATE]

## [Neighborhood Name]

[Short Summary Paragraph]

---

### Key Details
- WHAT TO EXPECT:
- UNEXPECTED APPEAL:
- THE MARKET:

---

### Around the Block

[A 1–2 paragraph narrative]

---

### Neighborhood Facts
- Population:
- Population Density:
- Area:
- ZIP Codes:
- Boundaries:
- Adjacent Neighborhoods:
- Community District:

---

### Transit & Accessibility

#### Nearest Subways:
[bullet list]

#### Major Stations:
[bullet list]

#### Bus Routes:
[bullet list]

#### Rail / Freight Access:
[bullet list]

#### Highways & Major Roads:
[bullet list]

---

### Commute Times
| Destination | Subway | Drive |
|-------------|--------|-------|
| Midtown | … | … |
| Grand Central | … | … |
| Wall Street | … | … |
~~~

---

## 5. Agent Configuration (inside Agent Builder)

### 5.1 Tools to Enable
- **Web Browser Tool**
  - Allows the agent to open Wikipedia, NYC Open Data, and read tables/pages directly
- **Code Interpreter** (optional)
  - For converting tables → structured data
  - For generating/exporting `.md` files into a ZIP download

### 5.2 Agent Instructions

Provide this in the system prompt:

```
Your job is to generate a complete neighborhood profile in Markdown. 
For each neighborhood:
- Read the relevant Wikipedia page
- Extract demographics, boundaries, ZIP codes, transit options, and historical notes
- Use your own reasoning to summarize "Key Details" and the "Around the Block" narrative
- Pull additional structured information from NYC Open Data when needed
- Output the final result ONLY in the approved Markdown template
- Use tildes (~~~) for any internal code blocks
- Ensure accuracy, avoid fabricating data, and leave placeholders when missing
```

---

## 6. Workflow Inside Agent Builder

1. User enters:  
   **“Generate profile for Maspeth, Queens (v1.0)”**

2. Agent:
   - Opens Wikipedia
   - Extracts relevant data
   - Opens NYC Open Data for district boundaries, ZIP verification, etc.
   - Writes the Markdown using the template
   - Generates a downloadable `.md` file

3. Repeat for each neighborhood.

---

## 7. Scaling Up

Once the workflow works for 1 neighborhood:

- Upload your CSV
- Build a loop:
  - Agent iterates through each row
  - Produces one `.md` file per neighborhood
  - Bundles them into a ZIP for download
- Version updates handled via:
  - Input parameters:  
    `--version 1.1 --ratified 2025-12-04`

---

## 8. Why This Works (and Python Didn't)

| Task | Python Scraper | Agent Builder |
|------|----------------|----------------|
| Extracting structured tables | Hard | Easy |
| Understanding unstructured text | **Very hard** | **Native strength** |
| Writing narrative summaries | Impossible | Natural |
| Handling inconsistent Wikipedia pages | Fragile | Robust |
| Generating Markdown | Manual | Built-in |
| Maintaining / debugging | High cost | Low cost |

You picked the correct pivot.

---

## 9. Next Steps

1. I can generate:
   - Your **Agent Builder system prompt**
   - Your **Output schema**  
   - A **Starter JSON personality file**
2. You plug it into Agent Builder.
3. You test with 1–2 neighborhoods.
4. We refine.
