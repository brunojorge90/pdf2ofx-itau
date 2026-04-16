import hashlib
from datetime import datetime


def _make_fitid(date: str, description: str, amount: float) -> str:
    raw = f"{date}|{description}|{amount}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def generate_ofx(transactions: list[dict]) -> str:
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
        "<BALAMT>0.00",
        f"<DTASOF>{now}",
        "</LEDGERBAL>",
        "</STMTRS>",
        "</STMTTRNRS>",
        "</BANKMSGSRSV1>",
        "</OFX>",
    ])

    return header + "\n".join(body_lines)
