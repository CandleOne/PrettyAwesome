import base64
import hashlib
import json
import mimetypes
import os
import re
import time
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

try:
    import stripe
except ImportError:
    stripe = None

ROOT = Path(__file__).resolve().parent
QUOTE_DIR = ROOT / "quote_requests"
QUOTE_DIR.mkdir(exist_ok=True)


def load_local_env(env_path: Path) -> None:
    if not env_path.exists() or not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_local_env(ROOT / ".env")

CLOUDINARY_CLOUD  = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_KEY    = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")

if stripe and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def cloudinary_upload(file_bytes: bytes, filename: str, folder: str) -> str:
    """Upload a file to Cloudinary and return the secure URL."""
    if not CLOUDINARY_CLOUD or not CLOUDINARY_KEY or not CLOUDINARY_SECRET:
        raise RuntimeError(
            "Cloudinary credentials not configured. "
            "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET."
        )
    ts = str(int(time.time()))
    safe_folder = re.sub(r"[^\w/._-]+", "_", folder)
    sign_str = f"folder={safe_folder}&timestamp={ts}{CLOUDINARY_SECRET}"
    signature = hashlib.sha1(sign_str.encode("utf-8")).hexdigest()
    boundary = "TeeminusBdy" + ts

    def _part(name: str, value: str) -> bytes:
        return (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode("utf-8")

    safe_filename = re.sub(r"[^\w.\-]", "_", filename)
    body = (
        _part("api_key", CLOUDINARY_KEY)
        + _part("timestamp", ts)
        + _part("folder", safe_folder)
        + _part("signature", signature)
        + (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{safe_filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
        + file_bytes
        + f"\r\n--{boundary}--\r\n".encode("utf-8")
    )
    req = urllib.request.Request(
        f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD}/auto/upload",
        data=body,
        method="POST",
    )
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    return result["secure_url"]


def escape_pdf_text(value: object) -> str:
    text = str(value)
    return (
        text
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def build_pdf(payload: dict) -> bytes:
    client    = payload.get("client", {})
    logistics = payload.get("logistics", {})
    billing = payload.get("billing", {})
    quantities = payload.get("quantities", {})
    sizes     = [f"{k}: {quantities.get(k, 0)}" for k in sorted(quantities)]
    designs   = payload.get("designs", [])

    design_lines: list[str] = []
    for i, d in enumerate(designs, 1):
        design_lines.extend([
            f"Design {i}: {d.get('placement') or 'Placement not set'}",
            f"  File: {d.get('fileName') or 'No file'}",
            f"  URL: {d.get('cloudinaryUrl') or 'Not uploaded'}",
        ])

    lines = [
        f"Tee-Minus Quote Request — {payload.get('projectName') or 'Untitled'}",
        "",
        f"Project: {payload.get('projectName') or 'Not provided'}",
        f"Submitted: {payload.get('submittedAt', 'Unknown')}",
        "",
        "Client Information",
        f"Name: {client.get('name', '')}",
        f"Email: {client.get('email', '')}",
        f"Phone: {client.get('phone', '')}",
        "",
        f"Shirt Color: {payload.get('shirtColor') or 'Not provided'}",
        f"Total Pieces: {payload.get('totalPieces', 0)}",
        "Sizes:",
        *sizes,
        "",
        "Designs:",
        *design_lines,
        "",
        "Logistics",
        f"Rush Order: {'Yes' if logistics.get('rushOrder') else 'No'}",
        f"Delivery: {logistics.get('delivery') or 'Not provided'}",
        f"Shipping Address: {logistics.get('shippingAddress') or 'Not provided'}",
        "",
        "Billing Profile",
        f"Saved Payment Method: {billing.get('paymentMethodLabel') or 'Not attached'}",
        f"Processor Payment Method ID: {billing.get('paymentMethodId') or 'Not attached'}",
        f"Billing Consent: {'Yes' if billing.get('consent') else 'No'}",
        "",
        "Additional Context",
        f"{payload.get('context') or 'No additional context provided'}",
        "",
        "Proof Approval",
        f"Acknowledged: {'Yes' if payload.get('proofApprovalAcknowledged') else 'No'}",
    ]

    font_size = 10
    line_height = 14
    start_y = 760
    content_stream = "BT\n/F1 {} Tf\n".format(font_size)
    for index, line in enumerate(lines):
        y = start_y - index * line_height
        content_stream += "1 0 0 1 72 {} Tm\n({}) Tj\n".format(y, escape_pdf_text(line))
    content_stream += "ET\n"

    content_bytes = content_stream.encode("latin-1", errors="replace")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        f"4 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n".encode("latin-1") + content_bytes + b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    pdf_bytes = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf_bytes))
        pdf_bytes.extend(obj)

    xref_offset = len(pdf_bytes)
    pdf_bytes.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf_bytes.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf_bytes.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    pdf_bytes.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
    )
    return bytes(pdf_bytes)


