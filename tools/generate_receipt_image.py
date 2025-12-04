import os
import random
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

ITEMS = [
    ("Rice 2kg", 220),
    ("Cooking Oil 1L", 365),
    ("Bread Brown", 78),
    ("Milk 500ml", 65),
    ("Sugar 1kg", 150),
    ("Chicken 1kg", 480),
    ("Onions", 50),
    ("Tomatoes", 40),
    ("Spaghetti 500g", 150),
    ("Tea Leaves 250g", 120),
]


def generate_receipt_text() -> str:
    """Generate a synthetic receipt as plain text."""
    merchant = random.choice(["Mama Lucy Shop", "QuickMart", "BudgetMart"])
    date = datetime.now().strftime("%d/%m/%Y %H:%M")
    chosen = random.sample(ITEMS, random.randint(4, 7))

    subtotal = sum(i[1] for i in chosen)
    vat = round(subtotal * 0.16, 2)
    total = round(subtotal + vat, 2)

    lines = [
        f"          {merchant}",
        "      Nairobi, Kenya",
        "",
        f"Date: {date}",
        "",
        "Items Purchased",
        "-------------------------",
    ]

    for name, price in chosen:
        lines.append(f"{name:<25} {price:>7.2f}")

    lines += [
        "-------------------------",
        f"Subtotal               {subtotal:.2f}",
        f"VAT (16%)              {vat:.2f}",
        "-------------------------",
        f"TOTAL                  {total:.2f} KES",
        "",
        "Payment: M-PESA",
        "Thank you for shopping!",
    ]

    return "\n".join(lines)


def create_receipt_image(
    text: str,
    output_path: str,
    width: int = 600,
    margin: int = 40,
    bg_color=(255, 255, 255),
    text_color=(0, 0, 0),
):
    """Render multiline receipt text into a PNG image and save it."""
    lines = text.splitlines()

    # Use a simple default font so this never crashes
    font = ImageFont.load_default()

    # Rough line height
    line_height = font.getbbox("A")[3] + 6

    height = margin * 2 + line_height * len(lines)

    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    y = margin
    for line in lines:
        draw.text((margin, y), line, fill=text_color, font=font)
        y += line_height

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    return output_path


def generate_receipt_image(output_dir: str) -> str:
    """High-level helper."""
    text = generate_receipt_text()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"receipt_{timestamp}.png"
    output_path = os.path.join(output_dir, filename)

    saved_path = create_receipt_image(text, output_path)
    return saved_path


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    # from tools/ -> project_root/data/sample_receipts
    output_dir = os.path.join(here, "..", "data", "sample_receipts")

    path = generate_receipt_image(output_dir=output_dir)
    print(f"Generated receipt image at: {os.path.normpath(path)}")
