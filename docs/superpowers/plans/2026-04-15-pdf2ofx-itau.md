# PDF to OFX Itaú — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Flask web app that converts Itaú credit card PDF statements to OFX format for import into Mobills.

**Architecture:** Three modules — PDF parser (PyMuPDF), OFX generator (string templates), Flask app (upload/preview/download). Single page UI with drag & drop upload, transaction preview table, and OFX download.

**Tech Stack:** Python 3.11, Flask, PyMuPDF (fitz), HTML/CSS

---

## File Structure

| File | Responsibility |
|------|---------------|
| `parser_pdf.py` | Extract transactions from Itaú PDF: date, description, amount, category |
| `generator_ofx.py` | Convert list of transactions to OFX 1.0.2 SGML string |
| `app.py` | Flask routes: upload PDF, return preview JSON, serve OFX download |
| `templates/index.html` | Single page UI: upload area, preview table, download button |
| `static/style.css` | Styling |
| `requirements.txt` | Dependencies |
| `tests/test_parser.py` | Tests for PDF parser |
| `tests/test_generator.py` | Tests for OFX generator |

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py`

- [ ] **Step 1: Initialize git repo and create requirements.txt**

```bash
cd C:/Users/Dell/Projetos/pdf2ofx-itau
git init
```

```
# requirements.txt
Flask==3.1.1
PyMuPDF==1.27.2.2
```

- [ ] **Step 2: Create empty test package**

Create `tests/__init__.py` (empty file).

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt tests/__init__.py docs/
git commit -m "chore: initial project setup with requirements and spec"
```

---

### Task 2: PDF Parser — Transaction Extraction

**Files:**
- Create: `tests/test_parser.py`
- Create: `parser_pdf.py`

**Reference:** Use the sample PDF at `C:\Users\Dell\Documents\Fatura_Itau_26.03.26.pdf` for testing.

- [ ] **Step 1: Write failing tests for parser**

```python
# tests/test_parser.py
import pytest
from parser_pdf import parse_transaction_line, extract_due_date_year, infer_year, normalize_encoding, parse_pdf

# --- Unit tests for line parsing ---

def test_parse_simple_transaction():
    line = "24/02\tDM*Spotify\t40,90"
    result = parse_transaction_line(line)
    assert result is not None
    assert result["day"] == 24
    assert result["month"] == 2
    assert result["description"] == "DM*Spotify"
    assert result["amount"] == -40.90

def test_parse_installment_transaction():
    line = "01/09\tVIVA MOVEIS\t19/21\t333,40"
    result = parse_transaction_line(line)
    assert result is not None
    assert result["description"] == "VIVA MOVEIS 19/21"
    assert result["amount"] == -333.40

def test_parse_negative_adjustment():
    line = "20/01\tIG*LL12minMEGAB\t- 0,03"
    result = parse_transaction_line(line)
    assert result is not None
    assert result["amount"] == 0.03  # positive = credit/refund

def test_parse_large_value():
    line = "18/12\tMP *SPECIALC-CT\t04/06\t2.166,70"
    result = parse_transaction_line(line)
    assert result is not None
    assert result["amount"] == -2166.70

def test_ignore_non_transaction_line():
    line = "Total da fatura anterior"
    result = parse_transaction_line(line)
    assert result is None

def test_ignore_header_line():
    line = "DATA\tESTABELECIMENTO\tVALOR EM R$"
    result = parse_transaction_line(line)
    assert result is None

# --- Due date / year inference ---

def test_extract_due_date_year():
    text = "Vencimento\n26/03/2026\nOutra coisa"
    assert extract_due_date_year(text) == (2026, 3)

def test_infer_year_same_year():
    # Transaction in Feb, due date in March 2026
    assert infer_year(month=2, due_month=3, due_year=2026) == 2026

def test_infer_year_cross_year():
    # Transaction in Dec, due date in Jan 2026 -> transaction was in 2025
    assert infer_year(month=12, due_month=1, due_year=2026) == 2025

def test_infer_year_cross_year_feb():
    # Transaction in Nov, due date in Jan 2026 -> transaction was in 2025
    assert infer_year(month=11, due_month=1, due_year=2026) == 2025

# --- Encoding normalization ---

def test_normalize_encoding():
    assert normalize_encoding("VESTU\ufffdRIO") == "VESTUÁRIO"
    assert normalize_encoding("TURISMO E ENTRETENIM") == "TURISMO E ENTRETENIM"

# --- Integration test with real PDF ---

def test_parse_real_pdf():
    transactions = parse_pdf(r"C:\Users\Dell\Documents\Fatura_Itau_26.03.26.pdf")
    assert len(transactions) > 50  # PDF has many transactions
    first = transactions[0]
    assert "date" in first
    assert "description" in first
    assert "amount" in first
    assert "category" in first
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/Dell/Projetos/pdf2ofx-itau
python -m pytest tests/test_parser.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'parser_pdf'`

