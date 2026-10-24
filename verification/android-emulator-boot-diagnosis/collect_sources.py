#!/usr/bin/env python3
"""Bind official platform documentation without vendoring emulator implementation."""
import base64
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent


def read(url):
    return urllib.request.urlopen(url, timeout=8).read()


def main():
    observed = datetime.datetime.now(datetime.timezone.utc).isoformat()
    docs = 'https://developer.android.com/studio/run/emulator-networking-interconnect'
    html = read(docs)
    assert b'-WiFiPacketStream' in html
    entries = [{
        'url': docs, 'retrievedUTC': observed, 'responseSHA256': hashlib.sha256(html).hexdigest(),
        'observedControl': ['-feature', '-WiFiPacketStream'],
        'scope': 'Official documented per-process fallback to previous emulator networking model',
    }]
    for repo, ref, path, observations in (
        ('external/qemu', 'emu-master-dev', 'android-qemu2-glue/netsim/NetsimWifiForwarder.cpp',
         ['NetsimWifiForwarder::init obtains a channel before creating the Wi-Fi packet stream']),
        ('tools/netsim', 'main', 'src/backend/packet_streamer_client.cc',
         ['GetChannel serializes channel setup with a mutex',
          'GetChannel retries channel readiness and sleeps between retries',
          'This is current public source; it is not proven identical to installed emulator build 16428233']),
    ):
        base = f'https://android.googlesource.com/platform/{repo}/+/'
        meta = read(base + f'refs/heads/{ref}?format=JSON')
        revision = json.loads(meta.decode().split('\n', 1)[1])['commit']
        url = base + revision + '/' + path
        data = base64.b64decode(read(url + '?format=TEXT'))
        assert b'CreateChannel' in data
        entries.append({'url': url, 'revision': revision, 'retrievedUTC': observed,
                        'decodedSourceSHA256': hashlib.sha256(data).hexdigest(),
                        'observations': observations, 'implementationCopiedIntoProduct': False})
    output = {'schema': 1, 'command': ['python3', 'verification/android-emulator-boot-diagnosis/collect_sources.py'],
              'collectorSHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'sources': entries}
    path = HERE / 'official-sources.json'
    assert not path.exists(), 'preserve existing source packet'
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'output': str(path), 'sources': len(entries), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
