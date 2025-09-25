import subprocess
import json
import re
from pathlib import Path

def compile_patterns(patterns):
    compiled = []
    for pattern in patterns:
        if isinstance(pattern, tuple):
            compiled.append(re.compile(pattern[0], pattern[1]))
        else:
            compiled.append(re.compile(pattern, re.IGNORECASE))
    return compiled

JP_PATTERNS = compile_patterns([
    r"\bJP\b",
    r"(?<![a-z])JP(?![a-z])",
    r"J\.P\.",
    r"Jap\.",
    r"Japan",
    r"Japanese",
    r"assetstoragejp",
    r"FGORegion\.JP",
    r"Region\.JP",
    r"BetterFGO JP",
    r"Fate/Grand Order JP",
    r"日服",
    r"JPArtChecksums",
    r"JPInstaller",
    r"JPArtName",
])

NA_PATTERNS = compile_patterns([
    r"\bNA\b",
    r"(?<![a-z])NA(?![a-z])",
    r"N\.A\.",
    r"North America",
    r"assetstoragena",
    r"FGORegion\.NA",
    r"Region\.NA",
    r"BetterFGO NA",
    r"Fate/Grand Order NA",
    r"com\.aniplex\.fategrandorder\.en",
    r"美服",
    r"NAArtChecksums",
    r"NAInstaller",
    r"NAArtName",
])

root = Path('.')
ls = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=True)
files = sorted(filter(None, ls.stdout.splitlines()))

records = []

for rel_path in files:
    path = root / rel_path
    entry = {
        'path': rel_path,
        'classification': None,
        'evidence': [],
    }
    notes = None
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding='utf-8-sig')
        except Exception:
            entry['classification'] = 'unknown'
            notes = 'Binary or non-text file'
            entry['notes'] = notes
            records.append(entry)
            continue
    except Exception:
        entry['classification'] = 'unknown'
        notes = 'Unreadable file'
        entry['notes'] = notes
        records.append(entry)
        continue

    line_hits = {}
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        matched_jp = any(pattern.search(line) for pattern in JP_PATTERNS)
        matched_na = any(pattern.search(line) for pattern in NA_PATTERNS)
        if matched_jp or matched_na:
            hit = line_hits.setdefault(line_no, {'line': line_no, 'text': stripped, 'regions': set()})
            if matched_jp:
                hit['regions'].add('JP')
            if matched_na:
                hit['regions'].add('NA')

    has_jp = any('JP' in hit['regions'] for hit in line_hits.values())
    has_na = any('NA' in hit['regions'] for hit in line_hits.values())

    if has_jp and has_na:
        entry['classification'] = 'shared'
    elif has_jp:
        entry['classification'] = 'jp-only'
    elif has_na:
        entry['classification'] = 'na-only'
    else:
        entry['classification'] = 'unknown'
        notes = 'No region-specific keywords detected'

    if notes:
        entry['notes'] = notes

    if line_hits:
        ordered_hits = []
        for line_no in sorted(line_hits):
            hit = line_hits[line_no]
            ordered_hits.append({
                'line': hit['line'],
                'text': hit['text'],
                'regions': sorted(hit['regions']),
            })
        entry['evidence'] = ordered_hits

    records.append(entry)

output_json = {
    'generated_by': 'scripts_generate_classification.py',
    'classifications': records,
}

output_path = root / 'Codex' / 'classification.json'
output_path.write_text(json.dumps(output_json, indent=2, ensure_ascii=False), encoding='utf-8')

lines = ["# File Region Classification", ""]
lines.append("| File | Classification | Evidence | Notes |")
lines.append("| --- | --- | --- | --- |")
for entry in records:
    evidence_lines = []
    for ev in entry.get('evidence', []):
        regions = ','.join(ev['regions']) if ev['regions'] else ''
        prefix = f"[{regions}] " if regions else ''
        evidence_lines.append(f"L{ev['line']}: {prefix}{ev['text']}")
    evidence_str = "<br>".join(evidence_lines) if evidence_lines else ""
    notes_str = entry.get('notes', '') or ''
    lines.append(f"| `{entry['path']}` | {entry['classification']} | {evidence_str} | {notes_str} |")

md_path = root / 'Codex' / 'classification.md'
md_path.write_text("\n".join(lines) + "\n", encoding='utf-8')
