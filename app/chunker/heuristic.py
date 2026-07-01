import re
from app.models import Page, Section, RawDocument

SECTION_MARKERS = [
    (r"(?i)\bdeckblatt\b|\btitelseite\b|\banschreiben\b", 1, 0.90),
    (r"(?i)\bkostenübersicht\b|\bgesamtkosten\b|\bzusammenstellung\b|\babrechnungsergebnis\b", 1, 0.90),
    (r"(?i)\bverteilerschlüssel\b|\bumlageschlüssel\b|\bverteilungsschlüssel\b", 1, 0.85),
    (r"(?i)\bheizung\b|\bheizkosten\b|\bwärmekosten\b|\bheizenergie\b|\bwärmeversorgung\b|\bbrennstoff\b", 1, 0.90),
    (r"(?i)\bwarmwasser\b|\bwarmwasserkosten\b|\bwarmwasserbereitung\b", 1, 0.90),
    (r"(?i)\bkaltwasser\b|\bwasserverbrauch\b|\bwasserkosten\b|\btrinkwasser\b|\bfrischwasser\b", 1, 0.85),
    (r"(?i)\babwasser\b|\bentwässerung\b|\bschmutzwasser\b|\bniederschlagswasser\b", 1, 0.85),
    (r"(?i)\bgrundsteuer\b|\bgrundbesitzabgaben\b", 1, 0.90),
    (r"(?i)\bversicherung\b|\bhaftpflicht\b|\bsachversicherung\b|\bgebäudeversicherung\b|\bfeuerversicherung\b", 1, 0.85),
    (r"(?i)\b(?<!CO₂)strom\b|\ballgemeinstrom\b|\belelektrizität\b", 1, 0.85),
    (r"(?i)\bobjektbetreuung\b|\bhausmeister\b|\bverwaltungskosten\b", 1, 0.80),
    (r"(?i)\baufzug\b|\bfahrstuhl\b|\blift\b", 1, 0.90),
    (r"(?i)\breinigung\b|\bhausreinigung\b|\btreppenhausreinigung\b|\bputzdienst\b", 1, 0.85),
    (r"(?i)\bgarten\b|\bgartenpflege\b|\baußenanlage\b|\bgrünanlage\b", 1, 0.85),
    (r"(?i)\bschornsteinfeger\b|\bschornsteinreinigung\b|\bkaminfeger\b", 1, 0.90),
    (r"(?i)\bmüll\b|\babfall\b|\bmüllabfuhr\b|\babfallentsorgung\b|\bmüllentsorgung\b", 1, 0.85),
    (r"(?i)\bhauswart\b|\bgehwegreinigung\b|\bwinterdienst\b|\bschneeräumung\b", 1, 0.80),
    (r"(?i)\buntermieter\b|\bnutzereinheiten\b|\beinheitenübersicht\b|\bmietparteien\b", 1, 0.80),
    (r"(?i)\bunterschrift\b|\bgezeichnet\b|\bfür rückfragen\b|\banhang\b|\bimpressum\b", 1, 0.70),
]


def detect_sections(doc: RawDocument) -> tuple[list[Section], float]:
    if not doc.pages:
        return [], 0.0

    sections: list[Section] = []
    current_start = 1
    current_title = "Deckblatt"
    current_level = 1
    current_confidence = 0.7
    has_new_section = False

    for i, page in enumerate(doc.pages):
        page_num = i + 1
        title, level, conf, is_new = _classify_page(page)

        if is_new and not has_new_section:
            current_title = title
            current_level = level
            current_confidence = conf
            has_new_section = True
            continue

        if is_new:
            sections.append(Section(
                title=current_title,
                level=current_level,
                start_page=current_start,
                end_page=page_num - 1,
                confidence=current_confidence,
            ))
            current_start = page_num
            current_title = title
            current_level = level
            current_confidence = conf

    sections.append(Section(
        title=current_title,
        level=current_level,
        start_page=current_start,
        end_page=len(doc.pages),
        confidence=current_confidence,
    ))

    overall = sum(s.confidence for s in sections) / max(len(sections), 1)
    return sections, round(overall, 2)


def _classify_page(page: Page) -> tuple[str, int, float, bool]:
    combined = page.text
    for t in page.tables:
        for row in t.rows:
            combined += " " + " ".join(str(v) for v in row.values())

    for pattern, level, base_conf in SECTION_MARKERS:
        match = re.search(pattern, combined)
        if match:
            title = match.group(0)
            conf = base_conf + 0.03
            return title, level, min(conf, 1.0), True

    if page.tables:
        return f"Tabelle (Seite {page.number})", 2, 0.60, True

    return "", 1, 0.30, False
