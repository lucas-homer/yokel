#!/bin/bash
# usage: fetch.sh <id> ; run from sources-r2/
id=$1; d=$id; mkdir -p $d
url=https://lawfilesext.leg.wa.gov/law/wsr/2026/19/$id.htm
cp ../../round14-semantic-contract/source/extract_source.py $d/extract_source.py
for n in 1 2; do
  s=$(date -u +%Y-%m-%dT%H:%M:%S+00:00)
  out=$(curl -q -L --fail --max-time 30 --silent --show-error --netrc-file /dev/null --dump-header $d/headers-$n.txt --output $d/attempt-$n.body --write-out '%{http_code}|%{url_effective}|%{content_type}|%{size_download}' $url 2>$d/stderr-$n.txt); rc=$?
  echo "$n|$s|$rc|$out" >> $d/attempts.log
  [ $rc -eq 0 ] && break
done
