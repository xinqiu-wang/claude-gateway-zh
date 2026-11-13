#!/usr/bin/env python3
"""Build, inject, inspect, and roll back a local Claude Desktop Chinese UI patch."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

TOOL = Path(__file__).resolve().parent
RESOURCES = Path('/usr/lib/claude-desktop/resources')
STATE = Path.home() / '.local/state/claude-gateway-zh'
FILES = ('app.asar', 'ion-dist.asar')


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, TOOL / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_state():
    file = STATE / 'active.json'
    return json.loads(file.read_text()) if file.exists() else None


def desktop_processes():
    found = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            if os.readlink(p / 'exe') == '/usr/lib/claude-desktop/claude-desktop':
                found.append(int(p.name))
        except OSError:
            pass
    return found


def close_desktop():
    for pid in desktop_processes():
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    for _ in range(200):
        if not desktop_processes():
            return
        time.sleep(0.1)
    raise RuntimeError('Claude Desktop 未退出，请正常退出后重试。不会强制终止 Cowork。')


def atomic_json(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def status():
    current = {name: digest(RESOURCES / name) for name in FILES}
    active = read_state()
    print(json.dumps({'resources': current, 'patch': active,
                      'active_matches': bool(active and all(current[n] == active['after'][n] for n in FILES))}, ensure_ascii=False, indent=2))


def build():
    if os.geteuid() == 0:
        raise RuntimeError('请以普通用户构建；仅 install/restore 使用 sudo 或 pkexec。')
    if not (TOOL / 'node_modules/@formatjs/icu-messageformat-parser').is_dir():
        raise RuntimeError('请先运行 npm ci --prefix ' + str(TOOL) + ' --ignore-scripts')
    STATE.mkdir(parents=True, mode=0o700, exist_ok=True)
    active = read_state()
    hashes = {name: digest(RESOURCES / name) for name in FILES}
    source = RESOURCES
    if active:
        matched = [hashes[n] == active['after'][n] for n in FILES]
        if any(matched) and not all(matched):
            raise RuntimeError('资源处于部分更新状态，请先恢复官方安装包再注入。')
        if all(matched):
            source = Path(active['originals'])
    asar = load_module('asar_tools')
    archives = {name: asar.Archive(source / name) for name in FILES}
    version = archives['app.asar'].json('/package.json')['version']
    out = Path(tempfile.mkdtemp(prefix=version + '-', dir=STATE))
    patches, report, exact = load_module('build_catalogs').build_catalogs(TOOL, archives, out)
    runtime_report = load_module('runtime_patch').apply(archives, patches, exact, out)
    for name, archive in archives.items():
        archive.patch(out / name, patches[name])
        print('已逐成员校验:', name, flush=True)
    manifest = {
        'version': version, 'build': str(out),
        'before': hashes,
        'originals_sha256': {name: digest(source / name) for name in FILES},
        'after': {name: digest(out / name) for name in FILES},
        'report': report, 'runtime': runtime_report,
        'members': {name: list(patches[name]) for name in FILES}}
    atomic_json(out / 'manifest.json', manifest)
    atomic_json(STATE / 'latest-build.json', {'path': str(out)})
    print('构建完成:', out, flush=True)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return out


def install(out):
    if os.geteuid() != 0:
        raise RuntimeError('安装需要 sudo 或 pkexec。')
    out = out.resolve()
    manifest = json.loads((out / 'manifest.json').read_text())
    for name in FILES:
        if digest(RESOURCES / name) != manifest['before'][name]:
            raise RuntimeError('安装期间程序已更新，请重新构建。')
        if digest(out / name) != manifest['after'][name]:
            raise RuntimeError('补丁文件校验失败。')
    close_desktop()
    state = out.parent
    active_file = state / 'active.json'
    old_active = json.loads(active_file.read_text()) if active_file.exists() else None
    originals = out / 'originals'
    originals.mkdir(mode=0o755)
    original_source = RESOURCES
    if old_active and all(manifest['before'][n] == old_active['after'][n] for n in FILES):
        original_source = Path(old_active['originals'])
    for name in FILES:
        shutil.copy2(original_source / name, originals / name)
        os.chmod(originals / name, 0o644)
        if digest(originals / name) != manifest['originals_sha256'][name]:
            raise RuntimeError('原始资源校验失败。')
        staging = RESOURCES / (name + '.gateway-zh-stage')
        with staging.open('xb') as target, (out / name).open('rb') as source:
            shutil.copyfileobj(source, target)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(staging, 0o644)
        if digest(staging) != manifest['after'][name]:
            raise RuntimeError('暂存校验失败。')
    previous = out / 'previous-installed'
    previous.mkdir(mode=0o755)
    installed = []
    try:
        for name in FILES:
            # /usr and the user's home may be on different filesystems.
            shutil.copy2(RESOURCES / name, previous / name)
            if digest(previous / name) != manifest['before'][name]:
                raise RuntimeError('当前资源的回滚副本校验失败。')
            (RESOURCES / (name + '.gateway-zh-stage')).replace(RESOURCES / name)
            installed.append(name)
    except BaseException:
        for name in installed:
            rollback = RESOURCES / (name + '.rollback-stage')
            shutil.copy2(previous / name, rollback)
            rollback.replace(RESOURCES / name)
        raise
    active = dict(manifest, originals=str(originals))
    atomic_json(active_file, active)
    # State belongs to the user even when installation used pkexec.
    owner = state.stat()
    os.chown(active_file, owner.st_uid, owner.st_gid)
    print('中文注入完成，版本:', manifest['version'])


def restore(state):
    if os.geteuid() != 0:
        raise RuntimeError('恢复需要 sudo 或 pkexec。')
    active_file = state / 'active.json'
    active = json.loads(active_file.read_text())
    if not all(digest(RESOURCES / n) == active['after'][n] for n in FILES):
        raise RuntimeError('官方资源已经变化，拒绝覆盖更新版本；可用 apt reinstall claude-desktop 恢复。')
    originals = Path(active['originals'])
    if not all(digest(originals / n) == active['originals_sha256'][n] for n in FILES):
        raise RuntimeError('原文件备份校验失败。')
    close_desktop()
    for name in FILES:
        temp = RESOURCES / (name + '.restore-stage')
        shutil.copy2(originals / name, temp)
        temp.replace(RESOURCES / name)
    active_file.rename(state / ('restored-' + str(time.time_ns()) + '.json'))
    print('已恢复注入前的官方资源。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('build')
    p = sub.add_parser('apply')
    p.add_argument('--auth', choices=('pkexec', 'sudo'), default='pkexec')
    p = sub.add_parser('install')
    p.add_argument('build', type=Path)
    sub.add_parser('status')
    p = sub.add_parser('restore')
    p.add_argument('--state', type=Path, default=STATE)
    args = parser.parse_args()
    if args.command == 'build':
        build()
    elif args.command == 'apply':
        out = build()
        subprocess.run([args.auth, sys.executable, '-I', str(TOOL / 'inject.py'), 'install', str(out)], check=True)
    elif args.command == 'install':
        install(args.build)
    elif args.command == 'restore':
        restore(args.state)
    else:
        status()


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print('未完成:', error, file=sys.stderr)
        sys.exit(1)
