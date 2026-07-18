from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def insert_after(text: str, anchor: str, addition: str) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Could not find integration anchor: {anchor}")
    return text.replace(anchor, anchor + addition, 1)


app = ROOT / "app.py"
text = app.read_text(encoding="utf-8")
text = insert_after(text, "from ui.market_scan import render_market_scan\n", "from ui.paper_trading import render_paper_trading\n")
if '"Paper Trading": render_paper_trading,' not in text:
    route_anchor = '        "Market Scan": render_market_scan,\n'
    text = text.replace(route_anchor, route_anchor + '        "Paper Trading": render_paper_trading,\n', 1)
app.write_text(text, encoding="utf-8")

components = ROOT / "ui" / "components.py"
text = components.read_text(encoding="utf-8")
if '"Paper Trading"' not in text:
    for anchor in ['"Market Scan",', '"Alerts",']:
        if anchor in text:
            text = text.replace(anchor, anchor + ' "Paper Trading",', 1)
            break
    else:
        raise RuntimeError("Could not add Paper Trading to navigation.")
components.write_text(text, encoding="utf-8")

version = ROOT / "version.py"
if version.exists():
    vtext = version.read_text(encoding="utf-8")
    lines = []
    replaced = False
    for line in vtext.splitlines():
        if line.startswith("APP_VERSION"):
            lines.append('APP_VERSION = "6.0.0-sprint4-part1"')
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.append('APP_VERSION = "6.0.0-sprint4-part1"')
    version.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("Sprint 4 Part 1 integration complete.")
