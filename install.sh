#!/usr/bin/env bash
# Install dependencies and a PATH entry; does not patch Claude until claude-zh runs.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mode=user
case "${1:-}" in
  --system) mode=system ;;
  --help|-h) printf '%s\n' 'bash install.sh [--system]' '默认安装到 ~/.local/bin；--system 安装到 /usr/local/bin。请以普通用户运行。'; exit 0 ;;
  '') ;;
  *) printf '%s\n' '未知参数，请执行 bash install.sh --help' >&2; exit 1 ;;
esac
if [[ $(id -u) -eq 0 ]]; then printf '%s\n' '请以普通用户运行本脚本；需要时会调用 sudo。' >&2; exit 1; fi
command -v python3 >/dev/null || { printf '%s\n' '请先安装 Python 3.11 或更高版本。' >&2; exit 1; }
python3 -I -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else "需要 Python 3.11 或更高版本")'
command -v node >/dev/null && command -v npm >/dev/null || { printf '%s\n' '请先安装 Node.js 20.19+ 和 npm（推荐 Node.js 22/24 LTS）。' >&2; exit 1; }
node -e 'const [major,minor]=process.versions.node.split(".").map(Number);if(major<20 || major===20 && minor<19){console.error("需要 Node.js 20.19+，推荐22/24 LTS");process.exit(1)}'
test -f /usr/lib/claude-desktop/resources/app.asar || { printf '%s\n' '未找到官方 Linux deb 版 Claude Desktop，请先安装。' >&2; exit 1; }
npm ci --prefix "$HERE" --ignore-scripts --no-audit --no-fund
chmod 755 "$HERE/claude-zh"
if [[ "$mode" == system ]]; then
  target=/usr/local/bin/claude-zh
else
  target="$HOME/.local/bin/claude-zh"
  mkdir -p -- "$HOME/.local/bin"
fi
# Inspect an existing entry and keep it if it is not already ours.
if [[ -e "$target" || -L "$target" ]]; then
  if [[ "$(readlink -f -- "$target")" != "$HERE/claude-zh" ]]; then
    saved="$target.before-$(date +%Y%m%d-%H%M%S)-$$"
    if [[ "$mode" == system ]]; then sudo mv -- "$target" "$saved"; else mv -- "$target" "$saved"; fi
    printf '原命令保留在：%s\n' "$saved"
  fi
fi
if [[ "$mode" == system ]]; then
  sudo ln -sfn -- "$HERE/claude-zh" "$target"
else
  ln -sfn -- "$HERE/claude-zh" "$target"
fi
printf '命令安装完成：%s\n' "$target"
case ":$PATH:" in
  *":$(dirname -- "$target"):"*) printf '%s\n' '执行 claude-zh 即可汉化。' ;;
  *) printf '当前 PATH 未包含该目录。请重新登录，或执行：\n  %q\n' "$target" ;;
esac
printf '%s\n' '请保留此仓库目录，快捷命令通过符号链接使用其中的程序。'
