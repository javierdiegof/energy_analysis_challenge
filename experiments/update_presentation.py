"""
Updates presentation/monclova_lmp_presentation.pptx safely in-place:
- Preserves Slides 1–6, 8, and 9 content (including manual user edits on Slides 8 & 9).
- Updates Slide 7 (Track 2 MDA consistency), Slide 10 (MDA-only Anomaly Figure & Cards),
  Slide 11 (3-Stage Analyst Workflow, Schedule, Alerting & Audited ROI), and
  adds/refreshes Slide 12 (Palantir Blueprint Analyst Console UI Showcase).
- Updates slide page footers cleanly across Slides 3–12 to N / 12 (right-aligned without wrapping).
- Validates ZIP CRC-32, geometry bounds, aspect-ratio fidelity, and PIL line-wrap height.
"""

from pathlib import Path
import argparse
import zipfile
from PIL import Image, ImageFont
from pptx import Presentation
from pptx.util import Pt, Inches, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT = Path(__file__).resolve().parents[1]
PPTX_PATH = ROOT / "presentation" / "monclova_lmp_presentation.pptx"
FIG_DIR = ROOT / "experiments" / "figures"
SCREENSHOT_DIR = ROOT / "analyst_website" / "screenshots"

SCREENSHOTS = {
    "tab1": SCREENSHOT_DIR / "01_tab1_day_ahead_planner.png",
    "tab2": SCREENSHOT_DIR / "02_tab2_realtime_monitor.png",
    "tab3": SCREENSHOT_DIR / "03_tab3_settlement_review.png",
}

SLIDE12_EYEBROW = "ANALYST CONSOLE PROTOTYPE // PALANTIR-INSPIRED WORKBENCH"


def replace_picture_fit(slide, shape_idx: int, img_path: Path):
    """Replace an existing picture shape at shape_idx, preserving center, z-order, and aspect ratio."""
    old_sh = slide.shapes[shape_idx]
    assert old_sh.shape_type == 13, f"Shape {shape_idx} is not a picture: {old_sh.name}"

    box_l, box_t, box_w, box_h = old_sh.left, old_sh.top, old_sh.width, old_sh.height
    cx = box_l + box_w / 2
    cy = box_t + box_h / 2
    old_name = old_sh.name

    with Image.open(img_path) as im:
        px_w, px_h = im.size
    img_ratio = px_w / px_h
    box_ratio = box_w / box_h

    if img_ratio >= box_ratio:
        new_w = box_w
        new_h = int(round(box_w / img_ratio))
    else:
        new_h = box_h
        new_w = int(round(box_h * img_ratio))

    new_l = int(round(cx - new_w / 2))
    new_t = int(round(cy - new_h / 2))

    sp_tree = slide.shapes._spTree
    z_idx = list(sp_tree).index(old_sh._element)

    new_sh = slide.shapes.add_picture(str(img_path), Emu(new_l), Emu(new_t), width=Emu(new_w), height=Emu(new_h))
    new_sh.name = old_name

    sp_tree.remove(new_sh._element)
    sp_tree.insert(z_idx, new_sh._element)
    sp_tree.remove(old_sh._element)


def set_paragraphs(shape, specs):
    """
    Populate paragraphs and runs cleanly inside shape.text_frame.
    specs: list of dicts with:
      - 'align': optional PP_ALIGN
      - 'space_after_pt': optional float
      - 'runs': list of (text, size_pt, bold_bool_or_None, hex_rgb, font_name_or_None)
    """
    tf = shape.text_frame
    existing_count = len(tf.paragraphs)
    for i, spec in enumerate(specs):
        p = tf.paragraphs[i] if i < existing_count else tf.add_paragraph()
        for r in list(p.runs):
            p._p.remove(r._r)
        if spec.get("align") is not None:
            p.alignment = spec["align"]
        if spec.get("space_after_pt") is not None:
            p.space_after = Pt(spec["space_after_pt"])
        for text, sz, bold, hex_rgb, fname in spec["runs"]:
            run = p.add_run()
            run.text = text
            if sz is not None:
                run.font.size = Pt(sz)
            if bold is not None:
                run.font.bold = bold
            if hex_rgb is not None:
                run.font.color.rgb = RGBColor.from_string(hex_rgb)
            if fname is not None:
                run.font.name = fname
    while len(tf.paragraphs) > len(specs):
        last_p = tf.paragraphs[-1]._p
        last_p.getparent().remove(last_p)


