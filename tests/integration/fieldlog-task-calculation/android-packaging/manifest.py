#!/usr/bin/env python3
"""Add the local checklist's permission and loopback-only policy to the ordinary manifest."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ANDROID = "http://schemas.android.com/apk/res/android"
ET.register_namespace("android", ANDROID)

source, destination = map(Path, sys.argv[1:])
manifest = ET.parse(source)
root = manifest.getroot()
application = root.find("application")
name = f"{{{ANDROID}}}name"
policy = f"{{{ANDROID}}}networkSecurityConfig"
if (root.tag != "manifest" or application is None or policy in application.attrib
        or any(p.get(name) == "android.permission.INTERNET" for p in root.findall("uses-permission"))):
    raise SystemExit("Unexpected ordinary Android manifest")
permission = ET.Element("uses-permission", {name: "android.permission.INTERNET"})
root.insert(list(root).index(application), permission)
application.set(policy, "@xml/checklist_network")
application.set(f"{{{ANDROID}}}label", "FieldLog")
with destination.open("xb") as stream:
    ET.indent(manifest, space="  ")
    manifest.write(stream, encoding="utf-8", xml_declaration=True)
