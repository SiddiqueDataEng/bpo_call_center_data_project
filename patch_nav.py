import pathlib
path = pathlib.Path("dashboard/app.py")
txt = path.read_text(encoding="utf-8")

# Fix garbled SQL nav entry and add missing pages
old = '''"\\U0001f5d4\\ufe0f SQL & AI Query Studio",
        "\\U0001f5c4\\ufe0f Data Mesh Health",'''

# Try direct replacement of the nav list items
import re
# Replace the nav radio list
nav_pattern = r'(page = st\.radio\("Navigation", \[)(.*?)(\], label_visibility="collapsed"\))'

def fix_nav(m):
    return m.group(1) + '''
        "\U0001f3e0 Executive Summary",
        "\U0001f4ca Operations Center",
        "\U0001f6e1\ufe0f Insurance",
        "\U0001f3e5 Healthcare",
        "\U0001f3e0 Real Estate",
        "\U0001f4b3 AR Sales",
        "\U0001f465 Agent & QA",
        "\u26a0\ufe0f Compliance & Risk",
        "\U0001f916 ML / AI Insights",
        "\U0001f50d SQL & AI Query Studio",
        "\U0001f4ac AI Data Assistant",
        "\U0001f4d6 Glossary & Definitions",
        "\U0001f5c4\ufe0f Data Mesh Health",
    ''' + m.group(3)

new_txt = re.sub(nav_pattern, fix_nav, txt, flags=re.DOTALL)
if new_txt == txt:
    print("Pattern not matched — using direct string replacement")
    # Fallback: just replace the broken emoji
    new_txt = txt.replace(
        '"\\u fffd\ufe0f SQL & AI Query Studio"',
        '"🔍 SQL & AI Query Studio"'
    ).replace(
        '"? SQL & AI Query Studio"',
        '"🔍 SQL & AI Query Studio"'
    )
    # Add missing items before Data Mesh if not present
    if '"💬 AI Data Assistant"' not in new_txt:
        new_txt = new_txt.replace(
            '"🗄️ Data Mesh Health"',
            '"🔍 SQL & AI Query Studio",\n        "💬 AI Data Assistant",\n        "📖 Glossary & Definitions",\n        "🗄️ Data Mesh Health"'
        )

path.write_text(new_txt, encoding="utf-8")
print("Nav patched.")
# Verify
content = path.read_text(encoding="utf-8")
for item in ["AI Data Assistant", "Glossary", "SQL"]:
    count = content.count(item)
    print(f"  '{item}' appears {count}x")