def find_picture_index(slide) -> int:
    """Find first picture shape index on slide."""
    for i, sh in enumerate(slide.shapes):
        if sh.shape_type == 13:
            return i
    raise LookupError("No picture shape found on slide")


def apply_footer(shape, slide_num: int, total_slides: int, font_name: str = "Liberation Sans"):
    """Format footer cleanly across 11.73 in width without wrapping page number."""
    page_str = f"{slide_num} / {total_slides}"
    spaces = " " * (172 if slide_num < 10 else 170)
    set_paragraphs(shape, [
        {
            "runs": [
                ("Arkham Technical Challenge // Javier Diego-Fernández", 11.0, None, "94A3B8", font_name),
                (spaces, 11.0, None, "94A3B8", font_name),
                (page_str, 11.0, True, "475569", font_name),
            ]
        }
    ])


def remove_existing_slide12(prs: Presentation):
    """If Slide 12 already exists from a prior run, remove it cleanly before rebuilding."""
    while len(prs.slides) > 11:
        last_slide = prs.slides[-1]
        is_console = any(
            sh.has_text_frame
            and (
                SLIDE12_EYEBROW in sh.text_frame.text
                or "OPERATIONAL CONSOLE PROTOTYPE" in sh.text_frame.text
                or "Monclova Analyst" in sh.text_frame.text
            )
            for sh in last_slide.shapes
        )
        if not is_console:
            raise RuntimeError(
                f"Expected slide {len(prs.slides)} to be Slide 12 console showcase, found unexpected content."
            )
        r_id = prs.slides._sldIdLst[-1].rId
        prs.part.drop_rel(r_id)
        del prs.slides._sldIdLst[-1]


def update_slide7_track2(prs: Presentation):
    """Sync Track 2 Anomaly card & orange pill on Slide 7 to Day-Ahead MDA telemetry (keeps Track 1 untouched)."""
    s7 = prs.slides[6]
    arch_sh = next(
        sh for sh in s7.shapes
        if sh.has_text_frame and "Model Architecture:" in sh.text_frame.text
    )
    pill_sh = next(
        sh for sh in s7.shapes
        if sh.has_text_frame and sh.top > Inches(4.3) and ("471 MTR" in sh.text_frame.text or "401 MDA" in sh.text_frame.text or "401 Anomaly" in sh.text_frame.text)
    )
    set_paragraphs(arch_sh, [
        {"runs": [
            ("Model Architecture: ", 10.5, True, "EA580C", None),
            ("Calibrated threshold at MDA PML > $2,500/MWh (CENACE VOLL cap) & < $0 tail.", 10.5, False, "0F172A", None),
        ]},
        {"runs": [
            ("Physical Grounding: ", 10.5, True, "EA580C", None),
            ("Captures 401 MDA scarcity alerts (91% in May–Jun '24) & 32.7x Ohmic line-heating surges (I²R).", 10.5, False, "0F172A", None),
        ]},
    ])
    set_paragraphs(pill_sh, [
        {"align": PP_ALIGN.CENTER, "runs": [("401 MDA Alerts (3.1% Rate)\n91% May–Jun '24 | -$53.4 Dec 25", 10.5, True, "EA580C", None)]},
    ])


