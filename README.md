# gInvoiceParser

## Setup

1. Install Python 3.9+
2. Create a virtual environment:
    ```bash
    python -m venv parser
    ```

3. Activate it:
    - Windows:
        ```bash
        parser\Scripts\activate
        ```
    - macOS/Linux:
        ```bash
        source parser/bin/activate
        ```

4. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

5. Run the tool:
    ```bash
    python main.py
    ```

## What it Does

- Parses Google Ads, LinkedIn, DV360, CM360, Workspace invoices.
- Extracts and exports structured Excel outputs.

## Known Issues

- Some invoices (e.g., `5171504661`) may not show line-item details in v1.0.

## Coming in v1.1

- Improved Google Ads detail extraction
