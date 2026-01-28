"""Sample Wikipedia HTML fixtures for testing Timeline of Food ingestion.

This module provides realistic HTML snippets extracted from the Wikipedia
"Timeline of Food" article to test various date formats and edge cases.
"""

# Bullet point with explicit year
BULLET_EXPLICIT_YEAR = """
<ul>
<li><b>1847</b> – One of America's first candy-making machines invented in Boston by Henry Chase and Joseph A. Etter.</li>
</ul>
"""

# Bullet point with year range
BULLET_YEAR_RANGE = """
<ul>
<li><b>1500–1600</b> – New World crops like potatoes and maize arrive in Europe from the Americas.</li>
</ul>
"""

# Bullet point with decade notation
BULLET_DECADE = """
<ul>
<li><b>1990s</b> – Goldschläger, a gold-infused cinnamon schnapps, becomes popular in North America.</li>
</ul>
"""

# Bullet point with century
BULLET_CENTURY = """
<ul>
<li><b>19th century</b> – Factory-based food production increases due to industrialization.</li>
</ul>
"""

# Bullet point with century range
BULLET_CENTURY_RANGE = """
<ul>
<li><b>15th-17th centuries</b> – Global spice trade flourishes connecting Asia, Africa, and Europe.</li>
</ul>
"""

# Bullet point with BC/BCE range
BULLET_BCE_RANGE = """
<ul>
<li><b>8000–5000 BCE</b> – Agricultural revolution begins in the Fertile Crescent.</li>
</ul>
"""

# Bullet point with "years ago"
BULLET_YEARS_AGO = """
<ul>
<li><b>250,000 years ago</b> – Evidence suggests controlled use of fire for cooking.</li>
</ul>
"""

# Bullet point with approximate date (tilde)
BULLET_TILDE = """
<ul>
<li><b>~1450</b> – Gutenberg's printing press invented, enabling recipe distribution.</li>
</ul>
"""

# Bullet point with "circa"
BULLET_CIRCA = """
<ul>
<li><b>Circa 1516</b> – Corn brought from Americas to Portugal.</li>
</ul>
"""

# Bullet point with contentious date
BULLET_CONTENTIOUS = """
<ul>
<li><b>1673</b> – (Contentious evidence) Chocolate first used in chocolate cake in Europe.</li>
</ul>
"""

# Bullet point with embedded date in parentheses
BULLET_EMBEDDED_PARENTHETICAL = """
<ul>
<li>The domestication of wheat (9600 BCE) marks the beginning of agricultural society.</li>
</ul>
"""

# Bullet point with embedded date range
BULLET_EMBEDDED_RANGE = """
<ul>
<li>Archaeological evidence from between 4000 and 3000 BCE shows grain cultivation in Egypt.</li>
</ul>
"""

# Bullet point without date (fallback to section)
BULLET_NO_DATE = """
<ul>
<li>Early fermentation techniques allowed preservation of vegetables and fruits.</li>
</ul>
"""

# Table with explicit year
TABLE_EXPLICIT_YEAR = """
<table>
<tr>
<td>1847</td>
<td>First candy-making machine invented in Boston by Henry Chase and Joseph A. Etter.</td>
</tr>
</table>
"""

# Table with decade notation
TABLE_DECADE = """
<table>
<tr>
<td>1990s</td>
<td>Goldschläger cinnamon schnapps becomes popular in North America.</td>
</tr>
</table>
"""

# Table with year range
TABLE_YEAR_RANGE = """
<table>
<tr>
<td>1500–1600</td>
<td>New World crops like potatoes and maize arrive in Europe.</td>
</tr>
</table>
"""

# Table with BCE range
TABLE_BCE_RANGE = """
<table>
<tr>
<td>8000–5000 BCE</td>
<td>Agricultural revolution begins in the Fertile Crescent.</td>
</tr>
</table>
"""

# Section header with implicit date range
SECTION_WITH_IMPLICIT_RANGE = """
<h2>8000–5000 BCE</h2>
<ul>
<li>Evidence of early grain cultivation in the Fertile Crescent.</li>
<li>First domesticated crops appear in archaeological records.</li>
</ul>
"""

# Section header with century range
SECTION_WITH_CENTURY_RANGE = """
<h2>15th-17th Centuries</h2>
<ul>
<li>Global spice trade flourishes between Asia, Africa, and Europe.</li>
<li>New routes to Asia drive exploration and commerce.</li>
</ul>
"""

# Complex section with mixed content
COMPLEX_SECTION = """
<h2>19th Century</h2>
<h3>Early 1800s</h3>
<ul>
<li><b>1800s</b> – New potato varieties brought from Chile to Europe.</li>
<li><b>1847</b> – First candy-making machine invented in Boston.</li>
<li>Factory automation begins transforming food production.</li>
</ul>
<h3>Late 1800s</h3>
<table>
<tr>
<td>1880–1890</td>
<td>Refrigeration technology revolutionizes food storage and distribution.</td>
</tr>
<tr>
<td>1895</td>
<td>First electric ovens introduce new cooking methods.</td>
</tr>
</table>
"""

# Section with "years ago" context
SECTION_WITH_YEARS_AGO = """
<h2>Prehistoric Era (10,000,000 years ago - 8000 BCE)</h2>
<ul>
<li><b>250,000 years ago</b> – Evidence of controlled fire use for cooking.</li>
<li><b>100,000 years ago</b> – Cooking improves digestibility and nutrition.</li>
<li>Hunting and gathering societies develop food preparation techniques.</li>
</ul>
"""

# Edge case: Very ancient date (>10K BC)
ANCIENT_DATE = """
<ul>
<li><b>12,000 BCE</b> – Early evidence of grain collection and processing in the Near East.</li>
</ul>
"""

# Edge case: Mixed BC/AD transition
BC_TO_AD_TRANSITION = """
<h2>1 BCE – 1 AD</h2>
<ul>
<li><b>1 BCE</b> – Evidence of wine production in Mediterranean region.</li>
<li><b>1 AD</b> – Roman cookbook traditions begin to formalize.</li>
</ul>
"""