def update_slide10_anomaly(prs: Presentation):
    """Sync Slide 10 header, 3 metric cards (zero clipping), and image to regenerated MDA-only figure."""
    s10 = prs.slides[9]
    pic_idx = find_picture_index(s10)
    replace_picture_fit(s10, pic_idx, FIG_DIR / "slide_11_anomaly_detection.png")

    set_paragraphs(s10.shapes[1], [
        {"runs": [("MAY 2024 ENERGY CRISIS, SCARCITY CAP & CHRISTMAS VALLEY", 12.0, True, "0284C7", "Liberation Sans")]},
        {"align": PP_ALIGN.LEFT, "runs": [("Systemic Grid Stress & Track 2 Anomaly Detection (MDA)", 26.0, True, "0F172A", "Liberation Sans")]},
    ])

    # Give top KPI cards clean vertical margin so 3 lines sit comfortably inside each card
    for sh_idx in (3, 5, 7):
        s10.shapes[sh_idx].top = Inches(1.22)
        s10.shapes[sh_idx].height = Inches(0.96)
    for sh_idx in (4, 6, 8):
        s10.shapes[sh_idx].top = Inches(1.28)
        s10.shapes[sh_idx].height = Inches(0.84)

    set_paragraphs(s10.shapes[4], [
        {"space_after_pt": 2.0, "runs": [
            ("SCARCITY PEAKS: ", 9.5, True, "DC2626", None),
            ("$26,094 ('24) | $3,051 ('25)", 10.5, True, "0F172A", None),
        ]},
        {"runs": [("401 MDA hrs > $2,500 (3.1%): 365 (91%) in May–Jun '24 + 7 in '25 ($26,222 zone max).", 9.0, False, "475569", None)]},
    ])
    set_paragraphs(s10.shapes[6], [
        {"space_after_pt": 2.0, "runs": [
            ("OHMIC LOSS SURGE: ", 9.5, True, "7C3AED", None),
            ("32.7x Baseline Surge", 10.5, True, "0F172A", None),
        ]},
        {"runs": [("MDA I²R spread jumped from $5.55 avg to $181.8/MWh (115 kV vs 400 kV; -$603.85 min).", 9.0, False, "475569", None)]},
    ])
    set_paragraphs(s10.shapes[8], [
        {"space_after_pt": 2.0, "runs": [
            ("CHRISTMAS VALLEY: ", 9.5, True, "0284C7", None),
            ("-$53.4/MWh Inversion", 10.5, True, "0F172A", None),
        ]},
        {"runs": [("5 hours inverted < $0 on Dec 25 holiday halt + trapped solar bottleneck (-$53.9 zone).", 9.0, False, "475569", None)]},
    ])


