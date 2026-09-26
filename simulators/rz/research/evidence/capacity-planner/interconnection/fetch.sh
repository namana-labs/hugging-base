#!/bin/zsh
# usage: fetch.sh URL OUTFILE   (no auth, no cookies beyond the session)
cd /Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/interconnection
url="$1"; out="$2"
r=$(curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36" -o "$out" -w "%{http_code} %{size_download} %{url_effective}" --max-time 120 "$url")
echo "$(date -u +%Y-%m-%dT%H:%MZ) | $r | $url" | tee -a fetch-log.txt
case "$out" in *.pdf|*.PDF) pdftotext -layout "$out" "${out%.*}.txt" 2>/dev/null && echo "txt lines: $(wc -l < ${out%.*}.txt)";; esac
