"""Inject at the final Intl provider, after bootstrap and experiment overrides."""
import json
import re
import subprocess


def apply(archives, patches, exact, output):
    archive = archives['ion-dist.asar']
    candidates = []
    # Match a structural call, not a fixed build-dependent asset filename.
    pattern = re.compile(r'return ([A-Za-z_$][\w$]*)\(([A-Za-z_$][\w$]*),\{locale:([A-Za-z_$][\w$]*),defaultLocale:([A-Za-z_$][\w$]*),messages:([A-Za-z_$][\w$]*),onError:([A-Za-z_$][\w$]*),fallbackOnEmptyString:!1,textComponent:')
    for path in archive.entries:
        if not path.endswith('.js') or not path.startswith('/assets/'):
            continue
        text = archive.read(path).decode('utf-8')
        if 'fallbackOnEmptyString:!1,textComponent:' not in text:
            continue
        for match in pattern.finditer(text):
            candidates.append((path, text, match))
    if len(candidates) != 1:
        raise RuntimeError('最终 Intl provider 入口无法唯一识别；拒绝修改此版本：' + str(len(candidates)))
    path, text, match = candidates[0]
    from pathlib import Path
    tool = Path(__file__).resolve().parent
    catalog = json.loads(patches['ion-dist.asar']['/i18n/en-US.json'])
    original = archive.json('/i18n/en-US.json')
    translated = {key: value for key, value in catalog.items() if value != original[key]}
    dynamic_original = archive.json('/i18n/dynamic/en-US.json')
    dynamic_zh = json.loads(patches['ion-dist.asar']['/i18n/dynamic/en-US.json'])
    dynamic_count = 0
    field_pattern = re.compile(r'(?:"([^"\\]*(?:\\.[^"\\]*)*)"|([A-Za-z_$][\w$]*)):[\w$]+\([^,]+,\{defaultMessage:("(?:[^"\\]|\\.)*"),id:("(?:[^"\\]|\\.)*")\}\)')
    for dynamic_path in archive.entries:
        if not dynamic_path.startswith('/assets/') or not dynamic_path.endswith('.js'):
            continue
        candidate = archive.read(dynamic_path).decode('utf-8')
        start = candidate.find('var Gv={')
        end = candidate.find('};function Kv(', start)
        if start < 0 or end < 0:
            continue
        for item in field_pattern.finditer(candidate[start:end]):
            prop = json.loads('"' + item.group(1) + '"') if item.group(1) is not None else item.group(2)
            key = json.loads(item.group(4))
            if key in dynamic_zh and dynamic_zh[key] != dynamic_original[key]:
                translated['dynamic:' + prop] = dynamic_zh[key]
                dynamic_count += 1
    if dynamic_count == 0:
        raise RuntimeError('动态消息映射无法识别，拒绝生成不完整的运行时补丁。')
    overlay = (tool / 'overlay.js').read_text().replace('__CATALOG__', json.dumps(translated, ensure_ascii=False, separators=(',', ':')))
    replacement = match.group().replace('messages:' + match.group(5) + ',', 'messages:__claudeGatewayZhOverlay(' + match.group(5) + '),', 1)
    patched = overlay + '\n/*END_LOCAL_OVERLAY*/\n' + text[:match.start()] + replacement + text[match.end():]
    script = output / 'provider-patched.mjs'
    script.write_text(patched)
    subprocess.run(['node', '--input-type=module', '-e',
                    'import {parse} from "' + (tool / 'node_modules/acorn/dist/acorn.mjs').as_uri() + '";import fs from "node:fs";parse(fs.readFileSync(process.argv[1],"utf8"),{ecmaVersion:"latest",sourceType:"module"});console.log("Provider JavaScript syntax verified");', str(script)], check=True)
    english_file = output / 'provider-english.json'
    english_file.write_text(json.dumps(original, ensure_ascii=False))
    subprocess.run(['node', str(tool / 'test-provider.mjs'), str(script), str(english_file)], check=True)
    patches['ion-dist.asar'][path] = patched.encode()
    return {'provider': path, 'translated_ids': len(translated), 'locale': 'original', 'strategy': 'final Intl message proxy overlay'}