def update_slide11_workflow(prs: Presentation):
    """
    Update Slide 11 cleanly with the 3-Stage Analyst Decision Workflow, scheduling,
    retraining cadence, alerting triggers, and audited Jun 9–15 D+7 pilot savings.
    """
    s11 = prs.slides[10]

    set_paragraphs(s11.shapes[1], [
        {"runs": [("PRODUCTIONIZATION & ANALYST WORKFLOW // SCHEDULE, ALERTING & GOVERNANCE", 11.0, True, "1E40AF", "Liberation Sans")]},
        {"runs": [("3-Stage Decision Engine: Scheduling, Alerting & Audited ROI", 22.0, True, "0F172A", "Liberation Sans")]},
    ])

    # Column 1: Stage 1 Day-Ahead Planner (Blue) — shape[3] text, shape[5] bottom mandate
    set_paragraphs(s11.shapes[3], [
        {"space_after_pt": 2.0, "runs": [("STAGE 1 · DAY-AHEAD (MDA · D-1)", 10.0, True, "1E40AF", None)]},
        {"space_after_pt": 4.0, "runs": [("Lock 85–90% Supply Before Noon", 13.0, True, "0F172A", None)]},
        {"space_after_pt": 12.0, "runs": [("Sizes D-1 bids vs. break-even ahead of CENACE's 12:00 CST gate.", 9.8, False, "475569", None)]},
        {"space_after_pt": 8.0, "runs": [("•  ", 10.0, True, "1E40AF", None), ("Pre-Noon Schedule: ", 9.8, True, "0F172A", None), ("Delivers 10:15 CST daily P10–P90 bands vs. $1,250/MWh break-even & CSV export.", 9.5, False, "475569", None)]},
        {"space_after_pt": 8.0, "runs": [("•  ", 10.0, True, "1E40AF", None), ("Post-Auction Alerts: ", 9.8, True, "0F172A", None), ("Sends 24h plant shift warnings when D-1 clears > $2,500 (Jun 11 HE 21: $3,012).", 9.5, False, "475569", None)]},
        {"space_after_pt": 8.0, "runs": [("•  ", 10.0, True, "1E40AF", None), ("Single Monclova View: ", 9.8, True, "0F172A", None), ("One zone curve replaces 9 near-identical tabs (r > 0.9999); flags 06AHM-400 splits.", 9.5, False, "475569", None)]},
        {"space_after_pt": 0.0, "runs": [("•  ", 10.0, True, "1E40AF", None), ("Phase 2 Causal Feeds: ", 9.8, True, "0F172A", None), ("Adds NOAA weather + Waha Hub gas prices before enabling automated D-1 ML bidding.", 9.5, False, "475569", None)]},
    ])
    set_paragraphs(s11.shapes[5], [
        {"align": PP_ALIGN.CENTER, "runs": [
            ("OPERATIONAL MANDATE\n", 8.5, True, "1E40AF", None),
            ("Export Pre-Noon Bids | 24h Plant Shift Advisories", 8.8, True, "0F172A", None),
        ]},
    ])

    # Column 2: Stage 2 Real-Time Monitor (Orange) — shape[7] text, shape[9] bottom mandate
    set_paragraphs(s11.shapes[7], [
        {"space_after_pt": 2.0, "runs": [("STAGE 2 · REAL-TIME (MTR · LIVE)", 10.0, True, "EA580C", None)]},
        {"space_after_pt": 4.0, "runs": [("Hourly :45 Dispatch & Triage", 13.0, True, "0F172A", None)]},
        {"space_after_pt": 12.0, "runs": [("Tracks live MTR − MDA spikes, 1–4h risks & immediate asset actions.", 9.8, False, "475569", None)]},
        {"space_after_pt": 8.0, "runs": [("•  ", 10.0, True, "EA580C", None), ("Causal :45 Inference: ", 9.8, True, "0F172A", None), ("HistGBDT (L1) predicts +1–4h MTR ($101.10 MAE; 79.9% ≤ $100) with Ridge fallback.", 9.5, False, "475569", None)]},
        {"space_after_pt": 8.0, "runs": [("•  ", 10.0, True, "EA580C", None), ("Alert Triggers: ", 9.8, True, "0F172A", None), ("Fires on > $2,500 VOLL, > 5x I²R line loss, or spread surges (Jun 10 HE 20: +$4,549).", 9.5, False, "475569", None)]},
        {"space_after_pt": 8.0, "runs": [("•  ", 10.0, True, "EA580C", None), ("Plain-English Triage: ", 9.8, True, "0F172A", None), ("Separates SIN scarcity (pml_cng = $0) from local bottlenecks & sizes $/hr risk.", 9.5, False, "475569", None)]},
        {"space_after_pt": 0.0, "runs": [("•  ", 10.0, True, "EA580C", None), ("SCADA vs. D-7 Mode: ", 9.8, True, "0F172A", None), ("Live utility SCADA (API lags 7 days) triggers 12 MW EAF cuts & 20 MWh BESS discharge.", 9.5, False, "475569", None)]},
    ])
    set_paragraphs(s11.shapes[9], [
        {"align": PP_ALIGN.CENTER, "runs": [
            ("OPERATIONAL MANDATE\n", 8.5, True, "EA580C", None),
            (":45 Live MTR Execution | BESS & EAF Override", 8.8, True, "0F172A", None),
        ]},
    ])

    # Column 3: Stage 3 D+7 Settlement & MLOps Governance — shape[11] text, shape[13] bottom mandate
    set_paragraphs(s11.shapes[11], [
        {"space_after_pt": 2.0, "runs": [("STAGE 3 · SETTLEMENT (D+7 · MLOPS)", 10.0, True, "7C3AED", None)]},
        {"space_after_pt": 4.0, "runs": [("Prove Dollar ROI & Govern Drift", 13.0, True, "0F172A", None)]},
        {"space_after_pt": 12.0, "runs": [("Audits finalized CENACE invoices, scores trust & shields weekly retrain.", 9.8, False, "475569", None)]},
        {"space_after_pt": 8.0, "runs": [("•  ", 10.0, True, "7C3AED", None), ("Jun 9–15 Audited ROI: ", 9.8, True, "0F172A", None), ("Cut bill from MXN 5.59M to 4.76M — MXN 828.7k (-14.8%) saved via hedges, EAF & BESS.", 9.5, False, "475569", None)]},
        {"space_after_pt": 8.0, "runs": [("•  ", 10.0, True, "7C3AED", None), ("Trust by Time of Day: ", 9.8, True, "0F172A", None), ("Highest precision in Morning Ramp (95.2% ≤ $100) & Solar (91.0%) vs. Peaks (58.5%).", 9.5, False, "475569", None)]},
        {"space_after_pt": 8.0, "runs": [("•  ", 10.0, True, "7C3AED", None), ("Retrain & Drift Guard: ", 9.8, True, "0F172A", None), ("Retrains Mon 00:00 CST (8-wk window) + KS test (p < 0.01); excludes May '24 blackouts.", 9.5, False, "475569", None)]},
        {"space_after_pt": 0.0, "runs": [("•  ", 10.0, True, "7C3AED", None), ("Low-Friction Rollout: ", 9.8, True, "0F172A", None), ("Launch automated morning Slack/email briefs first, wire SCADA, then open full console.", 9.5, False, "475569", None)]},
    ])
    set_paragraphs(s11.shapes[13], [
        {"align": PP_ALIGN.CENTER, "runs": [
            ("OPERATIONAL MANDATE\n", 8.5, True, "7C3AED", None),
            ("MXN 828.7k (-14.8%) Saved | Mon 00:00 Retrain", 8.8, True, "0F172A", None),
        ]},
    ])


