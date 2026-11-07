# V4 interpreter startup is outside the selected execution closure

Changes are required before selecting this execution closure. The supplied
fourteen synthetic integrity controls pass independently, and the architecture
successfully closes the earlier product-only scaffolding gap for payload,
classes and the complete JDK. However, Python identity is only the resolved
executable file hash. The trusted bootstrap and children use `-I -B`, which
still enable site initialization and virtual-environment `.pth` startup.

The independent witness uses the released synthetic selected-policy fixture,
without changing its manifest, payload, product/support classes, selected JDK
tree or resolved interpreter binary. It creates an owned venv with the same
resolved interpreter and adds a `.pth` file in that venv's site-packages. The
file writes a benign marker before the bootstrap runs. Under `-I -B`, the
actual bootstrap accepts the synthetic certificate and the marker proves
unselected startup code executed. All owned venv/scratch files were removed;
no global installation or other project's process was changed.

This is actual bootstrap/checker control flow under an explicitly synthetic
selected trust root. The real released product manifest/policy/producer remain
unselected and refused. It does not demonstrate an accepted production matrix
or grant any source, native, OTA or GA acceptance.

The external trusted parent and every Python child need an explicit no-site
startup contract, including `-S` and checks of actual flags. They also need
selected and freshly verified interpreter runtime/import support, executable
and installation/prefix/search-path identities. The Python executable dynamically
uses libraries and standard-library code; executable bytes alone do not close
that runtime. Inherited environment sanitization does not remove installation
startup code. A venv with the same binary must not gain authority through an
unselected startup/import graph.

Retain the existing acyclic parent/bootstrap trust-root separation. Check the
complete selected interpreter graph before descendant imports; include a
same-binary venv/site startup negative and changes to runtime/import-support
artifacts. A documented explicitly excluded startup path must actually remain
unreachable in the selected entry and children. Metadata claiming the same
interpreter is insufficient.
