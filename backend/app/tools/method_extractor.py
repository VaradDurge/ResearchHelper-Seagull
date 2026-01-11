"""
# Method Extractor Tool

## What it does:
Extracts method details from a paper. Uses LLM to identify and extract structured
information about the method: algorithm, architecture, training, hyperparameters, experiments.

## How it works:
- Retrieves all chunks from the paper
- Uses LLM with extraction prompt to identify method sections
- Extracts structured information
- Returns method details

## What to include:
- extract_method(paper_id: str) -> MethodDetails
  - Gets all chunks for paper
  - Uses LLM to extract method information
  - Returns structured MethodDetails with:
    - Algorithm: step-by-step algorithm description
    - Architecture: model architecture description
    - Training Schedule: training phases, epochs, etc.
    - Hyperparameters: key hyperparameters in table format
    - Experiments: experimental setup and results
  - Uses structured output (JSON schema) from LLM
  
- Handles papers with no clear method section
- Extracts code snippets if present
"""