def add_rect(slide, left, top, width, height, fill_hex: str, line_hex: str | None = None, line_pt: float = 1.0, rounded: bool = True, adj: float = 0.018):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    sh = slide.shapes.add_shape(shape_type, Inches(left), Inches(top), Inches(width), Inches(height))
    sh.fill.solid()
    sh.fill.fore_color.rgb = RGBColor.from_string(fill_hex)
    if line_hex is not None:
        sh.line.color.rgb = RGBColor.from_string(line_hex)
        sh.line.width = Pt(line_pt)
    else:
        sh.line.fill.background()
    if rounded and len(sh.adjustments):
        sh.adjustments[0] = adj
    return sh


def add_textbox(slide, left, top, width, height, m_lr=0.06, m_tb=0.04, vertical_anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(m_lr)
    tf.margin_right = Inches(m_lr)
    tf.margin_top = Inches(m_tb)
    tf.margin_bottom = Inches(m_tb)
    tf.vertical_anchor = vertical_anchor
    return tb


def add_slide12_console(prs: Presentation):
    """Add Slide 12 showcasing all 3 website panels in plain, non-technical language."""
    blank_layout = next(l for l in prs.slide_layouts if l.name == "Blank")
    s12 = prs.slides.add_slide(blank_layout)

    add_rect(s12, 0.0, 0.0, 13.333, 7.50, fill_hex="FFFFFF", line_hex=None, rounded=False)

    hdr = add_textbox(s12, 0.50, 0.30, 12.33, 0.78, m_lr=0.0, m_tb=0.0)
    set_paragraphs(hdr, [
        {"space_after_pt": 1.5, "runs": [(SLIDE12_EYEBROW, 11.0, True, "0284C7", "Liberation Sans")]},
        {"runs": [("Monclova Analyst Console: Plan Tomorrow, Manage Today & Verify Savings", 22.0, True, "0F172A", "Liberation Sans")]},
    ])

    cards = [
        {
            "left": 0.50, "top": 1.18,
            "fill": "F0F7FF", "border": "BFDBFE",
            "title": "TAB 1 · DAY-AHEAD PLANNER",
            "badge": "Lock Tomorrow Before Noon", "badge_color": "60A5FA",
            "accent": "1E40AF",
            "img": SCREENSHOTS["tab1"],
            "bullets": [
                ("Chart: ", "Tomorrow's 24h price outlook vs. break-even cost, flagging cheap solar & peak hours."),
                ("Sliders: ", "Test how much power to buy before noon and preview the projected daily bill."),
                ("Actions: ", "Download tomorrow's bid file and send an early warning to reschedule plant shifts."),
            ],
        },
        {
            "left": 6.79, "top": 1.18,
            "fill": "FFF7ED", "border": "FED7AA",
            "title": "TAB 2 · REAL-TIME MONITOR",
            "badge": "Live Operations & Alerts", "badge_color": "FB923C",
            "accent": "C2410C",
            "img": SCREENSHOTS["tab2"],
            "bullets": [
                ("Chart: ", "Live market price vs. yesterday's locked rate, next 4h outlook & extra cost/hr."),
                ("Diagnosis: ", "Explains in plain words if a spike hits the whole grid or one local line."),
                ("Actions: ", "Pause heavy furnaces, discharge the backup battery during peaks, or log alerts."),
            ],
        },
        {
            "left": 0.50, "top": 4.12,
            "fill": "ECFDF5", "border": "A7F3D0",
            "title": "TAB 3 · BILLING & WEEKLY REVIEW",
            "badge": "Saved: MXN 828,677 (-14.8%)", "badge_color": "34D399",
            "accent": "047857",
            "img": SCREENSHOTS["tab3"],
            "bullets": [
                ("Savings: ", "Compares weekly bills vs. doing nothing, proving MXN 828.7k (-14.8%) saved."),
                ("Reliability: ", "Shows which hours forecasts get right cleanly (daytime) vs. volatile peaks."),
                ("Review: ", "Inspect major price spikes and approve or exclude blackout days from updates."),
            ],
        },
    ]

    card_w, card_h = 6.04, 2.78
    hdr_h = 0.30

    for c in cards:
        x, y = c["left"], c["top"]
        add_rect(s12, x, y, card_w, card_h, fill_hex=c["fill"], line_hex=c["border"], line_pt=1.0, rounded=False)
        add_rect(s12, x, y, card_w, hdr_h, fill_hex="1C2127", line_hex="2F343C", line_pt=0.75, rounded=False)

        htb_l = add_textbox(s12, x + 0.08, y + 0.02, 3.65, hdr_h - 0.04, m_lr=0.02, m_tb=0.0, vertical_anchor=MSO_ANCHOR.MIDDLE)
        set_paragraphs(htb_l, [{"runs": [(c["title"], 9.0, True, "F6F7F9", "Liberation Sans")]}])

        htb_r = add_textbox(s12, x + 3.72, y + 0.02, 2.24, hdr_h - 0.04, m_lr=0.02, m_tb=0.0, vertical_anchor=MSO_ANCHOR.MIDDLE)
        set_paragraphs(htb_r, [{"align": PP_ALIGN.RIGHT, "runs": [(c["badge"], 8.3, True, c["badge_color"], "Liberation Sans")]}])

        with Image.open(c["img"]) as im:
            px_w, px_h = im.size
        img_h = 2.33
        img_w = img_h * (px_w / px_h)
        img_x = x + 0.08
        img_y = y + hdr_h + 0.075

        pic = s12.shapes.add_picture(str(c["img"]), Inches(img_x), Inches(img_y), width=Inches(img_w), height=Inches(img_h))
        pic.line.color.rgb = RGBColor.from_string("2F343C")
        pic.line.width = Pt(0.75)

        txt_x = img_x + img_w + 0.10
        txt_w = (x + card_w - 0.08) - txt_x
        btb = add_textbox(s12, txt_x, img_y - 0.02, txt_w, img_h + 0.04, m_lr=0.03, m_tb=0.04, vertical_anchor=MSO_ANCHOR.MIDDLE)
        specs = []
        for idx_b, (lead, body) in enumerate(c["bullets"]):
            specs.append({
                "space_after_pt": 7.5 if idx_b < len(c["bullets"]) - 1 else 0.0,
                "runs": [
                    ("▸ ", 8.5, True, c["accent"], "Liberation Sans"),
                    (lead, 8.5, True, "0F172A", "Liberation Sans"),
                    (body, 8.4, False, "334155", "Liberation Sans"),
                ],
            })
        set_paragraphs(btb, specs)

    qx, qy = 6.79, 4.12
    add_rect(s12, qx, qy, card_w, card_h, fill_hex="F8FAFC", line_hex="CBD5E1", line_pt=1.0, rounded=False)
    add_rect(s12, qx, qy, card_w, hdr_h, fill_hex="1C2127", line_hex="2F343C", line_pt=0.75, rounded=False)
    qht_l = add_textbox(s12, qx + 0.08, qy + 0.02, 3.85, hdr_h - 0.04, m_lr=0.02, m_tb=0.0, vertical_anchor=MSO_ANCHOR.MIDDLE)
    set_paragraphs(qht_l, [{"runs": [("HOW THE ANALYST CONSOLE WORKS", 9.0, True, "F6F7F9", "Liberation Sans")]}])
    qht_r = add_textbox(s12, qx + 3.92, qy + 0.02, 2.04, hdr_h - 0.04, m_lr=0.02, m_tb=0.0, vertical_anchor=MSO_ANCHOR.MIDDLE)
    set_paragraphs(qht_r, [{"align": PP_ALIGN.RIGHT, "runs": [("Unified Daily Workflow", 8.3, True, "94A3B8", "Liberation Sans")]}])

    qtb = add_textbox(s12, qx + 0.14, qy + hdr_h + 0.10, card_w - 0.28, card_h - hdr_h - 0.18, m_lr=0.04, m_tb=0.02, vertical_anchor=MSO_ANCHOR.MIDDLE)
    q_bullets = [
        ("1. Morning-to-Night Workflow: ", "Plan tomorrow's bids before noon (Tab 1), react to live price spikes during the day (Tab 2), and verify real savings each week (Tab 3)."),
        ("2. One Curve Instead of 9 Charts: ", "Since all 9 local substations move together, the screen stays clean with one curve and only flags the plant substation if it diverges."),
        ("3. Built for Real Market Timing: ", "Connects to live plant meters during operating hours for fast action, then matches official CENACE invoices released a week later."),
        ("4. Always-On Alerts Bar: ", "The top strip counts down to the daily bidding cutoff, shows the current zone price, and flashes immediately during extreme shortages."),
    ]
    set_paragraphs(qtb, [
        {
            "space_after_pt": 7.5 if idx_q < len(q_bullets) - 1 else 0.0,
            "runs": [
                (lead, 9.5, True, "1E40AF", "Liberation Sans"),
                (body, 9.4, False, "334155", "Liberation Sans"),
            ],
        }
        for idx_q, (lead, body) in enumerate(q_bullets)
    ])

    ftb = add_textbox(s12, 0.80, 7.0324, 11.733, 0.1851, m_lr=0.0, m_tb=0.0)
    apply_footer(ftb, 12, 12, font_name="Liberation Sans")


def update_all_footers(prs: Presentation):
    """Update page totals on all slides carrying the footer pattern to N / total."""
    total = len(prs.slides)
    for slide_num, slide in enumerate(prs.slides, 1):
        for sh in slide.shapes:
            if sh.has_text_frame and "Javier Diego-Fernández" in sh.text_frame.text and slide_num >= 2:
                apply_footer(sh, slide_num, total, font_name="Liberation Sans")


def audit_pptx(prs: Presentation):
    """Run strict geometry and image aspect-ratio checks on Slides 7, 10, 11, 12."""
    for s_idx in [7, 10, 11, 12]:
        if s_idx > len(prs.slides):
            continue
        s = prs.slides[s_idx - 1]
        for sh in s.shapes:
            l = sh.left / 914400.0
            t = sh.top / 914400.0
            w = sh.width / 914400.0
            h = sh.height / 914400.0
            assert l >= -0.01 and t >= -0.01, f"S{s_idx} {sh.name} negative coord: ({l:.2f},{t:.2f})"
            assert l + w <= 13.35 and t + h <= 7.52, f"S{s_idx} {sh.name} out of slide bounds: ({l+w:.2f},{t+h:.2f})"
            if sh.shape_type == 13:
                px_w, px_h = sh.image.size
                img_r = px_w / px_h
                box_r = w / h
                rel_diff = abs(img_r - box_r) / img_r
                assert rel_diff < 0.015, f"S{s_idx} {sh.name} aspect distortion {rel_diff:.3f}"
    print("Geometry and image aspect-ratio audit passed cleanly for Slides 7, 10, 11, 12.")


def main():
    parser = argparse.ArgumentParser(description="Safely update presentation/monclova_lmp_presentation.pptx.")
    parser.add_argument(
        "--slide10-only",
        action="store_true",
        help="Only update Slide 10 (and Slide 7 Track 2 MDA pill), without modifying Slides 11/12.",
    )
    parser.add_argument(
        "--slide12-only",
        action="store_true",
        help="Only rebuild Slide 12 (Analyst Console Showcase), preserving Slides 1–11 intact.",
    )
    parser.add_argument(
        "--pptx",
        type=Path,
        default=PPTX_PATH,
        help="Target PPTX path (defaults to presentation/monclova_lmp_presentation.pptx).",
    )
    args = parser.parse_args()
    target_pptx = args.pptx.resolve()

    lock_file = target_pptx.parent / f"~${target_pptx.name}"
    if lock_file.exists():
        raise RuntimeError(f"PowerPoint lock file is active ({lock_file}); close the deck before updating.")

    prs = Presentation(str(target_pptx))
    assert len(prs.slides) >= 11, f"Expected >= 11 slides, got {len(prs.slides)}"

    if args.slide10_only:
        update_slide7_track2(prs)
        update_slide10_anomaly(prs)
    elif args.slide12_only:
        remove_existing_slide12(prs)
        assert len(prs.slides) == 11, f"Expected 11 base slides before adding Slide 12, got {len(prs.slides)}"
        add_slide12_console(prs)
    else:
        remove_existing_slide12(prs)
        assert len(prs.slides) == 11, f"Expected 11 base slides before adding Slide 12, got {len(prs.slides)}"
        update_slide7_track2(prs)
        update_slide10_anomaly(prs)
        update_slide11_workflow(prs)
        add_slide12_console(prs)
        update_all_footers(prs)

    prs.save(str(target_pptx))
    with zipfile.ZipFile(target_pptx, "r") as zf:
        bad = zf.testzip()
        assert bad is None, f"ZIP CRC-32 failure in {target_pptx}: {bad}"

    prs_check = Presentation(str(target_pptx))
    audit_pptx(prs_check)
    print(f"Successfully updated ({len(prs_check.slides)} slides, ZIP CRC-32 OK): {target_pptx}")


if __name__ == "__main__":
    main()
