"""Freeze installed official API sources and versioned primary documentation."""
import hashlib, json, shutil, urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    target = HERE / 'api-source'
    target.mkdir(exist_ok=True)
    otp_root = Path('/opt/homebrew/Cellar/erlang/29.1.1_2/lib/erlang/lib')
    installed = {
        'otp-29.1.1-kernel-logger.erl': otp_root / 'kernel-11.0.4/src/logger.erl',
        'otp-29.1.1-erts-erlang.erl': otp_root / 'erts-17.1/src/erlang.erl',
        'otp-29.1.1-stdlib-gen.erl': otp_root / 'stdlib-8.0.2/src/gen.erl',
    }
    # Discover the installed stdlib directory if its app patch suffix differs.
    installed['otp-29.1.1-stdlib-gen.erl'] = next(otp_root.glob('stdlib-*/src/gen.erl'))
    sources = []
    for name, source in installed.items():
        dest = target / name
        if dest.exists():
            assert sha(dest) == sha(source), name
        else:
            shutil.copyfile(source, dest)
        sources.append({'source': str(source), 'retained': str(dest.relative_to(HERE)), 'sha256': sha(dest), 'bytes': dest.stat().st_size, 'authority': 'installed official OTP platform source; exact toolchain separately pinned'})
    urls = {
        'bandit-1.13.1.html': 'https://hexdocs.pm/bandit/1.13.1/Bandit.html',
        'thousand-island-1.6.0.html': 'https://hexdocs.pm/thousand_island/1.6.0/ThousandIsland.html',
        'thousand-island-telemetry-1.6.0.html': 'https://hexdocs.pm/thousand_island/1.6.0/ThousandIsland.Telemetry.html',
        'plug-1.20.3.html': 'https://hexdocs.pm/plug/1.20.3/Plug.Conn.html',
        'telemetry-1.4.2.html': 'https://telemetry.hexdocs.pm/1.4.2/telemetry.html',
        'process-1.20.4.html': 'https://elixir.hexdocs.pm/1.20.4/Process.html',
        'logger-otp-29.1.1.html': 'https://www.erlang.org/docs/29/apps/kernel/logger.html',
        'erlang-otp-29.1.1.html': 'https://www.erlang.org/docs/29/apps/erts/erlang.html',
    }
    docs = HERE / 'official-sources'
    docs.mkdir(exist_ok=True)
    for name, url in urls.items():
        dest = docs / name
        record = {'url': url, 'observedUTC': datetime.now(timezone.utc).isoformat()}
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = response.read()
                record.update(status=response.status, finalURL=response.url)
            dest.write_bytes(data)
            record.update(retained=str(dest.relative_to(HERE)), sha256=sha(dest), bytes=len(data))
        except Exception as exc:
            record['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
        sources.append(record)
    (HERE / 'sources.json').write_text(json.dumps({'schema': 1, 'command': ['python3', '-B', 'verification/stripe-webhook-transport-contract/collect_sources.py'], 'sources': sources}, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'installedSources': len(installed), 'documentationSources': len(urls), 'documentationFailures': sum('failure' in value for value in sources)}, sort_keys=True))

if __name__ == '__main__':
    main()
