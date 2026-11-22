#!/bin/bash
# Replay the pinned FieldLog synthetic Cancel/restart/sign-in clock control.
# Usage: bash replay.sh /path/to/mixer /path/to/local/fieldlog-checkout
set -euo pipefail
umask 077
if [[ $# != 2 ]]; then
  printf 'Usage: bash %s /path/to/mixer /path/to/local/fieldlog-checkout\n' "$0" >&2
  exit 64
fi
mixer=$(cd "$1" && pwd -P)
local_fieldlog=$(cd "$2" && pwd -P)
owned=$(mktemp -d "${TMPDIR:-/tmp}/fieldlog-clock-replay.XXXXXXXX")
cleanup() {
  local status=$?
  trap - EXIT
  local kib
  kib=$(du -sk "$owned" | cut -f 1)
  printf 'SCRATCH KiB=%s\n' "$kib"
  if (( kib > 716800 )); then status=1; fi
  rm -rf -- "$owned"
  test ! -e "$owned"
  printf 'CLEANUP absent=%s\n' "$owned"
  exit "$status"
}
trap cleanup EXIT
printf 'REPLAY mixer=cfaa84101d73f034704c18f1659177021c7d0e8e\n'
swiftc --version
python3 --version
git --version
prepare() {
export GIT_NO_LAZY_FETCH=1 GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0="url.file://$local_fieldlog.insteadOf" GIT_CONFIG_VALUE_0=https://github.com/snowdamiz/fieldlog.git
export TMPDIR="$root/tmp"
mkdir -p "$TMPDIR" "$root/pinned" "$root/work" "$root/checks" "$root/fixture"
git -C "$root/pinned" init -q
common=$(git -C "$mixer" rev-parse --path-format=absolute --git-common-dir)
printf '%s\n' "$common/objects" > "$root/pinned/.git/objects/info/alternates"
old=41d1b96fe4a0ddf67b5e7aa0ff4ea1cf473645c1
rec=660534ec0072f03469352adc13abb6f1e47c1bfa
new=cfaa84101d73f034704c18f1659177021c7d0e8e
prefix=tests/integration
git -C "$mixer" archive "$old" "$prefix/fieldlog-account-ios" "$prefix/fieldlog-account" "$prefix/fieldlog-ios-assignment/ordinary-witness" | tar -xf - -C "$root/pinned"
bash "$root/pinned/$prefix/fieldlog-account-ios/prepare.sh" "$root/work"
app="$root/work/source/fieldlog"
apply() {
  local rev=$1 path=$2 digest=$3 tree=$4
  git -C "$mixer" show "$rev:$prefix/$path.patch.b64" | base64 -D > "$root/work/control.patch"
  test "$(shasum -a 256 < "$root/work/control.patch" | cut -d ' ' -f 1)" = "$digest"
  git -C "$app" apply --index --whitespace=error-all "$root/work/control.patch"
  test "$(git -C "$app" write-tree)" = "$tree"
  du -sk "$root"
  echo "tree=$tree"
}
recovery_backend=$(git -C "$mixer" show "$old:$prefix/fieldlog-account-recovery/fieldlog-local-recovery.patch.b64" | base64 -D | shasum -a 256 | cut -d ' ' -f 1)
apply "$rec" fieldlog-account-recovery-ios/fieldlog-ios-recovery 1081df87e7362e46e39c4d74f110ae3ae32b1ea5fff197ea39c2d081d5f23a12 f478bec7d45a5960d514e5fe53960de9f25f73f5
apply "$old" fieldlog-account-recovery/fieldlog-local-recovery "$recovery_backend" a4e08d9b67d9811dfe160ac71b04b35e0730d954
apply "$rec" fieldlog-account-deletion/fieldlog-local-account-deletion 44aab1c0a6083b8495bb4e29777595570decab31760f43280ccb25466f7b6c43 0dd0b86a6105de7d7eed619f971adc3eb3e2a86e
apply "$new" fieldlog-account-deletion-ios/fieldlog-ios-local-deletion f78bc3ccc0fd3a0fa6614e26643ea7acf69f9351a0e24c5537119d029b283569 a218654455648bbddcdf829a97bb3002e8ba6b5d
apply "$new" fieldlog-account-deletion-ios/fieldlog-ios-deletion-callback-startup 2bbd21b329e0c2b973b726984e2a40038185242bb6571c72fcc462cb09ca1489 5cdfa986b54902b042f3b0bf1824f8d17f719a80
apply "$new" fieldlog-account-deletion-ios/fieldlog-apple-pending-replacement a1434ad3892bce3e8bc265201a810f190645718bcaf7ce50f6b59dd87a9c6876 1ba375bb182e83b0f25054e0178a7185ff3e84c3
owner=$(git -C "$app" hash-object Sources/FieldLogModels/FieldLogAccount.swift)
backend=$(git -C "$app" hash-object Backend/local_entry_sync.py)
test "$owner" = 377d020cb8c217d698b4de3d6cc02b2ba2da8b2e
test "$backend" = 535c33c727f8c0c630c444e180a754ec5625edea
echo "owner=$owner backend=$backend"
for file in run-host.py run-checks.sh DeletionChecks.swift; do
  git -C "$mixer" show "$new:$prefix/fieldlog-account-deletion-ios/$file" > "$root/fixture/$file"
done
}
root=$owned
prepare
python3 -B - "$root/fixture" <<'PY'
from pathlib import Path
import sys

fixture = Path(sys.argv[1])

def replace_once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new, 1)

swift_file = fixture / "DeletionChecks.swift"
swift = swift_file.read_text()
swift = replace_once(swift, "@main private struct DeletionChecks", """@MainActor private final class FixtureClock {
  static let serviceSecond: TimeInterval = 1_800_000_000
  var lag: TimeInterval = 0
  var now: Date { Date(timeIntervalSince1970: Self.serviceSecond - lag) }
}

@main private struct DeletionChecks""")
swift = replace_once(swift, "    let port = Int(CommandLine.arguments[3])!", """    let port = Int(CommandLine.arguments[3])!
    let profile = CommandLine.arguments[4]
    let clock = FixtureClock()
    if phase == "restore-cancelled" && profile != "confirm-lag" { clock.lag = 1 }""")
swift = replace_once(swift, "          let result = try await Browser.exchange(operation, port: port)", """          let result = try await Browser.exchange(operation, port: port)
          if phase == "restore-cancelled" && profile == "confirm-lag"
              && operation.method == .get && operation.path == "/v1/account/session"
              && result.status == 200 {
            await MainActor.run { clock.lag = 1 }
          }""")
swift = replace_once(swift, "deletionTarget: target, makeDeletionKey: FieldLogAccountApple.randomToken)",
                     "deletionTarget: target, makeDeletionKey: FieldLogAccountApple.randomToken, now: { clock.now })")
swift = replace_once(swift, '    case "cancel-held-exchange", "cancel-held-confirmation":\n      let url', """    case "cancel-held-exchange", "cancel-held-confirmation":
      for name in savedNames { try put(directory.appending(path: name)) }
      try put(ordinary)
      try put(peer.appending(path: "Workspace.json"))
      let url""")
swift = replace_once(swift, '      await owner.restore()\n      try require(owner.state == .welcome && owner.grant(for: scope) == nil,\n        "fresh process', """      let savedSlot = try Data(contentsOf: slot.url)
      await owner.restore()
      try require(try Data(contentsOf: slot.url) == savedSlot, "restore keeps slot bytes")
      try require(owner.state == .welcome && owner.grant(for: scope) == nil,
        "fresh process""")
start = swift.index("      try await signIn(owner, proof: replacement)\n")
end = swift.index('    case "save-unacknowledged":', start)
assert 'print("PASS \\(phase)")' in swift[start:end]
swift = swift[:start] + '''      let url = try await owner.beginSignIn()
      let ordinaryCallback = try await Browser.submit("proof=\\(replacement)", to: url, port: port)
      let accepted = await owner.acceptCallback(ordinaryCallback)
      let grant = owner.grant(for: scope) != nil
      try checkFiles()
      try require(try Data(contentsOf: ordinary) == saved, "ordinary workspace unchanged")
      try require(try Data(contentsOf: peer.appending(path: "Workspace.json")) == saved, "peer workspace unchanged")
      if profile == "short-lag" {
        guard case .admitted = owner.state, case .session = try slot.read()
        else { throw CheckFailure("short lifetimes admit and store a session") }
        try require(accepted && grant && !owner.hasReplacementSignInCode, "short sign-in admission")
        print("OWNER accepted=true state=admitted grant=true slot=session workspaceFilesPreserved=6")
      } else {
        try require(!accepted && !grant && owner.state == .unavailable, "full lifetimes fail closed")
        try require(try Data(contentsOf: slot.url) == savedSlot,
          "rejected sign-in preserves exact recovery slot")
        try require(!owner.hasReplacementSignInCode, "unavailable owner hides the code")
        let reopened = makeOwner(allowed: fixture.target)
        await reopened.restore()
        try require(reopened.state == .welcome && reopened.replacementSignInCodeForUser() == replacement,
          "fresh owner reveals the preserved replacement")
        print("OWNER accepted=false state=unavailable grant=false slot=recovery-byte-identical workspaceFilesPreserved=6")
      }
      return
''' + swift[end:]
swift_file.write_text(swift)

host_file = fixture / "run-host.py"
host = host_file.read_text()
host = replace_once(host, "from pathlib import Path", "from pathlib import Path\nfrom types import SimpleNamespace")
host = replace_once(host, "def verify(backend, binary, scratch, scenario):\n    root = scratch / scenario",
                    "def verify(backend, binary, scratch, scenario, profile):\n    root = scratch / profile")
host = replace_once(host, "    def phase(name):\n        subprocess.run([binary, root, name, str(port)], input=fixture, check=True, timeout=25)", """
    wire = []
    send_json = backend.EntrySyncHandler._send_json
    routes = (("POST", "/v1/account/recovery/exchange"), ("POST", "/v1/auth/exchange"),
              ("GET", "/v1/account/session"))
    def trace_json(handler, status, body):
        route = (handler.command, handler.path)
        if route in routes:
            same_scope = (body.get("accountID") == target[0] and body.get("scopes") == [binding(target)["scope"]])
            wire.append((*route, int(status), body.get("expiresAt", 0) - 1_800_000_000, same_scope))
        send_json(handler, status, body)

    def phase(name):
        with patch.object(backend.EntrySyncHandler, "_send_json", trace_json):
            result = subprocess.run([binary, root, name, str(port), profile], input=fixture,
                                    timeout=25, stdout=subprocess.PIPE)
        print(result.stdout.decode().strip(), flush=True)
        result.check_returncode()
""")
host = replace_once(host, "    peer_before = snapshot(peer)", """
    peer_before = snapshot(peer)
    content_tables = TABLES[-4:]
    target_data_before = snapshot(target, content_tables)
""")
start = host.index("            assert not (root / \"credentials.json\").exists()")
end = host.index('        elif scenario == "regression":', start)
host = host[:start] + '''            short = profile == "short-lag"
            provisional, confirmed = (58, 28795) if short else (60, 28800)
            expected = [
                ("POST", "/v1/account/recovery/exchange", 200, provisional, True),
                ("POST", "/v1/auth/exchange", 200, provisional, True),
            ]
            if profile != "steady-lag":
                expected.append(("GET", "/v1/account/session", 200, confirmed, True))
            assert wire == expected, wire
            for method, path, status, ttl, matches in wire:
                print(f"WIRE {method} {path} status={status} serverTTL={ttl} matchingScope={matches}")
            assert receipt_count() == 0 and observed == [] and snapshot(peer) == peer_before
            assert snapshot(target, content_tables) == target_data_before
            slot = json.loads((root / "credentials.json").read_bytes())
            assert set(slot) == ({"session"} if short else {"recovery"})
            if short:
                assert slot["session"]["_0"]["accountID"].lower() == target[0]
                assert {k: v.lower() for k, v in slot["session"]["_0"]["scope"].items()} == binding(target)["scope"]
            else:
                assert slot["recovery"]["_0"] == record
            with closing(sqlite3.connect(database)) as connection:
                rows = connection.execute(
                    "SELECT confirmed, expires_at - ? FROM local_sessions WHERE account_id = ? ORDER BY confirmed",
                    (1_800_000_000, target[0]),
                ).fetchall()
            if profile == "steady-lag":
                assert rows == [(0, 60), (0, 60)], rows
            else:
                assert rows == [(0, provisional), (1, confirmed)], rows
            print(f"SQLITE confirmedFlag/TTL={rows} targetContentPreserved=true peerPreserved=true receipts=0")
            return
''' + host[end:]
start = host.index('    scenarios = sys.argv[4:]')
end = host.index('    print("PASS owned loopback', start)
host = host[:start] + '''    assert (backend.SESSION_CONFIRMATION_TTL, backend.SESSION_TTL) == (60, 28800)
    with patch.object(backend, "time", SimpleNamespace(time=lambda: 1_800_000_000)):
        for profile in ("steady-lag", "confirm-lag", "short-lag"):
            durations = (58, 28795) if profile == "short-lag" else (60, 28800)
            print(f"CASE {profile}", flush=True)
            with (patch.object(backend, "SESSION_CONFIRMATION_TTL", durations[0]),
                  patch.object(backend, "SESSION_TTL", durations[1])):
                verify(backend, binary, scratch, "cancel-held-exchange", profile)
            print("PASS both fixture listeners closed and loopback ports rebound", flush=True)
''' + host[end:]
host_file.write_text(host)
PY
sh "$root/fixture/run-checks.sh" "$root/work/source/fieldlog" "$root/checks"
app="$root/work/source/fieldlog"
git -C "$app" diff --quiet
test "$(git -C "$app" write-tree)" = 1ba375bb182e83b0f25054e0178a7185ff3e84c3
