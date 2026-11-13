"""Match translations by source text, preserving message IDs and ICU contracts."""
import json
import subprocess
from pathlib import Path


def build_catalogs(tool, archives, output):
    translations = json.loads((tool / 'translations.json').read_text())
    overrides = json.loads((tool / 'ui-overrides.json').read_text())
    translations.update(overrides)
    messages = {}
    sources = {}
    for name, archive in archives.items():
        roots = ['/resources/i18n/en-US.json'] if name == 'app.asar' else ['/i18n/en-US.json', '/i18n/dynamic/en-US.json']
        for path in roots:
            catalog = archive.json(path)
            sources[(name, path)] = catalog
            for key, source in catalog.items():
                if not isinstance(source, str):
                    raise ValueError('Unexpected message type')
                messages[name + ':' + path + ':' + key] = {
                    'source': source, 'target': translations.get(source, source)}
    request = output / 'validation-input.json'
    result = output / 'validation-result.json'
    request.write_text(json.dumps({'messages': messages}, ensure_ascii=False))
    subprocess.run(['node', str(tool / 'validate.mjs'), str(request), str(result)], check=True)
    validated = json.loads(result.read_text())
    patches = {name: {} for name in archives}
    counts = {}
    missing = []
    exact = {}
    for (name, path), catalog in sources.items():
        rows = {}
        for key, source in catalog.items():
            target = validated['messages'][name + ':' + path + ':' + key]['target']
            rows[key] = target
            if source != target:
                exact[source] = target
            elif any(c.isascii() and c.isalpha() for c in source):
                missing.append({'archive': name, 'catalog': path, 'key': key, 'source': source})
        counts[name + ':' + path] = {'total': len(rows), 'translated': sum(catalog[k] != v for k, v in rows.items())}
        data = json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode()
        patches[name][path] = data
        patches[name][path.replace('/en-US.json', '/zh-Hans.json')] = data
    # Retain translations for small static buttons omitted from the catalogs.
    exact.update(overrides)
    (output / 'untranslated.json').write_text(json.dumps(missing, ensure_ascii=False, indent=2))
    (output / 'rejected-translations.json').write_text(json.dumps(validated['rejected'], ensure_ascii=False, indent=2))
    return patches, {'catalogs': counts, 'icu_rejected': len(validated['rejected']), 'untranslated': len(missing)}, exact