- [ ] **Step 3: Implement parser_pdf.py**

```python
# parser_pdf.py
import re
import hashlib
import fitz  # PyMuPDF


def normalize_encoding(text: str) -> str:
    """Fix common encoding issues in Itaú PDFs."""
    replacements = {
        "\ufffdR": "ÁR",   # VESTU�RIO -> VESTUÁRIO
        "\ufffdO": "ÃO",   # educa\ufffdO -> EDUCAÇÃO
        "\ufffdA": "ÇA",
        "\ufffd": "Ã",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def extract_due_date_year(first_page_text: str) -> tuple[int, int]:
    """Extract due date year and month from first page.
    Returns (year, month).
    """
    match = re.search(r"Vencimento\s*\n?\s*(\d{2})/(\d{2})/(\d{4})", first_page_text)
    if match:
        return int(match.group(3)), int(match.group(2))
    # Fallback: search for date pattern near "vencimento"
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", first_page_text)
    if match:
        return int(match.group(3)), int(match.group(2))
    raise ValueError("Could not find due date in PDF")


def infer_year(month: int, due_month: int, due_year: int) -> int:
    """Infer transaction year from transaction month and due date.
    Transactions from months after the due month belong to the previous year.
    """
    if month > due_month + 2:
        return due_year - 1
    return due_year


# Regex for transaction lines
# Matches: dd/mm  description  [nn/nn]  [-] value
_TX_RE = re.compile(
    r"^(\d{2})/(\d{2})\s+"       # date dd/mm
    r"(.+?)\s+"                   # description (non-greedy)
    r"(-\s*)?"                    # optional negative sign
    r"(\d{1,3}(?:\.\d{3})*,\d{2})"  # value 1.234,56
    r"\s*$"
)

_CATEGORY_RE = re.compile(
    r"^(DIVERSOS|VESTU[ÁA\ufffd]RIO|ALIMENTA[ÇC\ufffd][ÃA\ufffd]O|SA[ÚU\ufffd]DE|"
    r"TURISMO E ENTRETENIM|HOBBY|MORADIA|EDUCA[ÇC\ufffd][ÃA\ufffd]O|"
    r"VE[ÍI\ufffd]CULOS|SERVI[ÇC\ufffd]OS)\b",
    re.IGNORECASE
)

_HEADER_RE = re.compile(r"^DATA\s+ESTABELECIMENTO|^Lan[çc\ufffd]amentos", re.IGNORECASE)


def parse_transaction_line(line: str) -> dict | None:
    """Parse a single line into a transaction dict or None if not a transaction."""
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

    if is_negative_adj:
        # Negative adjustment in PDF = credit/refund -> positive in OFX
        amount = amount
    else:
        # Normal purchase -> negative in OFX
        amount = -amount

    # Check for installment info at end of description
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


def parse_pdf(pdf_path: str) -> list[dict]:
    """Parse an Itaú credit card PDF and return list of transactions.
    Each transaction: {date, description, amount, category}
    """
    doc = fitz.open(pdf_path)

    # Get due date from first page
    first_page_text = doc[0].get_text()
    due_year, due_month = extract_due_date_year(first_page_text)

    transactions = []
    current_category = ""

    for page in doc:
        text = page.get_text()
        text = normalize_encoding(text)
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a category line
            cat_match = _CATEGORY_RE.match(line)
            if cat_match:
                current_category = cat_match.group(1).upper()
                current_category = normalize_encoding(current_category)
                continue

            # Try to parse as transaction
            tx = parse_transaction_line(line)
            if tx:
                year = infer_year(tx["month"], due_month, due_year)
                tx["date"] = f"{year:04d}-{tx['month']:02d}-{tx['day']:02d}"
                tx["category"] = current_category
                del tx["day"]
                del tx["month"]
                transactions.append(tx)

    doc.close()
    return transactions
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_parser.py -v
```

