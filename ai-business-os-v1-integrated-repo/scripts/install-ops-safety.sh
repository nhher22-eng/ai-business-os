#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
sudo install -m 0755 "$ROOT/scripts/aios-doctor" /usr/local/bin/aios-doctor
sudo install -m 0755 "$ROOT/scripts/aios-preflight" /usr/local/bin/aios-preflight
printf '설치 완료: aios-doctor, aios-preflight\n'
printf '지금 실행: aios-doctor\n'
