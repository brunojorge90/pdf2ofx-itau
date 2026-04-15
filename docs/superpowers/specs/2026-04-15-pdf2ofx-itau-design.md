# PDF to OFX Converter — Fatura Itaú Cartão de Crédito

## Objetivo

Aplicação web (Flask) que converte faturas de cartão de crédito Itaú (PDF) para formato OFX, permitindo importação no app Mobills.

## Fluxo

Upload PDF → Parser extrai transações → Preview em tabela → Download OFX

## Arquitetura

### Interface Web (Flask + HTML/CSS)

Página única com:
- Área de upload (drag & drop ou botão)
- Botão "Converter"
- Tabela de preview com transações extraídas (data, descrição, categoria, valor)
- Botão "Baixar OFX"
- Mensagens de erro se PDF não for reconhecido

Stack: Flask + HTML/CSS simples, sem framework frontend.

### Parser PDF (`parser_pdf.py`)

Usa PyMuPDF para extrair texto do PDF.

Regras de extração:
- **Transação**: linha iniciando com `dd/mm`, seguida de descrição, opcionalmente parcelas `XX/XX`, e valor no final (formato `1.234,56`)
- **Valores negativos**: linhas com `- 0,01` etc. são ajustes/estornos
- **Categorias**: textos como `DIVERSOS .SAO PAULO`, `VESTUÁRIO .SAO PAULO` — associados ao bloco de transações correspondente
- **Ano**: inferido a partir da data de vencimento da fatura (página 1)
- **Linhas ignoradas**: cabeçalhos, resumo, boleto, rodapés, textos informativos
- **Encoding**: normalização de caracteres corrompidos (`VESTU�RIO` → `VESTUÁRIO`)

### Gerador OFX (`generator_ofx.py`)

Formato OFX 1.0.2 (SGML) — máxima compatibilidade com Mobills.

Cada transação gera um `<STMTTRN>`:
- `<DTPOSTED>` — `YYYYMMDD`
- `<TRNAMT>` — negativo para compras, positivo para estornos
- `<MEMO>` — descrição + categoria entre colchetes (ex: `APPLECOMBILL [DIVERSOS]`)
- `<TRNTYPE>` — `DEBIT` ou `CREDIT`
- `<FITID>` — hash único de data+descrição+valor

## Estrutura do Projeto

```
pdf2ofx-itau/
├── app.py              # Flask app (rotas, upload, download)
├── parser_pdf.py       # Extração de transações do PDF
├── generator_ofx.py    # Geração do arquivo OFX
├── templates/
│   └── index.html      # Página única
├── static/
│   └── style.css       # Estilos
└── requirements.txt    # Flask, PyMuPDF
```

## Decisões Técnicas

- **PyMuPDF** já está instalado na máquina do usuário
- **OFX 1.0.2 SGML** por compatibilidade com Mobills
- **Sem banco de dados** — conversão stateless
- **Categorias no MEMO** — Mobills não suporta campo de categoria no OFX, então vai no memo
