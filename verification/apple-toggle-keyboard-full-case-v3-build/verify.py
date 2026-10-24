#!/usr/bin/env python3
"""Read-only exact packet/source/tool/product/archive verification; no processes."""
import pathlib
import sys
import build_runner as b


def audit(event, args):
    if event in ['subprocess.Popen', 'os.system']:
        raise RuntimeError('Process operation forbidden by read-only build verification')


sys.addaudithook(audit)
seal = b.read(b.BASE/'packet-seal.json')
for name, expected in seal['files'].items():
    path = b.ROOT/name
    b.require(b.file_record(path) == expected, 'Sealed build evidence changed: '+name)
source = b.revalidate()
b.require(source == b.read(b.BASE/'source-before.json'), 'Accepted source tree not restored')
manifest = b.read(b.BASE/'supplement/build-products-manifest.json')
b.require(b.tool_metadata() == b.read(b.BASE/'supplement/tools-verified.json'), 'Tools changed')
b.require(b.tree(b.PRODUCTS) == manifest['products'], 'Compiled product tree changed')
archive = b.BASE/'supplement/test-runner-products.tar.gz'
b.require(b.sha(archive) == manifest['productArchiveSHA256'], 'Archive changed')
b.verify_archive(archive, manifest['products'])
for name, expected in manifest['originalEvidence'].items():
    b.require(b.sha(b.BASE/name) == expected, 'Original compiler/failure evidence changed: '+name)
print('verified: compiler succeeded; initial recorder failed on generated empty directories; source restoration and product archival supplement verified; native execution pending')
