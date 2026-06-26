#!/usr/bin/env bash
# Usage:
#   ./scripts/dump.sh path1 path2 ...
#   DUMP_CLIPBOARD=1 ./scripts/dump.sh ...   # ещё и в буфер обмена

set -euo pipefail

OUT="${DUMP_OUT:-dump.md}"
OUT="${OUT//\\//}" # Нормализация слэшей в пути вывода (замена '\' на '/')
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

collect_files() {
    find "$1" -type f \
        \( -name "*.py" -o -name "*.toml" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.cfg" -o -name "*.ini" \) \
        -not -path "*/__pycache__/*" \
        -not -path "*/.venv/*" \
        -not -path "*/.git/*" \
        -not -path "*/node_modules/*" \
        | sort
}

# --- собираем тело
for target in "$@"; do
    target="${target//\\//}" # Нормализация слэшей во входных путях
    if [ -f "$target" ]; then
        files=("$target")
    elif [ -d "$target" ]; then
        mapfile -t files < <(collect_files "$target")
    else
        echo "skip: $target (not found)" >&2
        continue
    fi

    for f in "${files[@]}"; do
        ext="${f##*.}"
        case "$ext" in
            py)             lang="python" ;;
            toml)           lang="toml" ;;
            md)             lang="markdown" ;;
            yml|yaml)       lang="yaml" ;;
            cfg|ini)        lang="ini" ;;
            *)              lang="" ;;
        esac

        {
            printf '\n### `%s`\n\n' "$f"
            printf '```%s\n' "$lang"
            cat "$f"
            printf '\n```\n'
        } >> "$TMP"
    done
done

# --- финальный файл: tree + тело
{
    printf '# Dump\n\n## Tree\n\n```\n'
    for target in "$@"; do
        target="${target//\\//}" # Нормализация слэшей (на случай, если в $@ остались оригинальные значения)
        if [ -d "$target" ]; then
            collect_files "$target"
        else
            echo "$target"
        fi
    done
    printf '```\n'
    cat "$TMP"
} > "$OUT"

lines=$(wc -l < "$OUT" | tr -d ' ')
bytes=$(wc -c < "$OUT" | tr -d ' ')
echo "Wrote $OUT ($lines lines, $bytes bytes)" >&2

if [ "${DUMP_CLIPBOARD:-0}" = "1" ]; then
    if command -v powershell.exe >/dev/null 2>&1; then
        powershell.exe -NoProfile -Command "Get-Content -Path '$OUT' -Encoding UTF8 -Raw | Set-Clipboard"
        echo "Also copied to clipboard via PowerShell" >&2
    elif command -v pbcopy >/dev/null 2>&1; then
        pbcopy < "$OUT"
        echo "Also copied to clipboard via pbcopy" >&2
    elif command -v xclip >/dev/null 2>&1; then
        xclip -selection clipboard -in < "$OUT"
        echo "Also copied to clipboard via xclip" >&2
    else
        echo "Warning: no clipboard tool found, skip" >&2
    fi
fi