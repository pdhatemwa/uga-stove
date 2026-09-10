import io
from xml.sax.saxutils import escape

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from api.config import get_settings

BLUE = colors.HexColor("#9DC3E6")
INK = colors.HexColor("#172033")
LIGHT = colors.HexColor("#F4F7FA")


def _p(value, style):
    return Paragraph(escape("" if value is None else str(value)), style)


def _qr_image(value: str) -> Image:
    image = qrcode.make(value)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return Image(buffer, width=22 * mm, height=22 * mm)


def _data_table(rows, widths, row_heights=None):
    table = Table(rows, colWidths=widths, rowHeights=row_heights)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#444444")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build_record_pdf(record) -> bytes:
    settings = get_settings()
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f"UGA Stove {record.household.household_uid}",
        author=settings.app_name,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "DocumentTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=20,
        alignment=TA_CENTER,
        textColor=INK,
    )
    section = ParagraphStyle(
        "Section",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
    )
    label = ParagraphStyle(
        "Label", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8.5, leading=10
    )
    value = ParagraphStyle("Value", parent=styles["BodyText"], fontSize=8.5, leading=10)
    body = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontSize=8.7, leading=11, alignment=TA_LEFT
    )
    centered = ParagraphStyle("Centered", parent=body, alignment=TA_CENTER)

    h = record.household
    s = record.stove
    d = record
    point = record.distribution_point
    verify_url = f"{settings.app_base_url.rstrip('/')}?verify={d.verification_code}"
    story = []

    header = Table(
        [
            [
                Paragraph(
                    "GS13031: Making Carbon Count<br/>Improved Cooking in Uganda<br/>"
                    "Stove Participation Form",
                    title,
                )
            ]
        ],
        colWidths=[186 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BLUE),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#444444")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([header, Spacer(1, 3 * mm)])

    story.append(Paragraph("Household data", section))
    story.append(
        _data_table(
            [
                [
                    _p("Family or household head", label),
                    _p("Household members", label),
                    _p("Mobile number", label),
                    _p("Additional contact", label),
                ],
                [
                    _p(h.family_name or h.household_head_name, value),
                    _p(h.household_size, value),
                    _p(h.phone_number, value),
                    _p(h.additional_contact, value),
                ],
            ],
            [52 * mm, 38 * mm, 44 * mm, 52 * mm],
            [9 * mm, 16 * mm],
        )
    )
    story.append(Spacer(1, 2.5 * mm))
    story.append(Paragraph("Current cooking data", section))
    story.append(
        _data_table(
            [
                [
                    _p("Existing stove type", label),
                    _p("Fuel type", label),
                    _p("Number of units", label),
                    _p("Fuel used per week", label),
                ],
                [
                    _p(h.existing_stove_type_1, value),
                    _p(h.fuel_type, value),
                    _p(h.existing_stove_units, value),
                    _p(h.fuel_amount_per_week, value),
                ],
                [_p(h.existing_stove_type_2, value), _p("", value), _p("", value), _p("", value)],
            ],
            [52 * mm, 38 * mm, 44 * mm, 52 * mm],
            [9 * mm, 12 * mm, 12 * mm],
        )
    )
    story.append(Spacer(1, 2.5 * mm))
    story.append(Paragraph("New project improved cook stove data", section))
    story.append(
        _data_table(
            [
                [
                    _p("Type and size", label),
                    _p("Serial number", label),
                    _p("Date of distribution", label),
                    _p("Household unique ID", label),
                ],
                [
                    _p(f"{s.stove_type}, {s.stove_size}", value),
                    _p(s.serial_number, value),
                    _p(d.distributed_on.isoformat(), value),
                    _p(h.household_uid, value),
                ],
            ],
            [52 * mm, 46 * mm, 42 * mm, 46 * mm],
            [9 * mm, 16 * mm],
        )
    )
    story.append(Spacer(1, 2.5 * mm))
    story.append(Paragraph("Additional data", section))
    gps = "" if h.latitude is None else f"{h.latitude:.6f}, {h.longitude:.6f}"
    story.append(
        _data_table(
            [
                [
                    _p("Location or village", label),
                    _p("Subcounty and district", label),
                    _p("GPS location", label),
                    _p("Existing stove removed", label),
                ],
                [
                    _p(f"{h.village}, {h.parish}", value),
                    _p(f"{h.subcounty}, {h.district}", value),
                    _p(gps, value),
                    _p(
                        "Yes"
                        if h.existing_stoves_removed
                        else "No"
                        if h.existing_stoves_removed is False
                        else "",
                        value,
                    ),
                ],
            ],
            [52 * mm, 50 * mm, 46 * mm, 38 * mm],
            [9 * mm, 16 * mm],
        )
    )
    story.append(Spacer(1, 3 * mm))
    waiver = (
        "The beneficiary confirms receiving the project improved cook stove from Pro Sphera "
        "free of charge and transfers the carbon credits generated through its use to Pro Sphera, "
        "subject to the agreed project terms."
    )
    waiver_table = Table(
        [[Paragraph("Carbon Emission Waiver", section), Paragraph(waiver, body)]],
        colWidths=[38 * mm, 148 * mm],
    )
    waiver_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#444444")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(waiver_table)
    story.append(Spacer(1, 3 * mm))
    signature_rows = [
        [
            Paragraph("Signatures", section),
            _p("Beneficiary", label),
            "",
            _p("Ambassador", label),
            "",
        ],
        ["", "", "", "", ""],
    ]
    sig = Table(
        signature_rows,
        colWidths=[34 * mm, 34 * mm, 48 * mm, 32 * mm, 38 * mm],
        rowHeights=[10 * mm, 25 * mm],
    )
    sig.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#444444")),
                ("SPAN", (0, 0), (0, 1)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story.extend([sig, Spacer(1, 2 * mm)])
    verify = Table(
        [
            [
                _qr_image(verify_url),
                Paragraph(
                    f"Verification code: <b>{escape(d.verification_code)}</b><br/>"
                    f"Distribution point: {escape(point.name)}<br/>"
                    f"Signature status: {escape(d.signature_status.value.title())}",
                    body,
                ),
            ]
        ],
        colWidths=[28 * mm, 158 * mm],
    )
    verify.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([verify, PageBreak()])

    certificate_header = Table(
        [[Paragraph("Beneficiary Certificate", title)]], colWidths=[186 * mm]
    )
    certificate_header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BLUE),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#444444")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([certificate_header, Spacer(1, 3 * mm)])
    story.append(
        _data_table(
            [
                [
                    _p("Family or household head", label),
                    _p("Household members", label),
                    _p("Mobile number", label),
                    _p("Additional contact", label),
                ],
                [
                    _p(h.family_name or h.household_head_name, value),
                    _p(h.household_size, value),
                    _p(h.phone_number, value),
                    _p(h.additional_contact, value),
                ],
            ],
            [52 * mm, 38 * mm, 44 * mm, 52 * mm],
            [12 * mm, 20 * mm],
        )
    )
    story.append(Spacer(1, 2.5 * mm))
    story.append(
        _data_table(
            [
                [
                    _p("Type and size", label),
                    _p("Serial number", label),
                    _p("Date of distribution", label),
                    _p("Household unique ID", label),
                ],
                [
                    _p(f"{s.stove_type}, {s.stove_size}", value),
                    _p(s.serial_number, value),
                    _p(d.distributed_on.isoformat(), value),
                    _p(h.household_uid, value),
                ],
            ],
            [52 * mm, 46 * mm, 42 * mm, 46 * mm],
            [12 * mm, 20 * mm],
        )
    )
    story.append(Spacer(1, 5 * mm))
    conditions = [
        "The beneficiary shall use the project improved cook stove for the household's "
        "personal use.",
        "The beneficiary will allow agreed project monitoring access to confirm that the stove "
        "remains in proper use.",
        "If the stove malfunctions or breaks, the beneficiary will contact Pro Sphera and will "
        "not dispose of or transfer it to another user.",
    ]
    for index, text in enumerate(conditions, start=1):
        story.append(Paragraph(f"<b>{index}.</b> {escape(text)}", body))
        story.append(Spacer(1, 2 * mm))
    story.append(Spacer(1, 5 * mm))
    participation = (
        f"We confirm that <b>{escape(h.household_head_name)}</b> is participating in GS13031: "
        "Making Carbon Count, Improved Cooking in Uganda. The household received an improved cook "
        "stove intended to reduce firewood consumption, household fuel costs, smoke exposure, and "
        "pressure on nearby forests."
    )
    story.extend([Paragraph(participation, body), Spacer(1, 7 * mm)])
    story.append(Paragraph("For stove support, call +256 782 401 544.", centered))
    story.append(Spacer(1, 7 * mm))
    story.append(sig)
    story.append(Spacer(1, 5 * mm))
    story.append(verify)

    doc.build(story)
    return output.getvalue()
