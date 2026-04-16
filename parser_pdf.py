import re
import fitz  # PyMuPDF


def normalize_encoding(text: str) -> str:
    replacements = {
        "\ufffdR": "ÁR",
        "\ufffdO": "ÃO",
        "\ufffdA": "ÇA",
        "\ufffd": "Ã",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def extract_due_date_year(first_page_text: str) -> tuple[int, int]:
    match = re.search(r"Vencimento\s*\n?\s*(\d{2})/(\d{2})/(\d{4})", first_page_text)
    if match:
        return int(match.group(3)), int(match.group(2))
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", first_page_text)
    if match:
        return int(match.group(3)), int(match.group(2))
    raise ValueError("Could not find due date in PDF")


def infer_year(month: int, due_month: int, due_year: int) -> int:
    if month > due_month + 2:
        return due_year - 1
    return due_year


# Keep for backward compatibility with unit tests
_TX_RE = re.compile(
    r"^(\d{2})/(\d{2})\s+"
    r"(.+?)\s+"
    r"(-\s*)?"
    r"(\d{1,3}(?:\.\d{3})*,\d{2})"
    r"\s*$"
)
_HEADER_RE = re.compile(r"^DATA\s+ESTABELECIMENTO|^Lan[çc\ufffd]amentos", re.IGNORECASE)


def parse_transaction_line(line: str) -> dict | None:
    line = line.strip()
    if not line or _HEADER_RE.match(line):
        return None

    match = _TX_RE.match(line)
    if not match:
        return None

    day = int(match.group(1))
    month = int(match.group(2))
    description = match.group(3).strip()
    is_negative_adj = match.group(4) is not None
    value_str = match.group(5).replace(".", "").replace(",", ".")
    amount = float(value_str)

    if not is_negative_adj:
        amount = -amount

    inst_match = re.search(r"\s+(\d{2}/\d{2})$", description)
    if inst_match:
        installment = inst_match.group(1)
        desc_clean = description[:inst_match.start()].strip()
        description = f"{desc_clean} {installment}"

    return {
        "day": day,
        "month": month,
        "description": description,
        "amount": amount,
    }


_DATE_LINE_RE = re.compile(r'^(\d{2})/(\d{2})$')
_VALUE_RE = re.compile(r'^-\s*\d{1,3}(?:\.\d{3})*,\d{2}$|^\d{1,3}(?:\.\d{3})*,\d{2}$')


def _is_date_line(line: str) -> tuple[int, int] | None:
    m = _DATE_LINE_RE.match(line)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return day, month
    return None


def _parse_amount(value_str: str) -> float:
    is_negative = value_str.lstrip().startswith('-')
    numeric = re.sub(r'[^\d,]', '', value_str).replace(',', '.')
    amount = float(numeric)
    return amount if is_negative else -amount


def parse_pdf(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    first_page_text = doc[0].get_text()
    due_year, due_month = extract_due_date_year(first_page_text)

    transactions = []

    for page in doc:
        text = normalize_encoding(page.get_text())
        lines = [l.strip() for l in text.split('\n')]

        i = 0
        while i < len(lines):
            line = lines[i]
            if not line:
                i += 1
                continue

            date_info = _is_date_line(line)
            if date_info is None:
                i += 1
                continue

            day, month = date_info
            i += 1

            desc_parts = []
            amount = None

            while i < len(lines):
                l = lines[i]
                if not l:
                    i += 1
                    continue

                if _VALUE_RE.match(l):
                    amount = _parse_amount(l)
                    i += 1
                    break

                # A date line with empty desc_parts = next transaction, don't consume
                if not desc_parts and _is_date_line(l):
                    break

                desc_parts.append(l)
                i += 1

            if amount is None or not desc_parts:
                continue

            year = infer_year(month, due_month, due_year)
            transactions.append({
                "date": f"{year:04d}-{month:02d}-{day:02d}",
                "description": " ".join(desc_parts),
                "amount": amount,
                "category": "",
            })

    doc.close()
    return transactions
