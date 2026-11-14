#!/usr/bin/env python3
"""Render the source-backed fresh-Fury guide as a printable PDF."""
import html
from pathlib import Path
import re
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Preformatted, Image, Table, TableStyle, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
BLUE = colors.HexColor('#004BDF')
INK = colors.HexColor('#182B3C')
MUTED = colors.HexColor('#526A80')


def main():
    fonts = Path('/usr/share/fonts/truetype/dejavu')
    for name, filename in [('Guide', 'DejaVuSans.ttf'), ('GuideBold', 'DejaVuSans-Bold.ttf'), ('GuideMono', 'DejaVuSansMono.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    pdfmetrics.registerFontFamily('Guide', normal='Guide', bold='GuideBold', italic='Guide', boldItalic='GuideBold')
    styles = {
        'body': ParagraphStyle('body', fontName='Guide', fontSize=9.2, leading=14.5, textColor=INK, spaceAfter=10),
        'small': ParagraphStyle('small', fontName='Guide', fontSize=8, leading=12, textColor=MUTED, spaceAfter=9),
        'heading': ParagraphStyle('heading', fontName='GuideBold', fontSize=23, leading=29, textColor=INK, spaceAfter=19),
        'cover': ParagraphStyle('cover', fontName='GuideBold', fontSize=44, leading=49, textColor=INK, spaceAfter=12),
        'subtitle': ParagraphStyle('subtitle', fontName='Guide', fontSize=21, leading=28, textColor=MUTED, spaceAfter=24),
        'eyebrow': ParagraphStyle('eyebrow', fontName='GuideBold', fontSize=9, leading=14, textColor=BLUE, spaceAfter=14),
        'code': ParagraphStyle('code', fontName='GuideMono', fontSize=7.1, leading=11, textColor=colors.HexColor('#163C68'), backColor=colors.HexColor('#F0F5FC'), borderPadding=9, spaceBefore=6, spaceAfter=15),
    }
    def markup(text):
        escaped = html.escape(text)
        escaped = re.sub(r'`([^`]+)`', r'<font name="GuideMono">\1</font>', escaped)
        escaped = re.sub(r'(https://[^\s<]+)', lambda m: '<link href="'+m.group(1)+'" color="#004BDF">'+m.group(1)+'</link>', escaped)
        return escaped
    story = [Spacer(1,25), Paragraph('PLANT 7 · INSIDE THE LINE', styles['eyebrow']),
             Paragraph('A fresh Fury.<br/>A smooth first launch.', styles['cover']),
             Paragraph('Installation, live inference<br/>and the five-step walkthrough', styles['subtitle'])]
    shot = ROOT / 'docs/captures/guided/value-1366x768.png'
    if shot.exists():
        story += [Image(str(shot), width=475, height=267), Spacer(1,18)]
    story += [Paragraph('VERSION 1.1.0 · 14 NOVEMBER 2026', styles['eyebrow']),
              Paragraph('<link href="https://github.com/Navigatedhustle/plant7-inside-the-line/releases/tag/v1.1.0" color="#004BDF">Open the private GitHub release and downloads ↗</link>', styles['body']),
              Paragraph('Private owner-authorized handoff. Application, media, synthetic evidence and offline Python dependencies included. Pinned live model weights and serving image are downloaded by the live installer.', styles['body']),
              Paragraph('Ubuntu 24.04 ARM64 · Python 3.12 · Compatible SM 10.3 Fury GPU for live inference. Recorded mode works without Docker or a GPU.', styles['small'])]
    text = (ROOT / 'docs/FRESH_FURY.md').read_text()
    lines = text.splitlines()
    buffer, code, in_code, in_section = [], [], False, False
    def flush():
        if buffer:
            story.append(Paragraph(markup(' '.join(buffer)), styles['body']));buffer.clear()
    for line in lines:
        if line.startswith('```'):
            flush()
            if in_code:
                longest = max(map(len, code), default=1)
                style = ParagraphStyle('sized-code', parent=styles['code'], fontSize=min(7.1, 470 / (longest * .61)), leading=11)
                story.append(KeepTogether([Preformatted('\n'.join(code), style)]));code=[]
            in_code = not in_code
            continue
        if in_code:
            code.append(line);continue
        if line.startswith('# '):
            continue
        if line.startswith('## '):
            flush();story.append(PageBreak());story.append(Paragraph('FRESH FURY INSTALLATION', styles['eyebrow']));story.append(Paragraph(markup(line[3:]), styles['heading']));in_section=True;continue
        if not in_section:
            continue  # Cover contains the introductory summary.
        if not line.strip():
            flush();continue
        if line.startswith('- '):
            flush();story.append(Paragraph('• '+markup(line[2:]),styles['body']));continue
        buffer.append(line)
    flush()
    target = ROOT / 'docs/Plant7-Fresh-Fury-Guide.pdf'
    def chrome(canvas, doc):
        w,h=A4
        canvas.setStrokeColor(colors.HexColor('#DCE4EB'));canvas.line(42,41,w-42,41)
        canvas.setFillColor(MUTED);canvas.setFont('Guide',7.3)
        canvas.drawString(42,28,'Plant 7: Inside the Line · v1.1.0 · Private handoff')
        canvas.drawRightString(w-42,28,str(doc.page))
        if doc.page>1:
            canvas.setFillColor(BLUE);canvas.rect(0,h-8,w,8,fill=1,stroke=0)
    doc=SimpleDocTemplate(str(target), pagesize=A4, rightMargin=42, leftMargin=42, topMargin=43, bottomMargin=57,
                          title='Plant 7 · Fresh Fury Installation & Launch', author='Plant 7 project', subject='Version 1.1.0 private handoff installation guide')
    doc.build(story,onFirstPage=chrome,onLaterPages=chrome)
    print(target)


if __name__ == '__main__':
    main()
