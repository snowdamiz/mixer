#!/bin/bash
set -euo pipefail

mixer=$(git -C "$1" rev-parse --show-toplevel)
run=$(cd "$2" && pwd -P)
public=d203a1c27027e2ae10bc46deb911cc94b8c28cbb
recipe_revision=050afa201ffbfa0d2c87ba84f9321ea2158d2bf8
recipe=tests/integration/fieldlog-pair25-android/rust-runtime-notices
owner=tests/integration/fieldlog-ios-assignment/current-owner
mkdir "$run/recipe"
export GIT_TERMINAL_PROMPT=0

from_git() {
  git -C "$mixer" show "$1" > "$2"
  local digest
  digest=$(shasum -a 256 < "$2")
  [[ ${digest%% *} == "$3" ]] || { echo "Input digest mismatch: $1" >&2; exit 65; }
}

from_git "$recipe_revision:$recipe/prepare-successor.py" "$run/recipe/prepare-successor.py" 99a8b563f84f345a0d2d6c63b5f11ad6d98434df2b517de34199845a2bf8580f
from_git "$recipe_revision:$recipe/fieldlog-packaging.patch" "$run/recipe/fieldlog-packaging.patch" 998fe05c85e2e5d4870c234816b8a18e19c39513fc5cbebbae768ac1acbc87fa
from_git "$recipe_revision:$recipe/fieldlog-l07-notices.patch" "$run/recipe/fieldlog-l07-notices.patch" f70c721ea18541b2bbe8100d327ccca534058b1f4b36dcfcdde42786347d3931

python3 -B "$run/recipe/prepare-successor.py" --mixer "$mixer" "$run/source"
app="$run/source/fieldlog"
sdk="$run/source/mixer"
require_tree() {
  local tree
  tree=$(git -C "$app" write-tree)
  [[ $tree == "$1" ]] || { echo "Expected FieldLog tree $1, got $tree" >&2; exit 65; }
  echo "FieldLog tree $tree"
}
require_tree 34810962320bdfb7877b8bbdd065495e9ec1e2bb
git -C "$app" apply --index --reverse "$run/recipe/fieldlog-l07-notices.patch"
require_tree 7b2b98f098559f57ce39e213321478058c289c5a
from_git "$public:verification/receipts/fieldlog-ios-settings-bounded-7b2b98f0.patch" "$run/settings.patch" 2639352790e03eadd4fc0ae1cb81fe2fbdcfd4d1c7f7d3f872dc405869fa7418
git -C "$app" apply --index --unidiff-zero --whitespace=error "$run/settings.patch"
require_tree f2865989693af3eb4a1891a492054baa36ac1e2f
from_git "$public:verification/receipts/fieldlog-ios-task-conflict-injected-f2865989.patch" "$run/task.patch" f5c09970636d4b4aa650aa7ee709d923f68281f7a09a41d17af05cb2772f7b34
git -C "$app" apply --index --unidiff-zero --whitespace=error "$run/task.patch"
require_tree 41eaf5b4e5ff22ed990e27166e4a860063b4ac26
for patch in fieldlog-ios-assignment-41eaf5b4 fieldlog-ios-assignment-review-fixes; do
  git -C "$mixer" show "$public:$owner/$patch.patch.b64" | base64 -D > "$run/$patch.patch"
done
assignment=$(shasum -a 256 < "$run/fieldlog-ios-assignment-41eaf5b4.patch")
recovery=$(shasum -a 256 < "$run/fieldlog-ios-assignment-review-fixes.patch")
[[ ${assignment%% *} == 80b2a0edfca615d07fbfdb0077719e9bce4efa381a99ed580458cc08ab373eaa ]]
[[ ${recovery%% *} == b80b10699aebeed52b239de41521db7e8ad1dc0654e336992337f80c8cdbe342 ]]
git -C "$app" apply --index --whitespace=error "$run/fieldlog-ios-assignment-41eaf5b4.patch"
require_tree 8c2cc120237e3dff26e959674cdd455a1499a202
git -C "$app" apply --index --whitespace=error "$run/fieldlog-ios-assignment-review-fixes.patch"
require_tree 73e9f093470ef9173a8e6a21da56f8537622212f
git -C "$app" diff --quiet
test "$(git -C "$sdk" rev-parse HEAD HEAD^{tree})" == $'857e4b4aa7a32cda368257b2be1a63e77106bed8\nfaf0902a82ffc7acb2ddde9c6dca24002f959c3d'