def save_pdf(payload: dict) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    project = payload.get("projectName") or payload.get("client", {}).get("name", "quote")
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", project.strip().lower()).strip("-") or "quote"
    filename = f"{safe_name}-{timestamp}.pdf"
    output_path = QUOTE_DIR / filename
    output_path.write_bytes(build_pdf(payload))
    return filename


def payments_ready() -> tuple[bool, str | None]:
    if stripe is None:
        return False, "stripe-sdk-missing"
    if not STRIPE_SECRET_KEY:
        return False, "missing-stripe-secret-key"
    if not STRIPE_PUBLISHABLE_KEY:
        return False, "missing-stripe-publishable-key"
    return True, None


def get_or_create_stripe_customer(payload: dict) -> object:
    existing_customer_id = (payload.get("customerId") or "").strip()
    if existing_customer_id:
        try:
            customer = stripe.Customer.retrieve(existing_customer_id)
            if customer and not getattr(customer, "deleted", False):
                updates = {}
                email = (payload.get("email") or "").strip()
                name = (payload.get("name") or "").strip()
                if email and customer.get("email") != email:
                    updates["email"] = email
                if name and customer.get("name") != name:
                    updates["name"] = name
                if updates:
                    customer = stripe.Customer.modify(existing_customer_id, **updates)
                return customer
        except Exception:
            pass

    metadata = {
        "teeminusAccountId": (payload.get("accountId") or "").strip(),
        "teeminusRole": (payload.get("role") or "").strip(),
    }
    metadata = {key: value for key, value in metadata.items() if value}
    return stripe.Customer.create(
        email=(payload.get("email") or "").strip() or None,
        name=(payload.get("name") or "").strip() or None,
        metadata=metadata,
    )


def create_setup_intent(payload: dict) -> dict:
    customer = get_or_create_stripe_customer(payload)
    setup_intent = stripe.SetupIntent.create(
        customer=customer.id,
        payment_method_types=["card"],
        usage="off_session",
        metadata={
            "teeminusAccountId": (payload.get("accountId") or "").strip(),
            "teeminusEmail": (payload.get("email") or "").strip(),
        },
    )
    return {
        "customerId": customer.id,
        "clientSecret": setup_intent.client_secret,
    }


def set_default_payment_method(payload: dict) -> dict:
    customer_id = (payload.get("customerId") or "").strip()
    payment_method_id = (payload.get("paymentMethodId") or "").strip()
    if not customer_id or not payment_method_id:
        raise ValueError("customer-and-payment-method-required")

    customer = stripe.Customer.modify(
        customer_id,
        invoice_settings={"default_payment_method": payment_method_id},
    )
    return {
        "customerId": customer.id,
        "defaultPaymentMethodId": customer.get("invoice_settings", {}).get("default_payment_method"),
    }


def detach_payment_method(payload: dict) -> dict:
    payment_method_id = (payload.get("paymentMethodId") or "").strip()
    if not payment_method_id:
        raise ValueError("payment-method-required")

    payment_method = stripe.PaymentMethod.detach(payment_method_id)
    return {
        "paymentMethodId": payment_method.id,
        "customerId": payment_method.get("customer") or "",
    }


def list_payment_methods(payload: dict) -> dict:
    customer_id = (payload.get("customerId") or "").strip()
    if not customer_id:
        raise ValueError("customer-required")

    customer = stripe.Customer.retrieve(customer_id)
    payment_methods = stripe.PaymentMethod.list(customer=customer_id, type="card", limit=20)
    default_payment_method_id = customer.get("invoice_settings", {}).get("default_payment_method")

    methods = []
    for payment_method in payment_methods.data:
        card = payment_method.get("card") or {}
        methods.append({
            "id": payment_method.id,
            "brand": card.get("brand") or "card",
            "last4": card.get("last4") or "",
            "expMonth": card.get("exp_month") or "",
            "expYear": card.get("exp_year") or "",
            "funding": card.get("funding") or "",
        })

    return {
        "customerId": customer_id,
        "defaultPaymentMethodId": default_payment_method_id,
        "paymentMethods": methods,
    }


