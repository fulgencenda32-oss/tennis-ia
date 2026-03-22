content = open("modules/prediction.py", encoding="utf-8").read()
content = content.replace(
    "f\"🎾 **Match trouvé aujourd'hui :**\n\n\"",
    "\"🎾 Match trouve aujourd\'hui :\""
)
# Correction plus large
import re
content = re.sub(
    r'f"🎾 \*\*Match trouvé aujourd\'hui :\*\*\\n\\n"\s*\n\s*f"\*\*\{match\[\'joueur_a\'\]\}\*\* vs \*\*\{match\[\'joueur_b\'\]\}\*\*\\n\\n"\s*\n\s*f"🏆 \{match\[\'tournoi\'\]\} \{\'• \' \+ match\[\'heure\'\] if match\[\'heure\'\] else \'\'\}"',
    'f"🎾 Match trouve aujourd\'hui : {match[\'joueur_a\']} vs {match[\'joueur_b\']} | {match[\'tournoi\']}"',
    content
)
open("modules/prediction.py", "w", encoding="utf-8").write(content)
