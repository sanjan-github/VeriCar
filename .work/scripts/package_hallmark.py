from pathlib import Path
import re
import shutil
import zipfile

SRC = Path(r"C:\Users\TestUser\Documents\GitHub\VeriCar\.work\hallmark-inspect\hallmark-main\skills\hallmark")
OUT = Path(r"C:\Users\TestUser\Documents\GitHub\VeriCar\outputs\hallmark-skill")
ZIP_PATH = Path(r"C:\Users\TestUser\Documents\GitHub\VeriCar\outputs\hallmark.skill")

OUT.parent.mkdir(parents=True, exist_ok=True)
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir()
shutil.copytree(SRC, OUT, dirs_exist_ok=True)

skill_md = OUT / "SKILL.md"
text = skill_md.read_text(encoding="utf-8")
assert text.startswith("---\n"), "frontmatter missing"
assert re.search(r"^name:\s*hallmark\s*$", text, re.M), "name missing"
assert re.search(r"^description:", text, re.M), "description missing"
assert len(text.splitlines()) < 5000, "unexpectedly large SKILL.md"

missing = []
for ref in re.findall(r"\]\((references/[^)]+)\)", text):
    if not (OUT / ref).exists():
        missing.append(ref)
assert not missing, f"missing references: {missing}"

files = [p for p in OUT.rglob("*") if p.is_file()]
assert all(p.name not in {"README.md", "CHANGELOG.md"} for p in files), "auxiliary docs included"

ZIP_PATH.unlink(missing_ok=True)
with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, Path("hallmark") / path.relative_to(OUT))

print(f"VALID frontmatter; files={len(files)}; bytes={sum(p.stat().st_size for p in files)}")
print(f"PACKAGE={ZIP_PATH}")
print("TRIGGERS=default design/build; hallmark audit; hallmark redesign; hallmark study")