Expected: All tests PASS. If some fail, adjust regex patterns to match actual PDF layout.

- [ ] **Step 5: Commit**

```bash
git add parser_pdf.py tests/test_parser.py
git commit -m "feat: add PDF parser for Itaú credit card statements"
```

---

### Task 3: OFX Generator

**Files:**
- Create: `tests/test_generator.py`
- Create: `generator_ofx.py`

- [ ] **Step 1: Write failing tests for OFX generator**

```python
# tests/test_generator.py
from generator_ofx import generate_ofx


def test_generate_ofx_basic():
    transactions = [
        {
            "date": "2026-02-24",
            "description": "DM*Spotify",
            "amount": -40.90,
            "category": "DIVERSOS",
        },
        {
            "date": "2026-02-20",
            "description": "IG*LL12minMEGAB",
            "amount": 0.03,
            "category": "TURISMO E ENTRETENIM",
        },
    ]
    ofx = generate_ofx(transactions)

    # OFX header
    assert "OFXHEADER:100" in ofx
    assert "<OFX>" in ofx
    assert "</OFX>" in ofx

    # Transaction 1 — debit
    assert "<TRNTYPE>DEBIT" in ofx
    assert "<DTPOSTED>20260224" in ofx
    assert "<TRNAMT>-40.90" in ofx
    assert "<MEMO>DM*Spotify [DIVERSOS]" in ofx

    # Transaction 2 — credit (refund)
    assert "<TRNTYPE>CREDIT" in ofx
    assert "<TRNAMT>0.03" in ofx

    # FITID must be unique
    assert ofx.count("<FITID>") == 2


def test_generate_ofx_empty():
    ofx = generate_ofx([])
    assert "<OFX>" in ofx
    assert "<STMTTRN>" not in ofx


def test_fitid_uniqueness():
    transactions = [
        {"date": "2026-02-24", "description": "LOJA A", "amount": -100.00, "category": ""},
        {"date": "2026-02-24", "description": "LOJA B", "amount": -100.00, "category": ""},
    ]
    ofx = generate_ofx(transactions)
    # Extract FITIDs
    import re
    fitids = re.findall(r"<FITID>(.+)", ofx)
    assert len(fitids) == 2
    assert fitids[0] != fitids[1]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_generator.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'generator_ofx'`

- [ ] **Step 3: Implement generator_ofx.py**

