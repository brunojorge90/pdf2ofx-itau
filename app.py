import os
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
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

    ofx_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ofx", mode="w", encoding="utf-8")
    ofx_tmp.write(ofx_content)
    ofx_tmp.close()
    app.config["LAST_OFX_PATH"] = ofx_tmp.name

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
