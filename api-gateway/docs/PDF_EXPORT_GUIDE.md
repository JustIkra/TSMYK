# PDF Export Feature Guide

## Overview

The PDF export feature allows users to download final proficiency assessment reports in PDF format. This feature is implemented using WeasyPrint library which converts HTML reports to high-quality PDF documents.

## Changes Made

### 1. Added Dependencies

**File:** `/api-gateway/requirements.txt`
- Added `weasyprint==63.1` in DOCX Processing section

**File:** `/api-gateway/Dockerfile`
- Added system dependencies required by WeasyPrint:
  - `libpango-1.0-0` - Text layout and rendering
  - `libpangocairo-1.0-0` - Cairo backend for Pango
  - `libgdk-pixbuf2.0-0` - Image loading
  - `libffi-dev` - Foreign function interface
  - `shared-mime-info` - MIME type detection

### 2. Created PDF Generator Service

**File:** `/api-gateway/app/services/pdf_generator.py`

```python
def render_html_to_pdf(html_content: str) -> bytes:
    """
    Convert HTML content to PDF bytes using WeasyPrint.

    Features:
    - A4 page size with 2cm margins
    - Font configuration for proper text rendering
    - Logging of generated PDF size
    """
```

### 3. Updated Router

**File:** `/api-gateway/app/routers/participants.py`

Changes:
- Added `Response` import from `fastapi.responses`
- Updated `format` query parameter description to include 'pdf'
- Added PDF generation logic:
  ```python
  if format == "pdf":
      html_content = render_final_report_html(report_data)
      pdf_bytes = render_html_to_pdf(html_content)
      return Response(
          content=pdf_bytes,
          media_type="application/pdf",
          headers={
              "Content-Disposition": f'attachment; filename="report_{participant_id}_{activity_code}.pdf"'
          }
      )
  ```

### 4. Enhanced HTML Template

**File:** `/api-gateway/app/templates/final_report_v1.html`

Added print-friendly CSS:
```css
@media print {
    body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
    .score-section, .item, .dev-area-item, .recommendation {
        break-inside: avoid;
    }
}
```

This ensures:
- Colors are preserved in PDF
- Sections don't break across pages

## API Usage

### Endpoint

```
GET /api/participants/{participant_id}/final-report?activity_code={code}&format=pdf
```

### Parameters

- `participant_id` (path, UUID) - Participant identifier
- `activity_code` (query, string) - Professional activity code
- `format` (query, string) - Output format: "json", "html", or "pdf" (default: "json")

### Response

**Success (200 OK)**
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="report_{participant_id}_{activity_code}.pdf"`
- Body: Binary PDF content

**Error Responses**
- 400: No scoring result found (calculate score first)
- 404: Participant or activity not found
- 401: Unauthorized (requires authentication)

## Testing

### 1. Local Development (requires system dependencies)

**Install system dependencies (macOS):**
```bash
brew install pango cairo gdk-pixbuf libffi
```

**Install system dependencies (Ubuntu/Debian):**
```bash
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

**Install Python dependencies:**
```bash
cd api-gateway
pip install -r requirements.txt
```

**Test PDF generation:**
```bash
python3 -c "from app.services.pdf_generator import render_html_to_pdf; print('PDF generator OK')"
```

### 2. Docker Testing (Recommended)

Docker image includes all required system dependencies.

**Rebuild and start services:**
```bash
docker-compose build
docker-compose up -d
```

**Test endpoint:**
```bash
# Get authentication token
TOKEN=$(curl -X POST http://localhost:9187/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}' \
  | jq -r '.access_token')

# Get participant ID
PARTICIPANT_ID=$(curl -s http://localhost:9187/api/participants \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.items[0].id')

# Download PDF report
curl -o report.pdf "http://localhost:9187/api/participants/${PARTICIPANT_ID}/final-report?activity_code=PROF001&format=pdf" \
  -H "Authorization: Bearer $TOKEN"

# Verify PDF was created
file report.pdf
# Expected output: report.pdf: PDF document, version 1.X
```

### 3. Integration Test

**File:** `/api-gateway/tests/test_pdf_export.py` (to be created)

```python
import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_pdf_export(client: AsyncClient, auth_token: str, participant_id: str):
    """Test PDF export endpoint."""
    response = await client.get(
        f"/api/participants/{participant_id}/final-report",
        params={"activity_code": "PROF001", "format": "pdf"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert len(response.content) > 1000  # Non-empty PDF
    assert response.content.startswith(b"%PDF")  # PDF magic number
```

## Troubleshooting

### Issue: "cannot load library 'libgobject-2.0-0'"

**Cause:** System dependencies not installed

**Solution:**
- For local development: Install system packages (see Testing section)
- For Docker: Rebuild image with `docker-compose build --no-cache`

### Issue: "PDF is blank or missing content"

**Cause:** HTML template issues or CSS conflicts

**Solution:**
1. Test HTML format first: `format=html`
2. Verify HTML renders correctly in browser
3. Check WeasyPrint logs for CSS warnings

### Issue: "File size too large"

**Cause:** Large images or complex CSS

**Solution:**
- Optimize images in report
- Review CSS for unnecessary rules
- Consider pagination for very long reports

## Performance Considerations

- PDF generation is synchronous and blocks the response
- Average generation time: 1-3 seconds per report
- For bulk exports, consider using Celery background tasks

## Future Enhancements

1. **Async PDF Generation:** Move to Celery task for bulk exports
2. **Custom Templates:** Support multiple PDF layouts
3. **Digital Signatures:** Add cryptographic signatures to PDFs
4. **Watermarks:** Add organization branding
5. **Compression:** Optimize PDF file size

## References

- [WeasyPrint Documentation](https://doc.courtbouillon.org/weasyprint/stable/)
- [WeasyPrint Installation Guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)
- [PDF/A Standard](https://en.wikipedia.org/wiki/PDF/A) - For archival quality PDFs
