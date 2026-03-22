content = open("app.py", encoding="utf-8").read()
content = content.replace(
    "if is_admin() and len(tabs) > 7:",
    "if is_admin() and len(tabs) >= 8:"
)
open("app.py", "w", encoding="utf-8").write(content)
print("OK")
