# Preserved setup and hardening observations

1. A narrow read of the historical collections manifest initially treated its
   integer `members` count as a row list and raised `TypeError: 'int' object is
   not iterable`. The next read used its actual `files` dictionary. No subject was
   imported and no process/native/runtime experiment occurred.
2. The first guarded structural parse of the historical DEX refused
   `DEX owner descriptor`: the draft incorrectly required every method owner to
   be an object descriptor. Legal array `clone` method owners use array
   descriptors. The parser now preserves those exact symbolic array owners;
   the historical fixture parses 335 classes and 2,307 Code bodies. This is a
   parser-fixture correction, not a candidate product/runtime result.
3. Independent draft review found that SDK comparison dominance alone allowed a
   jump into the middle of the SDK read/constant/branch sequence; DEX also needed
   separate SDK and threshold registers. The final guard proof refuses both.
   The independent review also caught JVM getstatic accepting a Methodref tag;
   field/invoke opcodes now validate their legal constant-pool tag.
4. Producer review identified the known ConcreteHostProbe mechanical family,
   source-family spoofing, helper call-kind validation and inert constructor
   topology requirements. The packet includes exact fixture-family exclusions,
   owner/SourceFile binding, legal invoke kinds and exact inert constructors.
5. The independent reviewer's initial Python import created one owned
   `__pycache__/inspect_artifacts.cpython-314.pyc`. Only that generated cache was
   removed, and its exact identity is retained in `cache-cleanup.json`. Source
   bytes were untouched. Subsequent control imports disable bytecode writes.
6. Final self-review found that a four-allocation DEX count alone allowed
   hoisting future drawable constructors before earlier setters. The helper
   proof now requires one pending next-drawable allocation/constructor before
   each next setter/postcheck. A positive and hoisting/omitted-postcheck/call-kind
   data controls were added; no product/runtime artifact was executed.

All final preparation controls are pure data checks. No compiler/JVM/product,
native, process custody or hosted-dispatch result exists in this packet.
