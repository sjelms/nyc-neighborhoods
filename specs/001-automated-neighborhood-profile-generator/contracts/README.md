# Contracts

For the "Automated Neighborhood Profile Generator" project, traditional API contracts (like REST or GraphQL schemas) are not applicable as this is a command-line interface (CLI) tool that processes local data and generates local files.

Instead, the "contracts" are defined by:

1.  **Input Data Format**: The structure of the CSV file (`neighborhood-borough.csv`) that provides the list of neighborhoods and their boroughs.
2.  **Output Document Template**: The fixed Markdown template (`output-template.md`) that defines the structure and expected content of the generated neighborhood profile files.
3.  **Data Model**: The `data-model.md` file defines the internal data structures that will be populated and used to render the output Markdown files.
