"""Patch app.py to add AI Chat and Glossary pages."""
import pathlib, re

path = pathlib.Path("dashboard/app.py")
txt = path.read_text(encoding="utf-8")

# 1. Add new nav items
old_nav = '"🔍 SQL & AI Query Studio",'
new_nav = '"🔍 SQL & AI Query Studio",\n        "💬 AI Data Assistant",\n        "📖 Glossary & Definitions",'
txt = txt.replace(old_nav, new_nav, 1)

# 2. Add SQL page routing before Data Mesh section if not already present
if "AI Data Assistant" not in txt or "render_ai_chat_page" not in txt:
    old_section = '# PAGE: Data Mesh Health'
    new_section = '''# PAGE: AI Data Assistant
# ─────────────────────────────────────────────────────────────────────────────
elif "AI Data Assistant" in page:
    render_ai_chat_page()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Glossary & Definitions
# ─────────────────────────────────────────────────────────────────────────────
elif "Glossary" in page:
    render_glossary_page()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Data Mesh Health'''
    txt = txt.replace(old_section, new_section, 1)

path.write_text(txt, encoding="utf-8")
print("app.py patched.")
