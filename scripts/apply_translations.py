#!/usr/bin/env python3
"""Regenerate stacer_*.ts against the zh-cn reference set.

- keeps finished translations already in the file
- fills unfinished/missing/empty entries from scripts/translations/<lang>.json
  (keyed "context|source" -> translated text)
- drops messages not in the reference set (stale strings)
- fixes the <TS language="..."> attribute, keeps sourcelanguage="en"
Usage: python3 apply_translations.py [lang1 lang2 ...]   (default: all but en)
"""
import json, os, sys, glob
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANS = os.path.join(ROOT, "translations")
DICT_DIR = os.path.join(ROOT, "scripts", "translations")

LANG_ATTR = {
    "ar": "ar_SA", "ca": "ca_ES", "cs": "cs_CZ", "de": "de_DE",
    "en": "en_US", "es": "es_ES", "eu": "eu_ES", "fr": "fr_FR",
    "gl": "gl_ES", "hi": "hi_IN", "hu": "hu_HU", "it": "it_IT",
    "kn": "kn_IN", "ko": "ko_KR", "ml": "ml_IN", "nl": "nl_NL",
    "oc": "oc_FR", "pl": "pl_PL", "pt": "pt_PT", "ro": "ro_RO",
    "ru": "ru_RU", "sv": "sv_SE", "tr": "tr_TR", "uk": "uk_UA",
    "vi": "vi_VN", "zh-cn": "zh_CN", "zh-tw": "zh_TW",
}

def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def read_ts(path):
    tree = ET.parse(path)
    root = tree.getroot()
    data, locs = {}, {}
    for ctx in root.findall("context"):
        name = ctx.findtext("name") or ""
        for m in ctx.findall("message"):
            src = m.findtext("source") or ""
            tr_el = m.find("translation")
            tr = tr_el.text if tr_el is not None and tr_el.text is not None else ""
            unfinished = tr_el is not None and tr_el.get("type") == "unfinished"
            data[(name, src)] = (tr, unfinished)
            loc = m.find("location")
            if loc is not None:
                locs[(name, src)] = (loc.get("filename", ""), loc.get("line", ""))
    return data, locs

def write_ts(path, lang_code, contexts):
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<!DOCTYPE TS>",
             f'<TS version="2.1" language="{LANG_ATTR[lang_code]}" sourcelanguage="en">']
    for ctx in sorted(contexts):
        lines.append("<context>")
        lines.append(f"    <name>{esc(ctx)}</name>")
        for src in sorted(contexts[ctx]):
            tr, loc = contexts[ctx][src]
            lines.append("    <message>")
            if loc[0]:
                lines.append(f'        <location filename="{loc[0]}"' + (f' line="{loc[1]}"/>' if loc[1] else "/>"))
            lines.append(f"        <source>{esc(src)}</source>")
            if tr:
                lines.append(f"        <translation>{esc(tr)}</translation>")
            else:
                lines.append('        <translation type="unfinished"></translation>')
            lines.append("    </message>")
        lines.append("</context>")
    lines.append("</TS>")
    lines.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))

def main():
    ref = {}
    root = ET.parse(os.path.join(TRANS, "stacer_zh-cn.ts")).getroot()
    for ctx in root.findall("context"):
        name = ctx.findtext("name") or ""
        for m in ctx.findall("message"):
            if m.get("obsolete") == "true": continue
            ref.setdefault(name, {})[m.findtext("source") or ""] = None

    # Strings introduced by the restart notice in settings_page.cpp
    ref.setdefault("SettingsPage", {})["Language Changed"] = None
    ref.setdefault("SettingsPage", {})["The language change will take effect after restarting Stacer."] = None

    targets = sys.argv[1:] or sorted(LANG_ATTR.keys())
    for lang in targets:
        if lang == "en":
            print("en skipped (source language)"); continue
        ts_path = os.path.join(TRANS, f"stacer_{lang}.ts")
        existing, locs = read_ts(ts_path)
        dict_path = os.path.join(DICT_DIR, f"{lang}.json")
        add = json.load(open(dict_path, encoding="utf-8")) if os.path.exists(dict_path) else {}

        contexts = {}
        gaps = []
        for ctx, msgs in ref.items():
            for src in msgs:
                key = f"{ctx}|{src}"
                cur = existing.get((ctx, src))
                if cur and not cur[1] and cur[0]:
                    tr = cur[0]
                elif key in add and add[key]:
                    tr = add[key]
                else:
                    tr = ""
                    gaps.append(key)
                loc = locs.get((ctx, src), ("", ""))
                contexts.setdefault(ctx, {})[src] = (tr, loc)

        write_ts(ts_path, lang, contexts)
        n = sum(len(m) for m in contexts.values())
        print(f"{lang:<6} messages={n:<4} gaps={len(gaps)}")
        for g in gaps[:8]:
            print(f"       missing: {g}")

if __name__ == "__main__":
    main()