```python
# generator_ofx.py
import hashlib
from datetime import datetime


def _make_fitid(date: str, description: str, amount: float) -> str:
    """Generate unique transaction ID from date + description + amount."""
    raw = f"{date}|{description}|{amount}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def generate_ofx(transactions: list[dict]) -> str:
    """Generate OFX 1.0.2 SGML string from list of transactions."""
    now = datetime.now().strftime("%Y%m%d%H%M%S")

    header = (
        "OFXHEADER:100\n"
        "DATA:OFXSGML\n"
        "VERSION:102\n"
        "SECURITY:NONE\n"
        "ENCODING:USASCII\n"
        "CHARSET:1252\n"
        "COMPRESSION:NONE\n"
        "OLDFILEUID:NONE\n"
        "NEWFILEUID:NONE\n"
        "\n"
    )

    body_lines = [
        "<OFX>",
        "<SIGNONMSGSRSV1>",
        "<SONRS>",
        "<STATUS>",
        "<CODE>0",
        "<SEVERITY>INFO",
        "</STATUS>",
        f"<DTSERVER>{now}",
        "<LANGUAGE>POR",
        "</SONRS>",
        "</SIGNONMSGSRSV1>",
        "<BANKMSGSRSV1>",
        "<STMTTRNRS>",
        "<TRNUID>1",
        "<STATUS>",
        "<CODE>0",
        "<SEVERITY>INFO",
        "</STATUS>",
        "<STMTRS>",
        "<CURDEF>BRL",
        "<BANKACCTFROM>",
        "<BANKID>0341",
        "<ACCTID>ITAU-CC",
        "<ACCTTYPE>CREDITLINE",
        "</BANKACCTFROM>",
        "<BANKTRANLIST>",
        f"<DTSTART>{now}",
        f"<DTEND>{now}",
    ]

    for tx in transactions:
        date_fmt = tx["date"].replace("-", "")
        trntype = "CREDIT" if tx["amount"] > 0 else "DEBIT"
        memo = tx["description"]
        if tx.get("category"):
            memo += f" [{tx['category']}]"
        fitid = _make_fitid(tx["date"], tx["description"], tx["amount"])

        body_lines.extend([
            "<STMTTRN>",
            f"<TRNTYPE>{trntype}",
            f"<DTPOSTED>{date_fmt}",
            f"<TRNAMT>{tx['amount']:.2f}",
            f"<FITID>{fitid}",
            f"<MEMO>{memo}",
            "</STMTTRN>",
        ])

    body_lines.extend([
        "</BANKTRANLIST>",
        "<LEDGERBAL>",
        f"<BALAMT>0.00",
        f"<DTASOF>{now}",
        "</LEDGERBAL>",
        "</STMTRS>",
        "</STMTTRNRS>",
        "</BANKMSGSRSV1>",
        "</OFX>",
    ])

    return header + "\n".join(body_lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_generator.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add generator_ofx.py tests/test_generator.py
git commit -m "feat: add OFX 1.0.2 generator"
```

---

### Task 4: Flask App — Routes

**Files:**
- Create: `app.py`

- [ ] **Step 1: Implement app.py**

```python
# app.py
import os
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
from parser_pdf import parse_pdf
from generator_ofx import generate_ofx

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    if "pdf" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["pdf"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Arquivo deve ser PDF"}), 400

    # Save uploaded PDF to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        transactions = parse_pdf(tmp_path)
    except Exception as e:
        os.unlink(tmp_path)
        return jsonify({"error": f"Erro ao processar PDF: {str(e)}"}), 400
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not transactions:
        return jsonify({"error": "Nenhuma transação encontrada no PDF"}), 400

    # Generate OFX
    ofx_content = generate_ofx(transactions)

    # Save OFX to temp file for download
    ofx_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ofx", mode="w", encoding="utf-8")
    ofx_tmp.write(ofx_content)
    ofx_tmp.close()

    # Store OFX path in a simple way for download
    app.config["LAST_OFX_PATH"] = ofx_tmp.name

    # Return preview data
    preview = [
        {
            "date": tx["date"],
            "description": tx["description"],
            "category": tx.get("category", ""),
            "amount": f"R$ {abs(tx['amount']):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "type": "Estorno" if tx["amount"] > 0 else "Compra",
        }
        for tx in transactions
    ]

    return jsonify({"transactions": preview, "count": len(preview)})


@app.route("/download")
def download():
    ofx_path = app.config.get("LAST_OFX_PATH")
    if not ofx_path or not os.path.exists(ofx_path):
        return "Nenhum arquivo OFX disponível. Converta um PDF primeiro.", 404

    return send_file(
        ofx_path,
        as_attachment=True,
        download_name="fatura_itau.ofx",
        mimetype="application/x-ofx",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

- [ ] **Step 2: Verify app starts**

```bash
cd C:/Users/Dell/Projetos/pdf2ofx-itau
python -c "from app import app; print('App imports OK')"
```

Expected: `App imports OK`

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add Flask app with upload, convert, and download routes"
```

