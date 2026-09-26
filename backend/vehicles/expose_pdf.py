"""Generate a branded, self-contained A4 vehicle expose without external PDF runtime dependencies."""
from io import BytesIO
from pathlib import Path

from django.conf import settings
from PIL import Image as PILImage

PAGE_W, PAGE_H = 595, 842


def _text(value):
    return str(value).strip() if value not in (None, "") else ""


def _pdf_text(value):
    return _text(value).encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _image_bytes(field, max_width, max_height):
    try:
        path = Path(field.path)
        with PILImage.open(path) as source:
            image = source.convert("RGB")
            scale = min(max_width / image.width, max_height / image.height, 1)
            image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))))
            stream = BytesIO()
            image.save(stream, format="JPEG", quality=88, optimize=True)
            return image.size, stream.getvalue()
    except (OSError, ValueError):
        return None, None


def _page_content(vehicle, image_data, page_number, page_count, contact, logo_ref=None):
    commands = ["q", "0.95 0.96 0.97 rg", "0 0 595 842 re", "f", "Q"]
    def text(x, y, value, size=10, font="F1", color="0.15 0.20 0.24"):
        commands.extend([f"{color} rg", "BT", f"/{font} {size} Tf", f"{x} {y} Td", f"({_pdf_text(value)}) Tj", "ET"])
    if logo_ref:
        commands.extend(["q", "135 0 0 38 54 775 cm", f"/Logo{logo_ref} Do", "Q"])
    text(54, 744, "FAHRZEUGEXPOSÉ", 18, "F2")
    text(54, 716, f"{vehicle.brand} {vehicle.model}", 24, "F2", "0.05 0.08 0.10")
    if _text(vehicle.variant):
        text(54, 697, vehicle.variant, 11)
    if image_data:
        image_ref, (width, height) = image_data
        x, y = 54, 485
        commands.extend(["q", f"{width} 0 0 {height} {x} {y} cm", f"/Im{image_ref} Do", "Q"])
    text(54, 455, "ANGEBOT", 9, "F2", "0.84 0.55 0.10")
    price = f"{vehicle.sale_price:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")
    text(54, 430, price, 20, "F2", "0.05 0.08 0.10")
    facts = [("Erstzulassung", vehicle.first_registration.strftime("%m/%Y") if vehicle.first_registration else ""), ("Kilometerstand", f"{vehicle.mileage:,} km".replace(",", ".")), ("Leistung", f"{vehicle.power_kw} kW / {vehicle.power_ps} PS"), ("Kraftstoff", vehicle.fuel_type), ("Getriebe", vehicle.transmission), ("Fahrzeugtyp", vehicle.vehicle_type)]
    for index, (label, value) in enumerate(facts):
        x = 54 + (index % 3) * 168
        y = 390 - (index // 3) * 54
        commands.extend(["0.90 0.92 0.93 rg", f"{x} {y} 158 40 re", "f"])
        text(x + 8, y + 25, label, 8, "F2", "0.35 0.40 0.43")
        text(x + 8, y + 10, value, 10, "F2")
    y = 270
    if _text(vehicle.description):
        text(54, y, "Fahrzeugbeschreibung", 12, "F2")
        for line in _text(vehicle.description).splitlines()[:5]:
            y -= 16
            text(54, y, line[: ninety], 9)
    equipment = _text(vehicle.equipment)
    if _text(vehicle.interior_equipment):
        equipment = f"{equipment} · Innenausstattung: {vehicle.interior_equipment}" if equipment else f"Innenausstattung: {vehicle.interior_equipment}"
    if equipment:
        y -= 26
        text(54, y, "Ausstattung", 12, "F2")
        for line in equipment.splitlines()[:5]:
            y -= 16
            text(54, y, line[: ninety], 9)
    commands.extend(["0.55 0.58 0.60 RG", "54 38 m", "541 38 l", "S"])
    text(54, 23, f"Auto Wallstein · {contact}", 8, "F1", "0.35 0.40 0.43")
    text(485, 23, f"Seite {page_number}/{page_count}", 8, "F1", "0.35 0.40 0.43")
    return "\n".join(commands).encode("latin-1")


# Keep this intentionally small; it is only used for short description lines.
ninety = 90


def build_vehicle_expose(vehicle, *, contact="06104 406770 · verkauf@auto-wallstein.de"):
    images = list(vehicle.images.all())
    prepared = []
    for item in images:
        size, data = _image_bytes(item.image, 487 if not prepared else 230, 220 if not prepared else 250)
        if size and data:
            prepared.append((size, data))
    pages = [prepared[0] if prepared else None]
    pages.extend(prepared[1:])
    if not pages:
        pages = [None]
    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    page_refs = []
    next_id = 5
    logo_size, logo_bytes = _image_bytes(type("Logo", (), {"path": Path(settings.BASE_DIR) / "static" / "images" / "logo.png"})(), 270, 76)
    logo_ref = None
    if logo_bytes:
        logo_ref = next_id
        next_id += 1
        width, height = logo_size
        objects.append(f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(logo_bytes)} >>\nstream\n".encode() + logo_bytes + b"\nendstream")
    for index, image in enumerate(pages):
        image_ref = None
        if image:
            image_ref = next_id
            next_id += 1
            (width, height), data = image
            objects.append(f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(data)} >>\nstream\n".encode() + data + b"\nendstream")
        content_ref = next_id
        next_id += 1
        content = _page_content(vehicle, (image_ref, image[0]) if image else None, index + 1, len(pages), contact, logo_ref)
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
        page_ref = next_id
        next_id += 1
        xobjects = []
        if image_ref:
            xobjects.append(f"/Im{image_ref} {image_ref} 0 R")
        if logo_ref:
            xobjects.append(f"/Logo{logo_ref} {logo_ref} 0 R")
        resources = f"/XObject << {' '.join(xobjects)} >>" if xobjects else ""
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> {resources} >> /Contents {content_ref} 0 R >>".encode())
        page_refs.append(page_ref)
    objects.insert(1, f"<< /Type /Pages /Count {len(page_refs)} /Kids [{''.join(f'{ref} 0 R ' for ref in page_refs)}] >>".encode())
    objects.insert(2, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.insert(3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    output = BytesIO(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, obj in enumerate(objects, 1):
        offsets.append(output.tell())
        if isinstance(obj, str):
            obj = obj.encode("latin-1")
        output.write(f"{object_id} 0 obj\n".encode() + obj + b"\nendobj\n")
    startxref = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode())
    output.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF".encode())
    return output.getvalue()
