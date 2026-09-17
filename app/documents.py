"""Render only the customer-facing, server-calculated quote projection."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def render_pdf(quote):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=(210 * mm, 297 * mm),
                            rightMargin=18 * mm, leftMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    body = styles['BodyText']
    content = [Paragraph('QUOTATION' + (' / DRAFT' if quote['draft'] else ''), styles['Title']),
               Paragraph(escape(quote['seller']), styles['Heading2']),
               Paragraph('Synthetic demo / fixture date ' + quote['fixture_date'], body),
               Spacer(1, 8 * mm),
               Paragraph(escape(quote['id']) + ' / Revision ' + str(quote['revision']), body),
               Paragraph(escape(quote['customer']), styles['Heading3']),
               Paragraph('Attention: ' + escape(quote['recipient']), body),
               Spacer(1, 6 * mm)]
    rows = [['Product', 'Qty', 'Unit SGD', 'Amount SGD']]
    for line in quote['lines']:
        rows.append([Paragraph(escape(line['name']) + '<br/>' + escape(line['sku']), body),
                     str(line['qty']) + ' ' + line['uom'], line['unit_price'], line['amount']])
    table = Table(rows, colWidths=[87 * mm, 23 * mm, 30 * mm, 34 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f0ec')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#d9dfdb')),
        ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 10)]))
    content.extend([table, Spacer(1, 6 * mm)])
    for label, value in [('Subtotal', quote['subtotal']), ('Freight', '0.00'), ('Mock GST 9%', quote['tax']), ('Total SGD', quote['total'])]:
        content.append(Paragraph(label + ': ' + value, styles['Heading3'] if label == 'Total SGD' else body))
    content.extend([Spacer(1, 6 * mm), Paragraph('Payment: Net 30. Valid until ' + quote['valid_until'] + '.', body),
                    Paragraph('Delivery: Jurong. In-stock lines on 19 September 2026. No inventory reservation.', body)])
    for split in quote['delivery']:
        content.append(Paragraph(escape(split['sku']) + ': ' + str(split['now']) + ' on 19 September; ' + str(split['later']) + ' on ' + split['eta'] + ', split accepted.', body))
    content.append(Paragraph('Demonstration only. Not a commercial offer. No external sending.', body))
    doc.build(content)
    return output.getvalue()


def email_draft(quote):
    return (f'Subject: Quotation {quote["id"]} - Acme Facilities\n\n'
            f'Dear {quote["recipient"]},\n\n'
            f'Please find quotation {quote["id"]}, revision {quote["revision"]}, '
            f'for SGD {quote["total"]} including mock GST.\n'
            f'Payment terms: Net 30. Valid until {quote["valid_until"]}.\n'
            'Please refer to the quotation for line items and delivery arrangements.\n\n'
            'QuoteFlow Demo Supplies Pte Ltd\n\n'
            'SYNTHETIC DEMO - not sent, not a commercial offer.\n')
