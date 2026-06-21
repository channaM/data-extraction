"""
ABA Bank — configuration.

To update for new ABA statement formats:
  1. Add new column name variants to COLUMN_MAP (always lowercase).
  2. Adjust HEADER_SEARCH_KEYWORDS if ABA changes their column header names.
  3. Adjust DATE_FORMATS if ABA changes their date format.
"""

BANK_NAME      = "aba"
BANK_FULL_NAME = "ABA Bank"
BANK_COUNTRY   = "Cambodia"

# ──────────────────────────────────────────────────────────────────────
# Column mapping  (all keys must be lowercase — normalised before lookup)
# Keys   → ABA's actual column headers (lowercase)
# Values → standard field names used throughout the pipeline
# ──────────────────────────────────────────────────────────────────────
COLUMN_MAP: dict[str, str] = {
    # Date variants
    "date":                 "transaction_date",
    "transaction date":     "transaction_date",
    "tran date":            "transaction_date",
    "trans date":           "transaction_date",
    "txn date":             "transaction_date",
    "value date":           "value_date",

    # Description / narration variants
    "narration":            "description",
    "description":          "description",
    "details":              "description",
    "particulars":          "description",
    "remarks":              "description",
    "transaction details":  "description",

    # Reference variants
    "reference no":         "reference_id",
    "reference":            "reference_id",
    "ref no":               "reference_id",
    "ref":                  "reference_id",
    "ref. no":              "reference_id",
    "transaction ref":      "reference_id",

    # Debit variants (money going OUT — always stored as positive)
    "debit":                "debit_amount",
    "debit (usd)":          "debit_amount",
    "debit (khr)":          "debit_amount",
    "withdrawal":           "debit_amount",
    "withdrawals":          "debit_amount",
    "dr":                   "debit_amount",

    # Credit variants (money coming IN — always stored as positive)
    "credit":               "credit_amount",
    "credit (usd)":         "credit_amount",
    "credit (khr)":         "credit_amount",
    "deposit":              "credit_amount",
    "deposits":             "credit_amount",
    "cr":                   "credit_amount",

    # Balance variants
    "balance":              "balance",
    "running balance":      "balance",
    "closing balance":      "balance",

    # Account variants
    "account no":           "account_number",
    "account number":       "account_number",
    "account":              "account_number",
    "acct no":              "account_number",
}

# ──────────────────────────────────────────────────────────────────────
# Header detection
# The extractor scans the first MAX_HEADER_SCAN_ROWS rows to find the
# row that contains the column headers.  It considers a row to be the
# header row if it contains at least HEADER_MIN_MATCH of these keywords.
# ──────────────────────────────────────────────────────────────────────
HEADER_SEARCH_KEYWORDS = {"date", "narration", "description", "debit",
                           "credit", "balance", "reference", "details"}
HEADER_MIN_MATCH       = 3
MAX_HEADER_SCAN_ROWS   = 20

# ──────────────────────────────────────────────────────────────────────
# Date parsing
# ──────────────────────────────────────────────────────────────────────
DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%Y%m%d",
]

# ──────────────────────────────────────────────────────────────────────
# Excel sheet preference
# ──────────────────────────────────────────────────────────────────────
EXCEL_SHEET_NAMES = ["Transactions", "Data", "Sheet1", "Sheet"]
