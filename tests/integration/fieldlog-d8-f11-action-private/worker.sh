#!/bin/bash
set -euo pipefail
recipe="$(cd "$(dirname "$0")" && pwd -P)"
stage=$1
fieldlog=$2
work=$3
vertical=$4
pin=b9d227c81c1c87b51d40fa55718ffbb18734c258
printf '%s\n' stage-pins > "$work/phase"
test "$(git -C "$stage" rev-parse "$pin^{tree}")" = d7993f666e14ca80a9ea3d14c171d6edd6e51d74
mkdir "$work"/{f04,f11}
git -C "$stage" show "$pin:tests/integration/fieldlog-d8-f04-signed/task-retry-replay.patch" > "$work/f04/task-retry-replay.patch"
git -C "$stage" show "$pin:tests/integration/fieldlog-d8-f11-signed/fixtures.py" > "$work/f11/fixtures.py"
python3 -B "$recipe/compose.py" worker "$vertical" "$recipe" "$work" > "$work/worker.sh"
exec /bin/bash "$work/worker.sh" "$stage" "$fieldlog" "$work/f04" "$work/f11" "$work"