---

### Task 5: Frontend — HTML Template

**Files:**
- Create: `templates/index.html`

- [ ] **Step 1: Create the HTML template**

```html
<!-- templates/index.html -->
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF → OFX | Fatura Itaú</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <div class="container">
        <h1>Conversor PDF → OFX</h1>
        <p class="subtitle">Fatura de cartão Itaú → Mobills</p>

        <div id="upload-area" class="upload-area">
            <input type="file" id="pdf-input" accept=".pdf" hidden>
            <p class="upload-text">Arraste o PDF aqui ou <span class="link">clique para selecionar</span></p>
            <p id="file-name" class="file-name"></p>
        </div>

        <button id="convert-btn" class="btn" disabled>Converter</button>

        <div id="error-msg" class="error" hidden></div>

        <div id="result" hidden>
            <h2>Transações extraídas (<span id="count"></span>)</h2>
            <div class="table-wrapper">
                <table id="transactions-table">
                    <thead>
                        <tr>
                            <th>Data</th>
                            <th>Descrição</th>
                            <th>Categoria</th>
                            <th>Tipo</th>
                            <th>Valor</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
            <button id="download-btn" class="btn btn-download">Baixar OFX</button>
        </div>

        <div id="loading" class="loading" hidden>
            <p>Processando...</p>
        </div>
    </div>

    <script>
        const uploadArea = document.getElementById("upload-area");
        const pdfInput = document.getElementById("pdf-input");
        const convertBtn = document.getElementById("convert-btn");
        const errorMsg = document.getElementById("error-msg");
        const result = document.getElementById("result");
        const loading = document.getElementById("loading");
        const fileName = document.getElementById("file-name");
        const countSpan = document.getElementById("count");
        const tbody = document.querySelector("#transactions-table tbody");
        const downloadBtn = document.getElementById("download-btn");

        let selectedFile = null;

        // Click to select
        uploadArea.addEventListener("click", () => pdfInput.click());

        // File selected
        pdfInput.addEventListener("change", (e) => {
            selectedFile = e.target.files[0];
            if (selectedFile) {
                fileName.textContent = selectedFile.name;
                convertBtn.disabled = false;
                errorMsg.hidden = true;
                result.hidden = true;
            }
        });

        // Drag & drop
        uploadArea.addEventListener("dragover", (e) => {
            e.preventDefault();
            uploadArea.classList.add("dragover");
        });
        uploadArea.addEventListener("dragleave", () => {
            uploadArea.classList.remove("dragover");
        });
        uploadArea.addEventListener("drop", (e) => {
            e.preventDefault();
            uploadArea.classList.remove("dragover");
            const file = e.dataTransfer.files[0];
            if (file && file.name.toLowerCase().endsWith(".pdf")) {
                selectedFile = file;
                fileName.textContent = file.name;
                convertBtn.disabled = false;
                errorMsg.hidden = true;
                result.hidden = true;
            }
        });

        // Convert
        convertBtn.addEventListener("click", async () => {
            if (!selectedFile) return;

            loading.hidden = false;
            errorMsg.hidden = true;
            result.hidden = true;
            convertBtn.disabled = true;

            const formData = new FormData();
            formData.append("pdf", selectedFile);

            try {
                const res = await fetch("/convert", { method: "POST", body: formData });
                const data = await res.json();

                if (!res.ok) {
                    errorMsg.textContent = data.error;
                    errorMsg.hidden = false;
                } else {
                    countSpan.textContent = data.count;
                    tbody.innerHTML = "";
                    data.transactions.forEach((tx) => {
                        const tr = document.createElement("tr");
                        tr.className = tx.type === "Estorno" ? "credit" : "";
                        tr.innerHTML = `
                            <td>${tx.date}</td>
                            <td>${tx.description}</td>
                            <td>${tx.category}</td>
                            <td>${tx.type}</td>
                            <td class="amount">${tx.amount}</td>
                        `;
                        tbody.appendChild(tr);
                    });
                    result.hidden = false;
                }
            } catch (err) {
                errorMsg.textContent = "Erro de conexão com o servidor.";
                errorMsg.hidden = false;
            } finally {
                loading.hidden = true;
                convertBtn.disabled = false;
            }
        });

        // Download
        downloadBtn.addEventListener("click", () => {
            window.location.href = "/download";
        });
    </script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/index.html
git commit -m "feat: add HTML template with upload, preview, and download UI"
```

