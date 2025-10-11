from io import BytesIO
import qrcode

def make_simple_payment_text(name: str, iban: str, amount: str, currency: str, purpose: str, order_id: str) -> str:
    return "\n".join([
        f"PAY TO: {name}",
        f"IBAN/ACC: {iban}",
        f"AMOUNT: {amount} {currency}",
        f"ORDER ID: {order_id}",
        f"PURPOSE: {purpose}",
    ])

def gen_qr_png_bytes(text: str) -> bytes:
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(text); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO(); img.save(bio, format="PNG")
    return bio.getvalue()
