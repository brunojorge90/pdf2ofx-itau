import os
import tempfile
from flask import Flask, render_template, request, jsonify
from parser_pdf import parse_pdf
from generator_ofx import generate_ofx

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


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

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        transactions = parse_pdf(tmp_path)
    except Exception as e:
        return jsonify({"error": f"Erro ao processar PDF: {str(e)}"}), 400
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not transactions:
        return jsonify({"error": "Nenhuma transação encontrada no PDF"}), 400

    ofx_content = generate_ofx(transactions)

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

    return jsonify({"transactions": preview, "count": len(preview), "ofx": ofx_content})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
