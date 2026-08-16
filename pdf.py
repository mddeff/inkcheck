import os
from io import BytesIO

import yaml
from reportlab.pdfgen import canvas

LAYOUT_PATH = os.environ.get(
    "CHECK_LAYOUT_PATH", os.path.join(os.path.dirname(__file__), "config", "check_layout.yml")
)

_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen",
]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
_SCALES = [(1_000_000_000, "Billion"), (1_000_000, "Million"), (1_000, "Thousand")]


def _three_digit_words(n):
    words = []
    hundreds, rem = divmod(n, 100)
    if hundreds:
        words.append(f"{_ONES[hundreds]} Hundred")
    if rem:
        if rem < 20:
            words.append(_ONES[rem])
        else:
            tens, ones = divmod(rem, 10)
            word = _TENS[tens] + (f"-{_ONES[ones]}" if ones else "")
            words.append(word)
    return " ".join(words)


def _dollars_to_words(n):
    if n == 0:
        return "Zero"
    parts = []
    remaining = n
    for scale_value, scale_name in _SCALES:
        if remaining >= scale_value:
            count, remaining = divmod(remaining, scale_value)
            parts.append(f"{_three_digit_words(count)} {scale_name}")
    if remaining:
        parts.append(_three_digit_words(remaining))
    return " ".join(parts)


def spell_out_cents(amount_cents):
    dollars, cents = divmod(amount_cents, 100)
    return f"{_dollars_to_words(dollars)} and {cents:02d}/100"


def load_layout():
    with open(LAYOUT_PATH) as f:
        return yaml.safe_load(f)


def render_check_pdf(txn):
    layout = load_layout()
    page = layout["page"]
    offset = layout.get("offset", {"x_pt": 0, "y_pt": 0})
    font = layout.get("font", {"name": "Helvetica", "size": 11})
    fields = layout["fields"]

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(page["width_pt"], page["height_pt"]))
    c.setFont(font["name"], font["size"])

    def draw(field_name, text):
        f = fields[field_name]
        x = f["x"] + offset.get("x_pt", 0)
        y = f["y"] + offset.get("y_pt", 0)
        if f.get("align") == "right":
            c.drawRightString(x, y, text)
        else:
            c.drawString(x, y, text)

    amount = txn["amount_cents"] / 100
    draw("date", txn["date"])
    draw("pay_to", txn["description"])
    draw("amount_numeric", f"{amount:,.2f}")
    draw("amount_words", spell_out_cents(txn["amount_cents"]))
    draw("memo", txn["memo"] or "")

    c.showPage()
    c.save()
    return buf.getvalue()