---

### Task 6: Frontend — CSS Styling

**Files:**
- Create: `static/style.css`

- [ ] **Step 1: Create style.css**

```css
/* static/style.css */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5;
    color: #333;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    padding: 2rem;
}

.container {
    max-width: 900px;
    width: 100%;
}

h1 {
    font-size: 1.8rem;
    margin-bottom: 0.25rem;
}

.subtitle {
    color: #666;
    margin-bottom: 2rem;
}

.upload-area {
    border: 2px dashed #ccc;
    border-radius: 8px;
    padding: 3rem 2rem;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
    margin-bottom: 1rem;
}

.upload-area:hover,
.upload-area.dragover {
    border-color: #ec7000;
    background: #fff8f0;
}

.upload-text {
    color: #888;
}

.link {
    color: #ec7000;
    text-decoration: underline;
    cursor: pointer;
}

.file-name {
    margin-top: 0.5rem;
    font-weight: 600;
    color: #333;
}

.btn {
    background: #ec7000;
    color: #fff;
    border: none;
    padding: 0.75rem 2rem;
    font-size: 1rem;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.2s;
}

.btn:hover:not(:disabled) {
    background: #d46200;
}

.btn:disabled {
    background: #ccc;
    cursor: not-allowed;
}

.btn-download {
    background: #28a745;
    margin-top: 1rem;
}

.btn-download:hover {
    background: #218838;
}

.error {
    color: #dc3545;
    background: #ffeef0;
    padding: 0.75rem 1rem;
    border-radius: 6px;
    margin-top: 1rem;
}

.loading {
    text-align: center;
    padding: 2rem;
    color: #888;
}

h2 {
    font-size: 1.2rem;
    margin: 2rem 0 1rem;
}

.table-wrapper {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

th {
    background: #f8f9fa;
    padding: 0.75rem 1rem;
    text-align: left;
    font-weight: 600;
    font-size: 0.85rem;
    color: #666;
    border-bottom: 2px solid #dee2e6;
}

td {
    padding: 0.5rem 1rem;
    border-bottom: 1px solid #eee;
    font-size: 0.9rem;
}

tr:hover {
    background: #f8f9fa;
}

tr.credit td {
    color: #28a745;
}

.amount {
    text-align: right;
    font-variant-numeric: tabular-nums;
}
```

- [ ] **Step 2: Commit**

```bash
git add static/style.css
git commit -m "feat: add CSS styling for converter UI"
```

---

### Task 7: Integration Test — Full Flow

**Files:** None new (uses existing)

- [ ] **Step 1: Start the Flask server and test manually**

```bash
cd C:/Users/Dell/Projetos/pdf2ofx-itau
python app.py
```

Open `http://localhost:5000` in browser.

Test flow:
1. Upload `C:\Users\Dell\Documents\Fatura_Itau_26.03.26.pdf`
2. Click "Converter"
3. Verify transactions appear in preview table
4. Click "Baixar OFX"
5. Verify the downloaded `.ofx` file is valid

- [ ] **Step 2: Verify OFX imports in Mobills**

Open the downloaded `.ofx` file in Mobills to confirm it imports correctly.

- [ ] **Step 3: Fix any issues found during testing**

Adjust parser regex, OFX format, or UI based on testing results.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "fix: adjustments from integration testing"
```
