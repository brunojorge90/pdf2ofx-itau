from generator_ofx import generate_ofx


def test_generate_ofx_basic():
    transactions = [
        {"date": "2026-02-24", "description": "DM*Spotify", "amount": -40.90, "category": "DIVERSOS"},
        {"date": "2026-02-20", "description": "IG*LL12minMEGAB", "amount": 0.03, "category": "TURISMO E ENTRETENIM"},
    ]
    ofx = generate_ofx(transactions)

    assert "OFXHEADER:100" in ofx
    assert "<OFX>" in ofx
    assert "</OFX>" in ofx
    assert "<TRNTYPE>DEBIT" in ofx
    assert "<DTPOSTED>20260224" in ofx
    assert "<TRNAMT>-40.90" in ofx
    assert "<MEMO>DM*Spotify [DIVERSOS]" in ofx
    assert "<TRNTYPE>CREDIT" in ofx
    assert "<TRNAMT>0.03" in ofx
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
    import re
    fitids = re.findall(r"<FITID>(.+)", ofx)
    assert len(fitids) == 2
    assert fitids[0] != fitids[1]
