#!/usr/bin/env python3
"""Report translation completeness per language against the zh-cn reference set."""
import xml.etree.ElementTree as ET, glob, os, json, sys

TRANS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "translations")
REF = os.path.join(TRANS, "stacer_zh-cn.ts")

def parse(path):
    root = ET.parse(path).getroot()
    data = {}
    for ctx in root.findall("context"):
        name = ctx.findtext("name") or ""
        for m in ctx.findall("message"):
            if m.get("obsolete") == "true": continue
            src = m.findtext("source") or ""
            tr_el = m.find("translation")
            tr = tr_el.text if tr_el is not None and tr_el.text is not None else ""
            unfinished = tr_el is not None and tr_el.get("type") == "unfinished"
            data.setdefault(name, {})[src] = (tr, unfinished)
    return root.get("language"), data

_, ref = parse(REF)
ref_keys = {(c, s) for c, m in ref.items() for s in m}

out = {}
for ts in sorted(glob.glob(os.path.join(TRANS, "stacer_*.ts"))):
    lang, data = parse(ts)
    base = os.path.basename(ts)
    keys = {(c, s) for c, m in data.items() for s in m}
    missing = ref_keys - keys
    extra = keys - ref_keys
    unfinished = [(c, s) for c, m in data.items() for s, (t, u) in m.items() if u or not t]
    print(f"{base:<22} lang={lang:<7} msgs={len(keys):>4} missing={len(missing):>3} extra={len(extra):>3} unfinished={len(unfinished):>3}", file=sys.stderr)
    gaps = sorted(unfinished) + sorted(missing)
    out[base[7:-3]] = [f"{c}|{s}" for c, s in gaps]
json.dump(out, sys.stdout)