class QuoteHandler(BaseHTTPRequestHandler):
    def _send_cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/payments/config":
            ready, err = payments_ready()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors()
            self.end_headers()
            self.wfile.write(json.dumps({
                "ok": True,
                "configured": ready,
                "publishableKey": STRIPE_PUBLISHABLE_KEY if ready else "",
                "error": err,
            }).encode("utf-8"))
            return

        parsed = urlparse(self.path)
        rel_path = parsed.path.lstrip("/")
        if rel_path in {"", "index.html", "teeminus-order-form.html"}:
            target = ROOT / "teeminus-order-form.html"
            if target.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self._send_cors()
                self.end_headers()
                self.wfile.write(target.read_bytes())
                return

        target = (ROOT / rel_path).resolve()
        if not str(target).startswith(str(ROOT)):
            self.send_error(403)
            return
        if target.exists() and target.is_file():
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
            self._send_cors()
            self.end_headers()
            self.wfile.write(target.read_bytes())
            return
        self.send_error(404)

    def _read_json_body(self) -> tuple[dict | None, str | None]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
        try:
            return json.loads(raw or "{}"), None
        except json.JSONDecodeError:
            return None, "invalid-json"

    def _json_error(self, code: int, msg: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._send_cors()
        self.end_headers()
        self.wfile.write(json.dumps({"ok": False, "error": msg}).encode("utf-8"))

    def _json_ok(self, payload: dict) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._send_cors()
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, **payload}).encode("utf-8"))

    def do_POST(self) -> None:
        if self.path == "/payments/setup-intent":
            ready, err = payments_ready()
            if not ready:
                self._json_error(503, err or "payments-unavailable")
                return
            body, err = self._read_json_body()
            if err:
                self._json_error(400, err)
                return
            try:
                self._json_ok(create_setup_intent(body))
            except Exception as exc:
                self._json_error(500, str(exc))
            return

        if self.path == "/payments/default":
            ready, err = payments_ready()
            if not ready:
                self._json_error(503, err or "payments-unavailable")
                return
            body, err = self._read_json_body()
            if err:
                self._json_error(400, err)
                return
            try:
                self._json_ok(set_default_payment_method(body))
            except ValueError as exc:
                self._json_error(400, str(exc))
            except Exception as exc:
                self._json_error(500, str(exc))
            return

        if self.path == "/payments/detach":
            ready, err = payments_ready()
            if not ready:
                self._json_error(503, err or "payments-unavailable")
                return
            body, err = self._read_json_body()
            if err:
                self._json_error(400, err)
                return
            try:
                self._json_ok(detach_payment_method(body))
            except ValueError as exc:
                self._json_error(400, str(exc))
            except Exception as exc:
                self._json_error(500, str(exc))
            return

        if self.path == "/payments/list":
            ready, err = payments_ready()
            if not ready:
                self._json_error(503, err or "payments-unavailable")
                return
            body, err = self._read_json_body()
            if err:
                self._json_error(400, err)
                return
            try:
                self._json_ok(list_payment_methods(body))
            except ValueError as exc:
                self._json_error(400, str(exc))
            except Exception as exc:
                self._json_error(500, str(exc))
            return

        if self.path == "/upload-design":
            body, err = self._read_json_body()
            if err:
                self._json_error(400, err)
                return
            project_name = re.sub(r"[^\w._-]+", "_", (body.get("project_name") or "unnamed").strip())
            filename     = body.get("filename") or "design"
            raw_data     = body.get("data", "")
            try:
                file_bytes = base64.b64decode(raw_data)
            except Exception:
                self._json_error(400, "invalid-base64")
                return
            folder = f"Tee-minus/{project_name}"
            try:
                url = cloudinary_upload(file_bytes, filename, folder)
            except Exception as exc:
                self._json_error(500, str(exc))
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors()
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "url": url}).encode("utf-8"))
            return

        if self.path != "/submit":
            self.send_error(404)
            return
        body, err = self._read_json_body()
        if err:
            self._json_error(400, err)
            return

        filename = save_pdf(body)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._send_cors()
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "file": filename}).encode("utf-8"))

    def log_message(self, format, *args) -> None:
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), QuoteHandler)
    print(f"Serving Tee-Minus quote form at http://127.0.0.1:{port}/teeminus-order-form.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server")
        server.server_close()
