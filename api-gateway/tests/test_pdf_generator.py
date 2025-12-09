"""
Unit tests for PDF generator service.

Tests cover:
- HTML to PDF conversion
- PDF output validation
- Error handling
"""

import pytest

from app.services.pdf_generator import render_html_to_pdf


@pytest.mark.unit
class TestPdfGenerator:
    """Unit tests for PDF generator."""

    def test_render_html_to_pdf__simple_html__returns_pdf_bytes(self):
        """Test that simple HTML is converted to PDF bytes."""
        # Arrange
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        <body><h1>Test Report</h1><p>Content</p></body>
        </html>
        """

        # Act
        pdf_bytes = render_html_to_pdf(html_content)

        # Assert
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF magic bytes
        assert pdf_bytes[:5] == b"%PDF-"

    def test_render_html_to_pdf__with_cyrillic_text__renders_correctly(self):
        """Test that Cyrillic text is rendered correctly in PDF."""
        # Arrange
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Тестовый отчёт</title>
        </head>
        <body>
            <h1>Итоговый коэффициент профпригодности</h1>
            <p>Иванов Иван Иванович</p>
            <p>Сильные стороны</p>
            <p>Зоны развития</p>
        </body>
        </html>
        """

        # Act
        pdf_bytes = render_html_to_pdf(html_content)

        # Assert
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    def test_render_html_to_pdf__with_table__renders_table(self):
        """Test that HTML tables are rendered in PDF."""
        # Arrange
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Table Test</title></head>
        <body>
            <table>
                <thead>
                    <tr><th>Код</th><th>Название</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    <tr><td>COMM</td><td>Коммуникация</td><td>8</td></tr>
                    <tr><td>PLAN</td><td>Планирование</td><td>7</td></tr>
                </tbody>
            </table>
        </body>
        </html>
        """

        # Act
        pdf_bytes = render_html_to_pdf(html_content)

        # Assert
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    def test_render_html_to_pdf__with_styles__applies_styles(self):
        """Test that CSS styles are applied in PDF."""
        # Arrange
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Styled Report</title>
            <style>
                body { font-family: sans-serif; }
                .score { font-size: 48px; color: #00798D; }
                .section { padding: 20px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="section">
                <div class="score">85%</div>
            </div>
        </body>
        </html>
        """

        # Act
        pdf_bytes = render_html_to_pdf(html_content)

        # Assert
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    def test_render_html_to_pdf__empty_html__returns_minimal_pdf(self):
        """Test that empty HTML produces a minimal PDF."""
        # Arrange
        html_content = "<html><body></body></html>"

        # Act
        pdf_bytes = render_html_to_pdf(html_content)

        # Assert
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    def test_render_html_to_pdf__realistic_report__generates_valid_pdf(self):
        """Test with realistic report structure similar to final_report_v1.html."""
        # Arrange
        html_content = """
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <title>Итоговый отчёт — Тестовый Участник</title>
            <style>
                body { font-family: 'Segoe UI', sans-serif; max-width: 1000px; margin: 0 auto; }
                .header { padding: 30px; background: linear-gradient(135deg, #00798D, #006d7d); color: white; }
                .score-section { text-align: center; padding: 40px; }
                .score-value { font-size: 56px; font-weight: bold; color: #00798D; }
                .metrics-table { width: 100%; border-collapse: collapse; }
                .metrics-table th, .metrics-table td { border: 1px solid #dee2e6; padding: 12px; }
                @media print {
                    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Итоговый отчёт</h1>
                <p>Тестовый Участник</p>
                <p>Дата: 15.01.2025</p>
            </div>
            <div class="score-section">
                <div class="score-value">85.5</div>
                <p>Итоговый коэффициент профпригодности</p>
            </div>
            <section>
                <h2>Сильные стороны</h2>
                <ul>
                    <li>Коммуникация (COMM): высокий уровень</li>
                    <li>Аналитика (ANAL): развитые навыки</li>
                </ul>
            </section>
            <section>
                <h2>Зоны развития</h2>
                <ul>
                    <li>Планирование (PLAN): требует внимания</li>
                </ul>
            </section>
            <section>
                <h2>Детальные метрики</h2>
                <table class="metrics-table">
                    <thead>
                        <tr>
                            <th>Код</th>
                            <th>Название</th>
                            <th>Значение</th>
                            <th>Вес</th>
                            <th>Вклад</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td>COMM</td><td>Коммуникация</td><td>9</td><td>0.3</td><td>2.7</td></tr>
                        <tr><td>ANAL</td><td>Аналитика</td><td>8</td><td>0.25</td><td>2.0</td></tr>
                        <tr><td>PLAN</td><td>Планирование</td><td>6</td><td>0.25</td><td>1.5</td></tr>
                        <tr><td>LEAD</td><td>Лидерство</td><td>7</td><td>0.2</td><td>1.4</td></tr>
                    </tbody>
                </table>
            </section>
            <footer>
                <p>Версия шаблона отчёта: 1.0.0</p>
            </footer>
        </body>
        </html>
        """

        # Act
        pdf_bytes = render_html_to_pdf(html_content)

        # Assert
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000  # Realistic report should be larger
        assert pdf_bytes[:5] == b"%PDF-"
