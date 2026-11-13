#!/usr/bin/env python3
"""Finite remote-only collector for the two frozen identity network methods.

Importing this file is side-effect free. The pure validators are intentionally
shared with stdlib fault controls; they do not establish runtime isolation.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import uuid

FROZEN_PRODUCT_DIGEST = "023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e"
FIXTURE_SOURCE_DIGEST = "ab8f8dbec5894ca96dd673db828a01afdc39a54ad008a2a2d4e598c1c62ce2f7"
SELECTED_SOURCE_DIGEST = "8d0139c8c64e02f29f42a96384661f60dd7b724fa5fb4d5f54f6e7c1b7b78cd3"
CURRENT_SOURCE_BASE = 'verification/identity-network-current-source-v1/'
CURRENT_SELECTION_SHA256 = '14868be39631a86c79f4ba7b6bfb9386c6d80062ef4d0ddebbf55aea833afc96'
CURRENT_SOURCE_DIGEST = '07bb7b5d7b518f487e4981dc4aa0e911f16c99a5bbbf96ea0bdc204d9455ccd9'
CURRENT_SOURCE_COUNT = 185
SUCCESSOR_SOURCE_BASE = 'verification/identity-network-current-source-v2/'
SUCCESSOR_SELECTION_SHA256 = 'bfeca22fb174a283206c8b9db0ffd858ba52849444384eeea62b728717b24272'
SUCCESSOR_SOURCE_DIGEST = '4d2eefb1fe856f83507fc643c46ba9f2171b5f11810ffad3942c345b209e9eab'
SUCCESSOR_SOURCE_COUNT = 190
PRIVATE_SOURCE_BASE = 'verification/identity-network-current-source-v3/'
PRIVATE_SELECTION_SHA256 = '37ce1ac2ce60e65fa51bc3c99417cc2ee666edaa114e7e9c3cdafe17fd468a02'
PRIVATE_SOURCE_DIGEST = '458b1eefe69c390a10676690434ee05fdfecda11a430347844f855bfc2be3b3c'
PRIVATE_SOURCE_COUNT = 201
BROWSER_SOURCE_BASE = 'verification/identity-network-current-source-v4/'
BROWSER_SELECTION_SHA256 = '7ebc5dd2f3eaf093442ecee1bf26078023d934cc62c216b90aa417cee86331cf'
BROWSER_SOURCE_DIGEST = 'e35af32a6ebaafec4d9154ca2d04bdb0655cdd57ad5c7e06988db8e1aa65477d'
OPERATION_SOURCE_BASE = 'verification/identity-network-current-source-v5/'
OPERATION_SELECTION_SHA256 = 'b204f4cda567bceedf47f4f23d2466c77a9a99bb071cd1cde1d22723c6825969'
OPERATION_SOURCE_DIGEST = '9514758b76335408231b72c1a9da06b55cce77b75c47bb79d153afb5e3ca7552'
LIFETIME_SOURCE_BASE = 'verification/identity-network-current-source-v6/'
LIFETIME_SELECTION_SHA256 = '243a0cbb98f15f048d0d12dbf5d6fb5ff89e616d0f21dd0dba786fe8fac1e211'
LIFETIME_SOURCE_DIGEST = '2cdc4df04d645fee0ca7d6e33aa02d96d02b8bc7cd3fb6848476d0a2bc7a7c11'
COMMIT_SOURCE_BASE = 'verification/identity-network-current-source-v7/'
COMMIT_SELECTION_SHA256 = '77406d745d798c83be28f1b26be08c3b396cee1093e4726b147ddc0a5e6b36ed'
COMMIT_SOURCE_DIGEST = '619e21ed7669a1b5782c6c4ccc4e0647aaba20433002ab8b4045e0d57df9891c'
PROXY_SOURCE_BASE = 'verification/identity-network-current-source-v8/'
PROXY_SELECTION_SHA256 = 'a5ade3b244f15d610b141eee05dc0c754adbb7e9fcaf71dca52b0100939124fb'
PROXY_SOURCE_DIGEST = 'cd8dfff529b3e461adbea1fec2b21dbbb0ece6ba323a26f63d5b3676cbd41c6f'
BUILD_READ_SOURCE_BASE = 'verification/identity-network-current-source-v9/'
BUILD_READ_SELECTION_SHA256 = 'd0c51485ce5fa56a94cfea1ffaf59b0afb383356c39619058c387f56ac58328e'
BUILD_READ_SOURCE_DIGEST = 'db080c4ff0b1bde4b0a03e1dccccb8a829c9feb84206f90dcf25620bc990c168'
BROWSER_BUILD_SOURCE_BASE = 'verification/identity-network-current-source-v10/'
BROWSER_BUILD_SELECTION_SHA256 = '542ceeff624ef3befd51e089cbab646cbb93242a4f48a0fae7033a8df0180f1d'
BROWSER_BUILD_SOURCE_DIGEST = 'b45def2cb208ba76c5472ac49bd379278d744fc7831b2e8da59e1baf7169c505'
OWNED_EVIDENCE_SOURCE_BASE = 'verification/identity-network-current-source-v11/'
OWNED_EVIDENCE_SELECTION_SHA256 = '7310bb24b6147d867eb0ef47afd6fb612dbe9c80903633d62268b68c8bf77d20'
OWNED_EVIDENCE_SOURCE_DIGEST = 'e3df1a2cf113db904dd48cca93d8492ba11c6b0f3201a6978596866d415f0e33'
HOSTED_COMPILER_SOURCE_BASE = 'verification/identity-network-current-source-v12/'
HOSTED_COMPILER_SELECTION_SHA256 = 'a58e82e2f5aff62244221cd99c5dbb6d5d23b6b00a0ece50bff074578f122591'
HOSTED_COMPILER_SOURCE_DIGEST = '495547c77707cf511b62e6aa9b6b9f5dbcb0c82969e6193ebd9e2d3b77bf7e9d'
HOSTED_COMPILER_INPUTS = ('console/src/state/browser-session-controller.ts', 'console/src/state/workspace-controller.ts', 'console/src/api/cookie-build-catalog-client.ts', 'console/src/domain/build-catalog.ts')
CATALOG_JOIN_SOURCE_BASE = 'verification/identity-network-current-source-v13/'
CATALOG_JOIN_SELECTION_SHA256 = '6dc37c2e86ba39377751d8fe03bdfbf11e2cce4a4613fbdd39c172fb37d6134a'
CATALOG_JOIN_SOURCE_DIGEST = 'cb35b0bde7d3eda61b16b7e754c37ca642c7a16571e8d06671455459a2f908c8'
CATALOG_JOIN_INPUTS = HOSTED_COMPILER_INPUTS
CATALOG_JOIN_DELTA = {'hosted/lib/mixer_hosted/browser_auth/active_read.ex': {'after': {'bytes': 8201,
                                                                   'sha256': '76b369e9f8117862bbac751734d09e2e8f6426eec9c3c5f9c1e24d293badc8e2'},
                                                         'before': {'bytes': 7957,
                                                                    'sha256': 'd2c356d9fa47cd3bdb4528f0647231491b2fe8a9a050b48d49f4efc8d969868c'}},
 'hosted/lib/mixer_hosted/browser_auth/build_catalog_admission.ex': {'after': {'bytes': 10797,
                                                                               'sha256': '35e59b49ccfa230111778c6abb485bec8559cbb909ff78d609bc5188b0e684f1'},
                                                                     'before': None},
 'hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex': {'after': {'bytes': 48754,
                                                                        'sha256': 'fef31903c1ac4f1a3aa3c4e0f22e55623ed878d68c4ceaf0a78a6087c2a54556'},
                                                              'before': {'bytes': 47573,
                                                                         'sha256': 'f71d79b92065d2137363f10de89c137b95ce5758b0e4c21b88faaeb8a779fcfc'}},
 'hosted/lib/mixer_hosted/browser_auth/relation_manifest_v3.ex': {'after': {'bytes': 859,
                                                                            'sha256': '34a650acde4959083c0ab47aac3a4b61164a002729acab588613cdc1979f31ed'},
                                                                  'before': None},
 'hosted/lib/mixer_hosted/browser_auth/runtime_config.ex': {'after': {'bytes': 8396,
                                                                      'sha256': '2fac58266ac73065b88ac2846bf401c0a32c122c84a9ad3564945c92c8c59c4a'},
                                                            'before': {'bytes': 7874,
                                                                       'sha256': '0ce7e28450b7f5652313fc22cb909ea6e65cc8b4a8edcc960669d5a950da0962'}},
 'hosted/lib/mixer_hosted/browser_auth/runtime_owner.ex': {'after': {'bytes': 27533,
                                                                     'sha256': '81c54c0a7ec53dd3d788be0d130c6d9abf68e95d0d0a3ae269fe0130e51bf537'},
                                                           'before': {'bytes': 26031,
                                                                      'sha256': '28582f7ae7340f3375de077e1381335d3c193b4da47dac9acf9751dbf2965c14'}},
 'hosted/lib/mixer_hosted/browser_auth/store.ex': {'after': {'bytes': 24830,
                                                             'sha256': 'a310b0a8ec8fb28fe78f8d69b3758399d88d096a7bd2a97fefbaaca091c188bb'},
                                                   'before': {'bytes': 24180,
                                                              'sha256': '4c1b726412bcdec9de5bd41730533aaf698b20101a7d8bd5cb048a08f8e80f3a'}},
 'hosted/lib/mixer_hosted/customer_build_catalog.ex': {'after': {'bytes': 609,
                                                                 'sha256': '2c498c3780fa49694ed6355370c72c3fd2dc7eac70418ee4006e1c34ace5befe'},
                                                       'before': None},
 'hosted/lib/mixer_hosted/customer_build_catalog/context.ex': {'after': {'bytes': 7674,
                                                                         'sha256': '1c3f04c256938e790e6556251f9c38d8e01a83d7c80129f935d5be5d7d605177'},
                                                               'before': None},
 'hosted/lib/mixer_hosted/customer_build_catalog/input.ex': {'after': {'bytes': 2636,
                                                                       'sha256': '5a951fc25a020a015f79faa1d5c7d48598965141bea333b63e67cf2c9ecdcdf3'},
                                                             'before': None},
 'hosted/lib/mixer_hosted/customer_build_catalog/schema.ex': {'after': {'bytes': 33899,
                                                                        'sha256': '3ae427632cee7932a24eb02a26cf560911c5e560457616e21e9588dfc6b8f790'},
                                                              'before': None},
 'hosted/lib/mixer_hosted/customer_build_catalog/snapshot.ex': {'after': {'bytes': 2292,
                                                                          'sha256': 'df96d686bb1ecffe98482738598bd0faf795c55b6d426b3fad3ab4fa2490c10b'},
                                                                'before': None},
 'hosted/lib/mixer_hosted_web/browser_build_catalog_dispatcher.ex': {'after': {'bytes': 2441,
                                                                               'sha256': '884e4f3aad7e3c102bd9d541c4bce11f7258aca93478a9e2c890f60f3fb1d0ed'},
                                                                     'before': None},
 'hosted/lib/mixer_hosted_web/browser_build_catalog_request.ex': {'after': {'bytes': 1730,
                                                                            'sha256': '146065231dcd41655ae0233c45f976afbd69389f7ac7237af26ce3867fc879b3'},
                                                                  'before': None},
 'hosted/lib/mixer_hosted_web/browser_http.ex': {'after': {'bytes': 7099,
                                                           'sha256': '4065474f1c12c364dd71f73cfdd1855a29bea2d94f5e32b2346141bd2ea622b7'},
                                                 'before': {'bytes': 6215,
                                                            'sha256': '2a617926bcf96f2cf25f03923567295792feac8e4cfd4038b4ca5109d2cf3737'}},
 'hosted/scripts/test-local.py': {'after': {'bytes': 25951,
                                            'sha256': 'f0585945da899d16f36c1c15531c867445ee390fea5fa8fa81f4f16f3dc1e5e7'},
                                  'before': {'bytes': 25108,
                                             'sha256': '0a0e1f844fe42fb4881cbac58efcb38d543e4125d3bd4dd6f495272cd38ca277'}},
 'hosted/test/customer_build_catalog_input_test.exs': {'after': {'bytes': 3553,
                                                                 'sha256': 'cca5b433ed030a9261860cc1a6fe78e6d488b73a51d2e1e39b117621903d8921'},
                                                       'before': None},
 'hosted/test/mixer_hosted/browser_auth/catalog_browser_current_surface_join_test.exs': {'after': {'bytes': 15617,
                                                                                                   'sha256': '90aa19229485ad6dba89cc4154b7dbca71d7d30ada816ad72b12ca22b64e0758'},
                                                                                         'before': None},
 'hosted/test/mixer_hosted/browser_auth/private_login_http_test.exs': {'after': {'bytes': 61834,
                                                                                 'sha256': '97889c149ddc69458b46f2d4e99a64b1ce37f4770e049515349b25d82fdc62f6'},
                                                                       'before': {'bytes': 50578,
                                                                                  'sha256': '0d0f4d0fa13a4cd1f0b635c75c56a31580d2dc623bbf866b1b1cc17bae2dc3a9'}},
 'hosted/test/mixer_hosted/browser_auth/runtime_config_test.exs': {'after': {'bytes': 21236,
                                                                             'sha256': 'c12b571e3a213955eee7b484d96af048c7f44b6e0dcaff81830bb80e4ec26c63'},
                                                                   'before': {'bytes': 20142,
                                                                              'sha256': 'fcd79eb95485dbe8e20b2fe4ec104daad59fc7eb78b607571132f89c0f0b2e82'}},
 'hosted/test/support/browser_build_catalog_client.mjs': {'after': {'bytes': 5118,
                                                                    'sha256': '3f4438faf287d198075a4c76d28daa33a2ff47b169a4e573ec44ebd0759a4f37'},
                                                          'before': None}}

FORMAT_BASE = "verification/identity-network-fixture-amendment-v2/metadata/"
FORMAT_SHA256 = "45f0c33f8f521ff43ed58b13c34466dea593ecd1c9e8aab166b1e075da07ef84"
FORMAT_PACKET = "46d75ed1393db3250b5b7df2611b82bdc5c49f5c1ca7ec64ff8f40e24f179760"
FORMAT_PACKET_SHA256 = "b4c80bfbfbb95e2affe77de1d2a1fc2067baec9f9a7132b3989369cd4c968dee"
FIXTURE_BASE = "verification/identity-network-fixture-amendment-v1/metadata/"
FIXTURE_SHA256 = "510771949fe7e95d81cd64f7a8d65df722fa7aa79293b55c773a61bbce8e351b"
FIXTURE_PACKET = "13a0b3d84a5140d8fd73d2d4468a5675f6fcaeb8467788bdbda469c18f3a1f4c"
FIXTURE_PACKET_SHA256 = "def35da9e8f01115a78356b836203fb6ef42a2eef76c058a8fbbafcc6f01be66"
FIXTURE_REVIEW_SHA256 = "613876f8c91fb07e08100ba8cf02906cf61b67ae8573703ecced44073c84fa5e"
FIXTURE_REVIEW_PACKET = "f8d04d5f4f118f940f7183f16b217ca401b34fcda5558dd7929ce2d5657d446d"
FROZEN_LOCK_SHA256 = "1eada39dcaf4863d02d39f51e218d2bad8908b36a0cba47ff2d16037b7bcf837"
CONTRACT_SHA256 = "695a165d41e9d4eac5fdc582b835a60f5c3bbdd6f0fb3131c0ad27ffbbe135bc"
CONTRACT_PACKET = "a3a806d83e285213df4c0e951282686dcfcfa81701e8005040d5172b3300050d"
CONTRACT_PACKET_SHA256 = "88e7b446e1470de0e1c54d770248ef6627a9bfb5623118d182a8dbd8b12c6c46"
CONTRACT_BASE = "verification/identity-production-network-contract/"
AMENDMENT_BASE = "verification/identity-network-image-amendment-v1/metadata/"
AMENDMENT_SHA256 = "6a2ec88721d89a28e40961f834b856598ba0f6f14d88708906cf3931e0e33afa"
AMENDMENT_PACKET = "9ddc12c8277b120dcd8ef7577dd9da03d245b8502802db85399a6f1104bcbdc8"
SOURCE_REVIEW_PACKET = "261023b77cb55255f666959f367330783a354174252ed23b71145566f87ba597"
EXECUTION_BASE = "verification/identity-network-image-amendment-v2/metadata/"
EXECUTION_SHA256 = "b447fe5919c4e73d86aee4da707570127de2c35ecdae5a7b90b0163eb9bc436c"
EXECUTION_PACKET = "0e35cd6dcc1685b16745def4fe0217fc60e5d703c95a5cddbfd2409381c63b6d"
EXECUTION_PACKET_SHA256 = "dcac91f5cae0a2495f79448a76098975edc18db0ce96a1e769106244a0cf8061"
OLD_TEST_IMAGE = {
    "ref": "hexpm/elixir@sha256:3571d320ec0656c38c76b4c362a8e0c0fd6f9b58cec6448a08e43a82940d4e43",
    "index": "sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde",
    "config": "sha256:6631543fddfe053ddbd30435318916667d5da87b5f5ec0644893d146a539370e",
    "platform": "linux/amd64",
}
PRODUCT_COMMIT = "9e860ea12074ca31bef4087ce34177a03f295dd8"
IMAGES = {
    "test": {
        "ref": "hexpm/elixir@sha256:ed110657152803079f311913be4effe02874e2c714a1b5a38891873b7f2a16c5",
        "config": "sha256:857e84a618d1f76390220fbff2e7d54d588aea4f772ab1e60dacfe3fa02602cc",
    },
    "pg": {
        "ref": "library/postgres@sha256:cf5d353f55240ecc2f811827a15c7d1f2d562f08019b49dca12b5a59f4ab5962",
        "config": "sha256:6a35283e53fbe883da6a6ffbce8d3999dc66076cc5c4e2f1d21bdbd9e26bf86f",
    },
}
BOOTSTRAP = {
    "hex": {
        "url": "https://builds.hex.pm/installs/1.20.0/hex-2.5.1-otp-29.ez",
        "sha512": "6629f4b4bb2e040326151ebb853aad065e342c65ad3a0f2a2674dcf7164eb4328d6c929513d7230309ad75042024e72bef0e0a51ebff373b4173d2746b1772b7",
        "version": "2.5.1",
    },
    "rebar": {
        "url": "https://builds.hex.pm/installs/1.18.4/rebar3-3.28.0-otp-29",
        "sha512": "b51946058fbe4aa823185bfe27204be59be439982ac3a3e1dbd9f8260b9af046fcfdfbd9066283c3fbba5a2a45dc3570550c12a9a548daf223b80cac222a6d0f",
        "version": "3.28.0",
    },
}
RESOURCES = {"prepare": (2147483648, 2, 256), "test": (2147483648, 2, 256), "pg": (1073741824, 1, 128)}
OLD_TMPFS = {'pg': {'/tmp': 'rw,nosuid,nodev,size=67108864,mode=1777',
        '/var/lib/postgresql/data': 'rw,nosuid,nodev,size=536870912,mode=0700',
        '/var/run/postgresql': 'rw,nosuid,nodev,size=16777216,mode=0775'},
 'prepare': {'/tmp': 'rw,nosuid,nodev,size=67108864,mode=1777',
             '/workspace': 'rw,nosuid,nodev,size=1073741824,mode=0755'},
 'test': {'/run': 'rw,nosuid,nodev,size=16777216,mode=0755',
          '/tmp': 'rw,nosuid,nodev,size=67108864,mode=1777',
          '/workspace': 'rw,nosuid,nodev,size=1073741824,mode=0755'}}
TMPFS = {'pg': {'/tmp': 'rw,nosuid,nodev,size=67108864,mode=1777',
        '/var/lib/postgresql/data': 'rw,nosuid,nodev,size=536870912,mode=0700',
        '/var/run/postgresql': 'rw,nosuid,nodev,size=16777216,mode=0775'},
 'prepare': {'/tmp': 'rw,nosuid,nodev,noexec,size=67108864,mode=1777',
             '/workspace': 'rw,nosuid,nodev,noexec,size=1006632960,mode=0755',
             '/workspace/tooling': 'rw,nosuid,nodev,exec,size=67108864,mode=0755'},
 'test': {'/run': 'rw,nosuid,nodev,size=16777216,mode=0755',
          '/tmp': 'rw,nosuid,nodev,noexec,size=67108864,mode=1777',
          '/workspace': 'rw,nosuid,nodev,noexec,size=1006632960,mode=0755',
          '/workspace/tooling': 'rw,nosuid,nodev,exec,size=67108864,mode=0755'}}
MOUNT_POLICY = {'descendants': 'only-exact-selected-tooling-child-mount-is-permitted',
 'max_bytes': 65536,
 'max_selected_line_bytes': 4096,
 'modes': {'/run': 493,
           '/tmp': 1023,
           '/workspace': 493,
           '/workspace/tooling': 493},
 'required': 'tmpfs-rw-nosuid-nodev-exact-size-noexec-except-tooling',
 'roles': {'prepare': ['/workspace', '/workspace/tooling', '/tmp'],
           'test': ['/workspace', '/workspace/tooling', '/tmp', '/run']},
 'source': '/proc/self/mountinfo',
 'tooling_mount_parent': 'workspace-mount-id'}
REBAR_TRANSFER = {'copy': 'exclusive-target-complete-close-sha512-before-chmod-direct-execution',
 'destination': '/workspace/tooling/rebar3',
 'max_bytes': 16777216,
 'remove': 'only-owned-source-after-complete-target-verification',
 'sha512': 'b51946058fbe4aa823185bfe27204be59be439982ac3a3e1dbd9f8260b9af046fcfdfbd9066283c3fbba5a2a45dc3570550c12a9a548daf223b80cac222a6d0f',
 'source': '/workspace/downloads/rebar3'}
CAPS = {"prepare": set(), "test": {"NET_ADMIN", "NET_BIND_SERVICE"}, "pg": {"CHOWN", "DAC_OVERRIDE", "FOWNER", "SETUID", "SETGID"}}
BASE_ENV = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "LANG": "C.UTF-8", "HOME": "/workspace/home", "MIX_ENV": "test",
    "MIX_HOME": "/workspace/tooling/mix", "MIX_REBAR3": "/workspace/tooling/rebar3",
    "HEX_HOME": "/workspace/tooling/hex", "XDG_CACHE_HOME": "/workspace/cache",
    "ERL_CRASH_DUMP": "/workspace/evidence/erl_crash.dump", "ERL_CRASH_DUMP_SECONDS": "0",
}
TEST_ENV = {**BASE_ENV, "MIXER_TEST_DATABASE_PORT": "5432", "MIXER_TEST_IDENTITY_EVIDENCE": "/workspace/evidence/identity"}
EXPECTED_METHODS = (
    ("Elixir.MixerHosted.Identity.KeyOwnerLinuxNetworkTest", "test K03 production resolver/classifier pins public peer despite rebinding; private sink remains untouched"),
    ("Elixir.MixerHosted.Identity.StartupLinuxNetworkTest", "test IS04 IS05 actual configured startup cold production DNS TLS admission and lifecycle"),
)
TEST_ROOTS = ["test/mixer_hosted/identity/key_owner_linux_network_test.exs", "test/mixer_hosted/identity/startup_linux_network_test.exs"]
MAX_COMMAND_BYTES = 8388608
MAX_LOG_BYTES = 67108864
MAX_ARCHIVE_BYTES = 536870912
MAX_ARTIFACT_BYTES = 268435456
# Mix 1.20.4 treats missing BEAMs as mtime 0 and requires source mtime > 0.
# Keep deterministic archive timestamps strictly above that missing-file sentinel.
PREPARED_MTIME = 1
GENERATED_DAG_PATH = "hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl/source.dag"
MAX_GENERATED_DAG_BYTES = 65536
GENERATED_DAG_PARENTS = ["/workspace", "/workspace/hosted", "/workspace/hosted/deps", "/workspace/hosted/deps/telemetry", "/workspace/hosted/deps/telemetry/_build", "/workspace/hosted/deps/telemetry/_build/prod", "/workspace/hosted/deps/telemetry/_build/prod/lib", "/workspace/hosted/deps/telemetry/_build/prod/lib/.rebar3", "/workspace/hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl"]
TELEMETRY_INPUTS = {
    "hosted/deps/telemetry/rebar.config": {"bytes": 943, "sha256": "2ac5ee04618133d912fcafe68859904ee88aa7bfac678c8165ce1dfb32cbc3b0"},
    "hosted/deps/telemetry/src/telemetry.erl": {"bytes": 17044, "sha256": "8bb2a1fa116def38f63a5b36b65fdc9af98022e6e378e047f38d49b584564278"},
    "hosted/deps/telemetry/src/telemetry.app.src": {"bytes": 533, "sha256": "29778243956492d0d255bf2289fe5e4f6b10f22d282ca5679015a478c1eb33d2"},
}


class CollectorError(ValueError):
    """A refusal, partial observation, or failed qualification."""


def require(condition, message):
    if not condition:
        raise CollectorError(message)


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _file_row(body):
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}


def validate_amendment_manifest(body):
    """The compiled root admits this one finite packet, never an overlay."""
    packet = json.loads(body)
    require(isinstance(packet, dict) and set(packet) == {"schema", "files", "tree_digest_sha256"} and type(packet["schema"]) is int and packet["schema"] == 1, "amendment packet shape")
    files = packet["files"]
    require(isinstance(files, dict) and len(files) == 78 and packet["tree_digest_sha256"] == AMENDMENT_PACKET and canonical_digest(files) == AMENDMENT_PACKET, "amendment packet seal mismatch")
    for path, row in files.items():
        name = PurePosixPath(path)
        require(not name.is_absolute() and ".." not in name.parts and str(name) == path and "\\" not in path and path != "packet-manifest.json", "unsafe amendment metadata path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"} and type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES and bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "amendment metadata row shape")
    return files


def predecessor_metadata_paths():
    paths = [CONTRACT_BASE + "contract.json", CONTRACT_BASE + "packet-manifest.json"]
    for label in ("elixir", "postgres"):
        paths += [CONTRACT_BASE + "inputs/registry/" + label + suffix for suffix in ("-index.json", "-amd64-manifest.json", "-amd64-config.json")]
    return paths


def validate_selected_metadata(metadata):
    """Validate both immutable namespaces before any image/runtime operation."""
    require(isinstance(metadata, dict) and all(isinstance(body, bytes) for body in metadata.values()), "missing selected metadata")
    manifest_path = AMENDMENT_BASE + "packet-manifest.json"
    require(manifest_path in metadata, "missing amendment seal")
    files = validate_amendment_manifest(metadata[manifest_path])
    expected_paths = set(predecessor_metadata_paths()) | {manifest_path} | {AMENDMENT_BASE + path for path in files}
    require(set(metadata) == expected_paths, "missing or extra selected metadata")
    old_packet_body = metadata[CONTRACT_BASE + "packet-manifest.json"]
    require(hashlib.sha256(old_packet_body).hexdigest() == CONTRACT_PACKET_SHA256, "predecessor packet bytes mismatch")
    old_packet = json.loads(old_packet_body)
    require(old_packet["tree_digest_sha256"] == CONTRACT_PACKET and canonical_digest(old_packet["files"]) == CONTRACT_PACKET, "contract packet seal mismatch")
    require(hashlib.sha256(metadata[CONTRACT_BASE + "contract.json"]).hexdigest() == CONTRACT_SHA256, "selected predecessor contract drift")
    for path in predecessor_metadata_paths():
        if path != CONTRACT_BASE + "packet-manifest.json":
            require(old_packet["files"][path.removeprefix(CONTRACT_BASE)] == _file_row(metadata[path]), "frozen predecessor metadata hash mismatch")
    for path, expected in files.items():
        require(expected == _file_row(metadata[AMENDMENT_BASE + path]), "frozen amendment metadata hash mismatch")
    amendment_body = metadata[AMENDMENT_BASE + "image-amendment.json"]
    require(hashlib.sha256(amendment_body).hexdigest() == AMENDMENT_SHA256, "selected amendment drift")
    amendment = json.loads(amendment_body)
    require(set(amendment) == {"schema", "operation", "predecessor", "old_test_image", "test_image", "preserved", "prerequisites", "source_review"} and amendment["schema"] == 1 and amendment["operation"] == "replace-test-image-only", "amendment is not the closed image-only change")
    require(amendment["predecessor"] == {"contract_sha256": CONTRACT_SHA256, "packet_manifest_sha256": CONTRACT_PACKET_SHA256, "packet_tree_digest_sha256": CONTRACT_PACKET} and amendment["old_test_image"] == OLD_TEST_IMAGE, "amendment predecessor mismatch")
    new = {**IMAGES["test"], "index": "sha256:1ae099301985ddf8a723ad50cc25e37dd854497aec12cebf984c195570b0d83e", "platform": "linux/amd64", "tag": "hexpm/elixir:1.20.4-erlang-29.1.1-debian-bookworm-20261005-slim"}
    require(amendment["test_image"] == new, "amendment selected image mismatch")
    preserved = {"product_commit": PRODUCT_COMMIT, "product_files": 177, "product_digest": FROZEN_PRODUCT_DIGEST, "lock_sha256": FROZEN_LOCK_SHA256, "postgres": {**IMAGES["pg"], "index": "sha256:cb20a02549a06de2f9b115b934f44ba43593e11663163e1f18d13facb4750de4", "platform": "linux/amd64"}, "bootstrap": BOOTSTRAP, "test_roots": TEST_ROOTS, "contract_boundaries": "all-other-predecessor-contract-fields-unchanged"}
    require(canonical_digest(amendment["preserved"]) == canonical_digest(preserved), "amendment changed a preserved contract")
    review = amendment["source_review"]
    review_base = AMENDMENT_BASE + "source-review/"
    review_body = metadata[review_base + "packet-manifest.json"]
    require(review["relative_namespace"] == "source-review/" and hashlib.sha256(review_body).hexdigest() == review["packet_manifest_sha256"], "source review packet bytes mismatch")
    review_packet = json.loads(review_body)
    require(review["packet_tree_digest_sha256"] == SOURCE_REVIEW_PACKET and review_packet["tree_digest_sha256"] == SOURCE_REVIEW_PACKET and canonical_digest(review_packet["files"]) == SOURCE_REVIEW_PACKET, "source review seal mismatch")
    require({path.removeprefix(review_base) for path in metadata if path.startswith(review_base)} == set(review_packet["files"]) | {"packet-manifest.json"}, "source review membership mismatch")
    for path, expected in review_packet["files"].items():
        require(expected == _file_row(metadata[review_base + path]), "source review file drift")
    for base, label, image in ((CONTRACT_BASE, "elixir", OLD_TEST_IMAGE), (CONTRACT_BASE, "postgres", preserved["postgres"]), (AMENDMENT_BASE, "elixir", new)):
        blobs = {suffix: metadata[base + "inputs/registry/" + label + suffix + ".json"] for suffix in ("-index", "-amd64-manifest", "-amd64-config")}
        for suffix, expected in (("-index", image["index"]), ("-amd64-manifest", image["ref"].split("@")[1]), ("-amd64-config", image["config"])):
            require("sha256:" + hashlib.sha256(blobs[suffix]).hexdigest() == expected, "static image metadata pin mismatch")
        index, manifest, config = (json.loads(blobs[suffix]) for suffix in ("-index", "-amd64-manifest", "-amd64-config"))
        candidates = [entry for entry in index["manifests"] if entry.get("platform") == {"architecture": "amd64", "os": "linux"}]
        require(len(candidates) == 1 and candidates[0]["digest"] == image["ref"].split("@")[1] and manifest["config"]["digest"] == image["config"] and config["os"] == "linux" and config["architecture"] == "amd64", "image index/child/config relation mismatch")
    capabilities = json.loads(metadata[review_base + "analysis/capabilities.json"])
    tools = amendment["prerequisites"]["tools"]
    expected_tools = {row["requested"]: {key: row["object"][key] for key in ("bytes", "sha256")} for row in capabilities["required_objects"] if row["requested"] in tools}
    require(len(tools) == 7 and tools == expected_tools, "prerequisite source tool binding mismatch")
    ca = amendment["prerequisites"]["ca"]
    require({key: ca[key] for key in ("path", "bytes", "sha256")} == {key: capabilities["ca_bundle"][key] for key in ("path", "bytes", "sha256")} and ca["der_sha256"] == sorted(row["der_sha256"] for row in capabilities["ca_bundle"]["certificates"]), "prerequisite CA source binding mismatch")
    return amendment


def validate_execution_manifest(body):
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == EXECUTION_PACKET_SHA256, "execution amendment packet bytes mismatch")
    packet = json.loads(body)
    require(isinstance(packet, dict) and set(packet) == {"schema", "files", "tree_digest_sha256"} and type(packet["schema"]) is int and packet["schema"] == 1, "execution amendment packet shape")
    files = packet["files"]
    require(isinstance(files, dict) and len(files) == 16 and packet["tree_digest_sha256"] == EXECUTION_PACKET and canonical_digest(files) == EXECUTION_PACKET, "execution amendment packet seal mismatch")
    for path, row in files.items():
        name = PurePosixPath(path)
        require(not name.is_absolute() and ".." not in name.parts and str(name) == path and "\\" not in path and path != "packet-manifest.json", "unsafe execution amendment path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"} and type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES and bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "execution amendment row shape")
    return files


def validate_execution_contract(value, image_amendment):
    require(isinstance(value, dict) and set(value) == {"schema", "operation", "base_contract", "prior_amendment", "old_tmpfs", "new_tmpfs", "workspace_partition", "preserved", "mount_observation", "bootstrap_transfer", "runtime_basis", "proof_files"} and type(value["schema"]) is int and value["schema"] == 1 and value["operation"] == "carve-bounded-executable-tooling-tmpfs", "execution amendment is not the closed tooling carve")
    require(value["base_contract"] == image_amendment["predecessor"] and value["prior_amendment"] == {"path": AMENDMENT_BASE, "amendment_sha256": AMENDMENT_SHA256, "packet_tree_digest_sha256": AMENDMENT_PACKET}, "execution amendment predecessor mismatch")
    require(canonical_digest(value["old_tmpfs"]) == canonical_digest(OLD_TMPFS) and canonical_digest(value["new_tmpfs"]) == canonical_digest(TMPFS), "execution amendment tmpfs table mismatch")
    partition = {"total_bytes": 1073741824, "workspace_bytes": 1006632960, "tooling_bytes": 67108864, "roles": ["prepare", "test"], "tooling_path": "/workspace/tooling"}
    require(canonical_digest(value["workspace_partition"]) == canonical_digest(partition) and partition["workspace_bytes"] + partition["tooling_bytes"] == partition["total_bytes"], "execution amendment workspace carve mismatch")
    preserved = {"test_image": image_amendment["test_image"], "prerequisites": image_amendment["prerequisites"], "product_pg_bootstrap_contract": image_amendment["preserved"], "resources": RESOURCES, "capabilities": {role: sorted(caps) for role, caps in CAPS.items()}}
    require(canonical_digest(value["preserved"]) == canonical_digest(preserved), "execution amendment changed an invariant")
    require(canonical_digest(value["mount_observation"]) == canonical_digest(MOUNT_POLICY), "execution amendment mount observation policy mismatch")
    require(canonical_digest(value["bootstrap_transfer"]) == canonical_digest(REBAR_TRANSFER) and REBAR_TRANSFER["sha512"] == BOOTSTRAP["rebar"]["sha512"], "execution amendment bootstrap transfer mismatch")
    basis = value["runtime_basis"]
    require(basis["run_id"] == 40740023326 and basis["artifact_id"] == 12837649788 and basis["delivery_revision"] == "cc350d3303ca71c5d57e87846f6a61304b658fa7" and basis["artifact_tree_digest_sha256"] == "616274ea3bccd45a7b506a0b71de1016b004cbe55e9ca5f3da9fb2cfb9d394bf" and basis["artifact_zip_sha256"] == "932f877ed0fc8cf8ad9457e0ba1b4888ff7bd5a58762b86975f6e887f9673231" and basis["failed_command"] == 22 and basis["source_supported_noexec_inference"] is True and basis["actual_prior_mountinfo"] is False, "execution amendment prior runtime basis mismatch")
    return value


def validate_execution_metadata(metadata):
    require(isinstance(metadata, dict) and EXECUTION_BASE + "packet-manifest.json" in metadata, "missing execution amendment seal")
    files = validate_execution_manifest(metadata[EXECUTION_BASE + "packet-manifest.json"])
    selected_paths = {EXECUTION_BASE + path for path in files} | {EXECUTION_BASE + "packet-manifest.json"}
    require({path for path in metadata if path.startswith(EXECUTION_BASE)} == selected_paths, "missing or extra execution amendment metadata")
    image_amendment = validate_selected_metadata({path: body for path, body in metadata.items() if not path.startswith(EXECUTION_BASE)})
    for path, expected in files.items():
        require(isinstance(metadata[EXECUTION_BASE + path], bytes) and expected == _file_row(metadata[EXECUTION_BASE + path]), "execution amendment metadata hash mismatch")
    body = metadata[EXECUTION_BASE + "execution-amendment.json"]
    require(hashlib.sha256(body).hexdigest() == EXECUTION_SHA256, "selected execution amendment drift")
    value = validate_execution_contract(json.loads(body), image_amendment)
    require(value["proof_files"] == {path: row for path, row in files.items() if path != "execution-amendment.json"}, "execution amendment proof membership mismatch")
    for name in ("image-amendment.json", "packet-manifest.json"):
        require(metadata[EXECUTION_BASE + "proof/prior-v1/" + name] == metadata[AMENDMENT_BASE + name], "execution amendment prior raw proof mismatch")
    proof = EXECUTION_BASE + "proof/runtime/selected/artifact/"
    artifact = json.loads(metadata[proof + "artifact-manifest.json"])
    require(artifact["tree_digest_sha256"] == value["runtime_basis"]["artifact_tree_digest_sha256"] and canonical_digest(artifact["files"]) == artifact["tree_digest_sha256"], "prior failed artifact seal mismatch")
    for name in ("prepare-prerequisites.json", "logs/0022.json", "logs/0022.stderr", "bootstrap-plan.json"):
        require(artifact["files"][name] == _file_row(metadata[proof + name]), "prior failed artifact proof drift")
    reference = value["runtime_basis"]["prerequisite_receipt_reference"]
    require(reference == {"original_path": "verification/github-delivery-blocker-campaign/network-review/selected/artifact/prepare-prerequisites.json", "packet_path": "proof/runtime/selected/artifact/prepare-prerequisites.json", **_file_row(metadata[proof + "prepare-prerequisites.json"])}, "prior actual prerequisite reference mismatch")
    validate_prerequisites(json.loads(metadata[proof + "prepare-prerequisites.json"]), image_amendment["prerequisites"])
    failure = json.loads(metadata[proof + "logs/0022.json"])
    require(failure["exit_code"] == 1 and failure["stdout_complete"] is False and failure["stderr_complete"] is False and failure["timed_out"] is False and b":eacces" in metadata[proof + "logs/0022.stderr"], "prior failed command facts changed")
    return value


def validate_bootstrap_export(tool, data, expected_bytes):
    require(tool in BOOTSTRAP and type(data) is bytes and type(expected_bytes) is int and 0 < expected_bytes <= 16777216, "bootstrap export input shape/bound")
    require(len(data) == expected_bytes, "observed bootstrap artifact byte-count mismatch")
    require(hashlib.sha512(data).hexdigest() == BOOTSTRAP[tool]["sha512"], "observed bootstrap artifact digest mismatch")
    return data


def validate_rebar_transfer(observed, download):
    require(isinstance(observed, dict) and set(observed) == {"source", "destination", "download_bytes", "copied_bytes", "target_bytes", "sha512", "exclusive_create", "closed_before_hash", "owned_download_removed"}, "actual Rebar transfer result missing")
    require(observed["source"] == REBAR_TRANSFER["source"] and observed["destination"] == REBAR_TRANSFER["destination"], "actual Rebar transfer paths mismatch")
    for key in ("download_bytes", "copied_bytes", "target_bytes"):
        require(type(observed[key]) is int and 0 < observed[key] <= REBAR_TRANSFER["max_bytes"], "actual Rebar transfer byte bound")
    require(observed["download_bytes"] == observed["copied_bytes"] == observed["target_bytes"] and observed["sha512"] == BOOTSTRAP["rebar"]["sha512"], "actual Rebar transfer short copy or checksum mismatch")
    require(all(observed[key] is True for key in ("exclusive_create", "closed_before_hash", "owned_download_removed")), "actual Rebar transfer incomplete or not exclusive")
    require(isinstance(download, dict) and type(download.get("bytes")) is int and download["bytes"] == observed["download_bytes"] and download.get("sha512") == observed["sha512"] and download.get("url") == BOOTSTRAP["rebar"]["url"], "actual Rebar transfer not joined to verified download")
    return observed


def validate_mount_observation(role, observed):
    require(role in {"prepare", "test"} and isinstance(observed, dict) and set(observed) == {"role", "source", "read_bytes", "read_sha256", "selected_lines", "path_modes"}, "actual mount observation missing or malformed")
    require(observed["role"] == role and observed["source"] == MOUNT_POLICY["source"] and type(observed["read_bytes"]) is int and 0 < observed["read_bytes"] <= MOUNT_POLICY["max_bytes"] and isinstance(observed["read_sha256"], str) and bool(re.fullmatch("[0-9a-f]{64}", observed["read_sha256"])), "actual mount observation source/bound mismatch")
    paths = MOUNT_POLICY["roles"][role]
    lines = observed["selected_lines"]
    require(isinstance(lines, list) and len(lines) == len(paths), "actual selected mounts missing or extra descendants")
    require(canonical_digest(observed["path_modes"]) == canonical_digest({path: MOUNT_POLICY["modes"][path] for path in paths}), "actual selected mount mode mismatch")
    entries = {}
    for line in lines:
        require(isinstance(line, str) and 0 < len(line.encode()) <= MOUNT_POLICY["max_selected_line_bytes"] and not any(char in line for char in "\n\r\t") and line.count(" - ") == 1, "actual mountinfo line malformed")
        left, right = line.split(" - ")
        fields, filesystem = left.split(), right.split()
        require(len(fields) >= 6 and len(filesystem) == 3 and all(re.fullmatch("[0-9]+", fields[index]) and int(fields[index]) > 0 for index in (0, 1)) and bool(re.fullmatch("[0-9]+:[0-9]+", fields[2])) and fields[3] == "/", "actual mountinfo identity malformed")
        path = fields[4]
        require(path in paths and path not in entries and filesystem[:2] == ["tmpfs", "tmpfs"], "actual mountpoint absent, duplicate, descendant or non-tmpfs")
        flags, super_flags = fields[5].split(","), filesystem[2].split(",")
        require(len(set(flags)) == len(flags) and len(set(super_flags)) == len(super_flags) and all(flags) and all(super_flags), "duplicate or empty actual mount options")
        combined = set(flags) | set(super_flags)
        require({"rw", "nosuid", "nodev"} <= set(flags) and not ({"ro", "suid", "dev"} & combined) and "rw" in super_flags, "actual mount security flags mismatch")
        require(("noexec" not in combined) if path == "/workspace/tooling" else ("noexec" in flags and "exec" not in combined), "actual mount execution policy mismatch")
        sizes = [option.removeprefix("size=") for option in super_flags if option.startswith("size=")]
        require(len(sizes) == 1 and bool(re.fullmatch(r"[0-9]+[kKmMgG]?", sizes[0])), "actual tmpfs size missing or ambiguous")
        text = sizes[0]
        scale = {"k": 1024, "m": 1048576, "g": 1073741824}
        size = int(text[:-1]) * scale[text[-1].lower()] if text[-1].isalpha() else int(text)
        expected = next(option.removeprefix("size=") for option in TMPFS[role][path].split(",") if option.startswith("size="))
        require(size == int(expected), "actual tmpfs size mismatch")
        entries[path] = {"id": fields[0], "parent": fields[1]}
    require(set(entries) == set(paths) and entries["/workspace/tooling"]["parent"] == entries["/workspace"]["id"] and len({entry["id"] for entry in entries.values()}) == len(entries), "actual selected mount hierarchy mismatch")
    require(observed["read_bytes"] >= sum(len(line.encode()) + 1 for line in lines), "actual mount observation byte count inconsistent")
    return observed


def validate_prerequisites(observed, expected):
    require(isinstance(observed, dict), "actual prerequisite result missing")
    required = {"elixir", "otp_patch", "mix", "openssl", "crypto", "crypto_libraries", "tools", "versions", "ca"}
    require(set(observed) == required, "actual prerequisite result incomplete")
    require(observed["elixir"] == expected["elixir"] and observed["otp_patch"] == expected["otp_patch"], "actual VM prerequisite version mismatch")
    require(isinstance(observed["mix"], str) and "Mix 1.20.4" in observed["mix"] and len(observed["mix"]) < 65536, "actual Mix version missing")
    require(isinstance(observed["openssl"], str) and observed["openssl"].startswith(expected["openssl_version_prefix"]) and len(observed["openssl"]) < 65536, "actual OpenSSL version mismatch")
    require(isinstance(observed["crypto"], str) and 0 < len(observed["crypto"]) < 65536, "actual crypto identity missing")
    libraries = observed["crypto_libraries"]
    require(isinstance(libraries, list) and len(libraries) == 1, "actual crypto library identity missing")
    library = libraries[0]
    require(isinstance(library, dict) and set(library) == {"name", "number", "version"} and library["name"] == expected["crypto_library"]["name"] and type(library["number"]) is int and library["number"] > 0 and isinstance(library["version"], str) and library["version"].startswith(expected["crypto_library"]["version_prefix"]) and len(library["version"]) < 65536, "actual crypto library version mismatch")
    require(canonical_digest(observed["tools"]) == canonical_digest(expected["tools"]), "actual executable bytes differ from source inventory")
    versions = observed["versions"]
    require(isinstance(versions, dict) and set(versions) == {"/usr/bin/tar"} and isinstance(versions["/usr/bin/tar"], str) and versions["/usr/bin/tar"].startswith("tar (GNU tar) 1.34") and len(versions["/usr/bin/tar"]) < 65536, "actual tar version missing")
    ca = observed["ca"]
    expected_ca = expected["ca"]
    require(isinstance(ca, dict) and set(ca) == {"path", "bytes", "sha256", "load", "loaded_count", "loaded_der_sha256"}, "actual CA observation missing")
    require(canonical_digest({key: ca[key] for key in ("path", "bytes", "sha256")}) == canonical_digest({key: expected_ca[key] for key in ("path", "bytes", "sha256")}), "actual CA bundle mismatch")
    require(ca["load"] == "explicit-selected-bundle" and type(ca["loaded_count"]) is int and ca["loaded_count"] > 0 and ca["loaded_count"] == len(expected_ca["der_sha256"]) and ca["loaded_der_sha256"] == expected_ca["der_sha256"], "actual loaded OS roots missing or differ from selected bundle")
    return observed


def _validate_source_manifest(manifest, expected_digest, expected_count):
    require(isinstance(manifest, dict) and len(manifest) == expected_count, "source path count mismatch")
    for path, row in manifest.items():
        p = PurePosixPath(path)
        require(path.startswith("hosted/") and not p.is_absolute() and ".." not in p.parts and str(p) == path, "unsafe source path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"}, "source row shape")
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES, "source byte bound")
        require(bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "source hash shape")
    if "hosted/mix.lock" in manifest:
        require(manifest["hosted/mix.lock"]["sha256"] == FROZEN_LOCK_SHA256, "frozen lock mismatch")
    require(canonical_digest(manifest) == expected_digest, "frozen product digest mismatch")
    return manifest


def validate_source_manifest(manifest, expected_digest=SELECTED_SOURCE_DIGEST, expected_count=178):
    require(expected_digest == SELECTED_SOURCE_DIGEST and type(expected_count) is int and expected_count == 178, "caller cannot replace selected source authority")
    return _validate_source_manifest(manifest, SELECTED_SOURCE_DIGEST, 178)


def validate_current_source_manifest(manifest, expected_digest=CURRENT_SOURCE_DIGEST, expected_count=CURRENT_SOURCE_COUNT):
    """Only this explicitly selected successor can authorize current product bytes."""
    require(expected_digest == CURRENT_SOURCE_DIGEST and type(expected_count) is int and expected_count == CURRENT_SOURCE_COUNT, "caller cannot replace current source authority")
    return _validate_source_manifest(manifest, CURRENT_SOURCE_DIGEST, CURRENT_SOURCE_COUNT)


def validate_current_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {CURRENT_SOURCE_BASE + "selection.json", CURRENT_SOURCE_BASE + "selected-source-manifest.json"}, "current source selection membership mismatch")
    body = metadata[CURRENT_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == CURRENT_SELECTION_SHA256, "current source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[CURRENT_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "current source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_current_source_manifest(selected)
    require(selected == CURRENT_MANIFEST and value["predecessor"] == {"source_count": 178, "source_digest_sha256": SELECTED_SOURCE_DIGEST, "source_amendment_sha256": FORMAT_SHA256}, "current source predecessor mismatch")
    delta = {path: {"before": FROZEN_MANIFEST.get(path), "after": row} for path, row in selected.items() if FROZEN_MANIFEST.get(path) != row}
    require(set(FROZEN_MANIFEST) <= set(selected) and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "current source delta mismatch")
    return value


def check_current_source(root):
    """Pure source preflight: no Git, subprocess, container or network activity."""
    metadata = {CURRENT_SOURCE_BASE + name: (root / CURRENT_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_current_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in CURRENT_MANIFEST}
    validate_current_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": CURRENT_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def validate_successor_source_manifest(manifest, expected_digest=SUCCESSOR_SOURCE_DIGEST, expected_count=SUCCESSOR_SOURCE_COUNT):
    """Only this explicitly selected successor can authorize current product bytes."""
    require(expected_digest == SUCCESSOR_SOURCE_DIGEST and type(expected_count) is int and expected_count == SUCCESSOR_SOURCE_COUNT, "caller cannot replace successor source authority")
    return _validate_source_manifest(manifest, SUCCESSOR_SOURCE_DIGEST, SUCCESSOR_SOURCE_COUNT)


def validate_successor_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {SUCCESSOR_SOURCE_BASE + "selection.json", SUCCESSOR_SOURCE_BASE + "selected-source-manifest.json"}, "successor source selection membership mismatch")
    body = metadata[SUCCESSOR_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == SUCCESSOR_SELECTION_SHA256, "successor source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[SUCCESSOR_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "successor source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_successor_source_manifest(selected)
    require(selected == SUCCESSOR_MANIFEST and value["predecessor"] == {"source_count": CURRENT_SOURCE_COUNT, "source_digest_sha256": CURRENT_SOURCE_DIGEST, "selection_sha256": CURRENT_SELECTION_SHA256}, "successor source predecessor mismatch")
    delta = {path: {"before": CURRENT_MANIFEST.get(path), "after": row} for path, row in selected.items() if CURRENT_MANIFEST.get(path) != row}
    require(set(CURRENT_MANIFEST) <= set(selected) and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "successor source delta mismatch")
    return value


def check_successor_source(root):
    """Pure source preflight: no Git, subprocess, container or network activity."""
    metadata = {SUCCESSOR_SOURCE_BASE + name: (root / SUCCESSOR_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_successor_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in SUCCESSOR_MANIFEST}
    validate_successor_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": SUCCESSOR_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def validate_private_source_manifest(manifest, expected_digest=PRIVATE_SOURCE_DIGEST, expected_count=PRIVATE_SOURCE_COUNT):
    """Only this explicitly selected private can authorize current product bytes."""
    require(expected_digest == PRIVATE_SOURCE_DIGEST and type(expected_count) is int and expected_count == PRIVATE_SOURCE_COUNT, "caller cannot replace private source authority")
    return _validate_source_manifest(manifest, PRIVATE_SOURCE_DIGEST, PRIVATE_SOURCE_COUNT)


def validate_private_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {PRIVATE_SOURCE_BASE + "selection.json", PRIVATE_SOURCE_BASE + "selected-source-manifest.json"}, "private source selection membership mismatch")
    body = metadata[PRIVATE_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == PRIVATE_SELECTION_SHA256, "private source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[PRIVATE_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "private source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_private_source_manifest(selected)
    require(selected == PRIVATE_MANIFEST and value["predecessor"] == {"source_count": SUCCESSOR_SOURCE_COUNT, "source_digest_sha256": SUCCESSOR_SOURCE_DIGEST, "selection_sha256": SUCCESSOR_SELECTION_SHA256}, "private source predecessor mismatch")
    delta = {path: {"before": SUCCESSOR_MANIFEST.get(path), "after": row} for path, row in selected.items() if SUCCESSOR_MANIFEST.get(path) != row}
    require(set(SUCCESSOR_MANIFEST) <= set(selected) and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "private source delta mismatch")
    return value


def check_private_source(root):
    """Pure source preflight: no Git, subprocess, container or network activity."""
    metadata = {PRIVATE_SOURCE_BASE + name: (root / PRIVATE_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_private_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in PRIVATE_MANIFEST}
    validate_private_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": PRIVATE_SELECTION_SHA256, "runtime_or_GA_accepted": False}



def validate_browser_source_manifest(manifest, expected_digest=BROWSER_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == BROWSER_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == BROWSER_SOURCE_COUNT),
            "caller cannot replace browser source authority")
    return _validate_source_manifest(manifest, BROWSER_SOURCE_DIGEST, BROWSER_SOURCE_COUNT)


def validate_browser_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {BROWSER_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "browser source selection membership mismatch")
    body = metadata[BROWSER_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == BROWSER_SELECTION_SHA256, "browser source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[BROWSER_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "browser source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_browser_source_manifest(selected)
    require(selected == BROWSER_MANIFEST and value["selected"]["source_count"] == BROWSER_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == BROWSER_SOURCE_DIGEST, "browser source count or digest mismatch")
    require(value["predecessor"] == {"source_count": PRIVATE_SOURCE_COUNT, "source_digest_sha256": PRIVATE_SOURCE_DIGEST, "selection_sha256": PRIVATE_SELECTION_SHA256}, "browser source predecessor mismatch")
    delta = {path: {"before": PRIVATE_MANIFEST.get(path), "after": row} for path, row in selected.items() if PRIVATE_MANIFEST.get(path) != row}
    require(set(PRIVATE_MANIFEST) <= set(selected) and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "browser source delta mismatch")
    return value


def check_browser_source(root):
    metadata = {BROWSER_SOURCE_BASE + name: (root / BROWSER_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_browser_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in BROWSER_MANIFEST}
    validate_browser_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": BROWSER_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_browser_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / BROWSER_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == BROWSER_SELECTION_SHA256, "browser source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / BROWSER_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "browser source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == BROWSER_SOURCE_DIGEST, "browser source authority shape")
    manifest = json.loads(manifest_body)
    _validate_source_manifest(manifest, BROWSER_SOURCE_DIGEST, count)
    return count, manifest


def validate_operation_source_manifest(manifest, expected_digest=OPERATION_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == OPERATION_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == OPERATION_SOURCE_COUNT),
            "caller cannot replace operation source authority")
    return _validate_source_manifest(manifest, OPERATION_SOURCE_DIGEST, OPERATION_SOURCE_COUNT)


def validate_operation_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {OPERATION_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "operation source selection membership mismatch")
    body = metadata[OPERATION_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == OPERATION_SELECTION_SHA256, "operation source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[OPERATION_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "operation source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_operation_source_manifest(selected)
    require(selected == OPERATION_MANIFEST and value["selected"]["source_count"] == OPERATION_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == OPERATION_SOURCE_DIGEST, "operation source count or digest mismatch")
    require(value["predecessor"] == {"source_count": BROWSER_SOURCE_COUNT, "source_digest_sha256": BROWSER_SOURCE_DIGEST, "selection_sha256": BROWSER_SELECTION_SHA256}, "operation source predecessor mismatch")
    delta = {path: {"before": BROWSER_MANIFEST.get(path), "after": row} for path, row in selected.items() if BROWSER_MANIFEST.get(path) != row}
    require(set(BROWSER_MANIFEST) <= set(selected) and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "operation source delta mismatch")
    return value


def check_operation_source(root):
    metadata = {OPERATION_SOURCE_BASE + name: (root / OPERATION_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_operation_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in OPERATION_MANIFEST}
    validate_operation_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": OPERATION_SELECTION_SHA256, "runtime_or_GA_accepted": False}


@dataclasses.dataclass(frozen=True)
class CurrentSourceAuthority:
    count: int
    digest: str
    manifest: dict


def _load_operation_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / OPERATION_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == OPERATION_SELECTION_SHA256, "operation source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / OPERATION_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "operation source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == OPERATION_SOURCE_DIGEST, "operation source authority shape")
    manifest = json.loads(manifest_body)
    _validate_source_manifest(manifest, OPERATION_SOURCE_DIGEST, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "operation typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)


def validate_lifetime_source_manifest(manifest, expected_digest=LIFETIME_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == LIFETIME_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == LIFETIME_SOURCE_COUNT),
            "caller cannot replace lifetime source authority")
    return _validate_source_manifest(manifest, LIFETIME_SOURCE_DIGEST, LIFETIME_SOURCE_COUNT)


def validate_lifetime_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {LIFETIME_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "lifetime source selection membership mismatch")
    body = metadata[LIFETIME_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == LIFETIME_SELECTION_SHA256, "lifetime source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[LIFETIME_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "lifetime source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_lifetime_source_manifest(selected)
    require(selected == LIFETIME_MANIFEST and value["selected"]["source_count"] == LIFETIME_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == LIFETIME_SOURCE_DIGEST, "lifetime source count or digest mismatch")
    require(value["predecessor"] == {"source_count": OPERATION_SOURCE_COUNT, "source_digest_sha256": OPERATION_SOURCE_DIGEST, "selection_sha256": OPERATION_SELECTION_SHA256}, "lifetime source predecessor mismatch")
    delta = {path: {"before": OPERATION_MANIFEST.get(path), "after": row} for path, row in selected.items() if OPERATION_MANIFEST.get(path) != row}
    require(set(OPERATION_MANIFEST) <= set(selected) and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "lifetime source delta mismatch")
    return value


def check_lifetime_source(root):
    metadata = {LIFETIME_SOURCE_BASE + name: (root / LIFETIME_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_lifetime_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in LIFETIME_MANIFEST}
    validate_lifetime_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": LIFETIME_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_lifetime_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / LIFETIME_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == LIFETIME_SELECTION_SHA256, "lifetime source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / LIFETIME_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "lifetime source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == LIFETIME_SOURCE_DIGEST, "lifetime source authority shape")
    manifest = json.loads(manifest_body)
    _validate_source_manifest(manifest, LIFETIME_SOURCE_DIGEST, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "lifetime typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)


def validate_commit_source_manifest(manifest, expected_digest=COMMIT_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == COMMIT_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == COMMIT_SOURCE_COUNT),
            "caller cannot replace commit source authority")
    return _validate_source_manifest(manifest, COMMIT_SOURCE_DIGEST, COMMIT_SOURCE_COUNT)


def validate_commit_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {COMMIT_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "commit source selection membership mismatch")
    body = metadata[COMMIT_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == COMMIT_SELECTION_SHA256, "commit source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[COMMIT_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "commit source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_commit_source_manifest(selected)
    require(selected == COMMIT_MANIFEST and value["selected"]["source_count"] == COMMIT_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == COMMIT_SOURCE_DIGEST, "commit source count or digest mismatch")
    require(value["predecessor"] == {"source_count": LIFETIME_SOURCE_COUNT, "source_digest_sha256": LIFETIME_SOURCE_DIGEST, "selection_sha256": LIFETIME_SELECTION_SHA256}, "commit source predecessor mismatch")
    delta = {path: {"before": LIFETIME_MANIFEST.get(path), "after": row} for path, row in selected.items() if LIFETIME_MANIFEST.get(path) != row}
    require(set(LIFETIME_MANIFEST) <= set(selected) and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "commit source delta mismatch")
    return value


def check_commit_source(root):
    metadata = {COMMIT_SOURCE_BASE + name: (root / COMMIT_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_commit_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in COMMIT_MANIFEST}
    validate_commit_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": COMMIT_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_commit_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / COMMIT_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == COMMIT_SELECTION_SHA256, "commit source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / COMMIT_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "commit source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == COMMIT_SOURCE_DIGEST, "commit source authority shape")
    manifest = json.loads(manifest_body)
    _validate_source_manifest(manifest, COMMIT_SOURCE_DIGEST, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "commit typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)


def validate_proxy_source_manifest(manifest, expected_digest=PROXY_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == PROXY_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == PROXY_SOURCE_COUNT),
            "caller cannot replace proxy source authority")
    return _validate_source_manifest(manifest, PROXY_SOURCE_DIGEST, PROXY_SOURCE_COUNT)


def validate_proxy_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {PROXY_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "proxy source selection membership mismatch")
    body = metadata[PROXY_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == PROXY_SELECTION_SHA256, "proxy source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[PROXY_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "proxy source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_proxy_source_manifest(selected)
    require(selected == PROXY_MANIFEST and value["selected"]["source_count"] == PROXY_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == PROXY_SOURCE_DIGEST, "proxy source count or digest mismatch")
    require(value["predecessor"] == {"source_count": COMMIT_SOURCE_COUNT, "source_digest_sha256": COMMIT_SOURCE_DIGEST, "selection_sha256": COMMIT_SELECTION_SHA256}, "proxy source predecessor mismatch")
    delta = {path: {"before": COMMIT_MANIFEST.get(path), "after": row} for path, row in selected.items() if COMMIT_MANIFEST.get(path) != row}
    require(set(COMMIT_MANIFEST) <= set(selected) and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "proxy source delta mismatch")
    return value


def check_proxy_source(root):
    metadata = {PROXY_SOURCE_BASE + name: (root / PROXY_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_proxy_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in PROXY_MANIFEST}
    validate_proxy_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": PROXY_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_proxy_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / PROXY_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == PROXY_SELECTION_SHA256, "proxy source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / PROXY_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "proxy source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == PROXY_SOURCE_DIGEST, "proxy source authority shape")
    manifest = json.loads(manifest_body)
    _validate_source_manifest(manifest, PROXY_SOURCE_DIGEST, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "proxy typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)


def validate_customer_build_source_manifest(manifest, expected_digest=BUILD_READ_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == BUILD_READ_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == BUILD_READ_SOURCE_COUNT),
            "caller cannot replace customer build source authority")
    return _validate_source_manifest(manifest, BUILD_READ_SOURCE_DIGEST, BUILD_READ_SOURCE_COUNT)


def validate_customer_build_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {BUILD_READ_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "customer build source selection membership mismatch")
    body = metadata[BUILD_READ_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == BUILD_READ_SELECTION_SHA256, "customer build source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[BUILD_READ_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "customer build source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_customer_build_source_manifest(selected)
    require(selected == BUILD_READ_MANIFEST and value["selected"]["source_count"] == BUILD_READ_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == BUILD_READ_SOURCE_DIGEST, "customer build source count or digest mismatch")
    require(value["predecessor"] == {"source_count": PROXY_SOURCE_COUNT, "source_digest_sha256": PROXY_SOURCE_DIGEST, "selection_sha256": PROXY_SELECTION_SHA256}, "customer build source predecessor mismatch")
    delta = {path: {"before": PROXY_MANIFEST.get(path), "after": row} for path, row in selected.items() if PROXY_MANIFEST.get(path) != row}
    require(set(PROXY_MANIFEST) <= set(selected) and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "customer build source delta mismatch")
    inverse = dict(selected)
    for path, change in delta.items():
        if change["before"] is None: inverse.pop(path)
        else: inverse[path] = change["before"]
    require(inverse == PROXY_MANIFEST and canonical_digest(inverse) == PROXY_SOURCE_DIGEST, "customer build predecessor inverse mismatch")
    return value


def check_customer_build_source(root):
    metadata = {BUILD_READ_SOURCE_BASE + name: (root / BUILD_READ_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_customer_build_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in BUILD_READ_MANIFEST}
    validate_customer_build_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": BUILD_READ_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_customer_build_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / BUILD_READ_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == BUILD_READ_SELECTION_SHA256, "customer build source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / BUILD_READ_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "customer build source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == BUILD_READ_SOURCE_DIGEST, "customer build source authority shape")
    manifest = json.loads(manifest_body)
    _validate_source_manifest(manifest, BUILD_READ_SOURCE_DIGEST, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "customer build typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)



def _validate_browser_build_source_manifest(manifest, count):
    require(type(count) is int and count == 243, "browser build closed source count")
    require(isinstance(manifest, dict) and len(manifest) == count, "source path count mismatch")
    console_inputs = ["console/package.json","console/src/api/browser-session-client.ts","console/src/api/cookie-build-client.ts","console/src/api/cookie-workspace-client.ts","console/src/api/workspace-client.ts","console/src/api/workspace-transport.ts","console/src/domain/build-overview.ts","console/src/domain/build-read.ts","console/src/domain/workspace-directory.ts","console/tests/cookie-build-client.test.mjs","console/tsconfig.json"]
    for path, row in manifest.items():
        p = PurePosixPath(path)
        require((path.startswith("hosted/") or path in console_inputs) and not p.is_absolute() and ".." not in p.parts and str(p) == path, "unsafe source path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"}, "source row shape")
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES, "source byte bound")
        require(bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "source hash shape")
    require(manifest["hosted/mix.lock"]["sha256"] == FROZEN_LOCK_SHA256, "frozen lock mismatch")
    require(canonical_digest(manifest) == BROWSER_BUILD_SOURCE_DIGEST, "frozen product digest mismatch")
    return manifest


def validate_browser_build_source_manifest(manifest, expected_digest=BROWSER_BUILD_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == BROWSER_BUILD_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == BROWSER_BUILD_SOURCE_COUNT),
            "caller cannot replace browser build source authority")
    return _validate_browser_build_source_manifest(manifest, BROWSER_BUILD_SOURCE_COUNT)

def validate_browser_build_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {BROWSER_BUILD_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "browser build source selection membership mismatch")
    body = metadata[BROWSER_BUILD_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == BROWSER_BUILD_SELECTION_SHA256, "browser build source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[BROWSER_BUILD_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "browser build source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_browser_build_source_manifest(selected)
    require(selected == BROWSER_BUILD_MANIFEST and value["selected"]["source_count"] == BROWSER_BUILD_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == BROWSER_BUILD_SOURCE_DIGEST, "browser build source count or digest mismatch")
    require(value["predecessor"] == {"source_count": BUILD_READ_SOURCE_COUNT, "source_digest_sha256": BUILD_READ_SOURCE_DIGEST, "selection_sha256": BUILD_READ_SELECTION_SHA256}, "browser build source predecessor mismatch")
    delta = {path: {"before": BUILD_READ_MANIFEST.get(path), "after": row} for path, row in selected.items() if BUILD_READ_MANIFEST.get(path) != row}
    require(set(BUILD_READ_MANIFEST) <= set(selected) and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "browser build source delta mismatch")
    inverse = dict(selected)
    for path, change in delta.items():
        if change["before"] is None: inverse.pop(path)
        else: inverse[path] = change["before"]
    require(inverse == BUILD_READ_MANIFEST and canonical_digest(inverse) == BUILD_READ_SOURCE_DIGEST, "browser build predecessor inverse mismatch")
    return value


def check_browser_build_source(root):
    metadata = {BROWSER_BUILD_SOURCE_BASE + name: (root / BROWSER_BUILD_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_browser_build_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in BROWSER_BUILD_MANIFEST}
    validate_browser_build_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": BROWSER_BUILD_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_browser_build_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / BROWSER_BUILD_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == BROWSER_BUILD_SELECTION_SHA256, "browser build source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / BROWSER_BUILD_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "browser build source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == BROWSER_BUILD_SOURCE_DIGEST, "browser build source authority shape")
    manifest = json.loads(manifest_body)
    _validate_browser_build_source_manifest(manifest, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "browser build typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)


def _validate_owned_evidence_source_manifest(manifest, count):
    require(type(count) is int and count == 243, "owned evidence closed source count")
    require(isinstance(manifest, dict) and len(manifest) == count, "source path count mismatch")
    console_inputs = ["console/package.json","console/src/api/browser-session-client.ts","console/src/api/cookie-build-client.ts","console/src/api/cookie-workspace-client.ts","console/src/api/workspace-client.ts","console/src/api/workspace-transport.ts","console/src/domain/build-overview.ts","console/src/domain/build-read.ts","console/src/domain/workspace-directory.ts","console/tests/cookie-build-client.test.mjs","console/tsconfig.json"]
    for path, row in manifest.items():
        p = PurePosixPath(path)
        require((path.startswith("hosted/") or path in console_inputs) and not p.is_absolute() and ".." not in p.parts and str(p) == path, "unsafe source path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"}, "source row shape")
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES, "source byte bound")
        require(bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "source hash shape")
    require(manifest["hosted/mix.lock"]["sha256"] == FROZEN_LOCK_SHA256, "frozen lock mismatch")
    require(canonical_digest(manifest) == OWNED_EVIDENCE_SOURCE_DIGEST, "frozen product digest mismatch")
    return manifest


def validate_owned_evidence_source_manifest(manifest, expected_digest=OWNED_EVIDENCE_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == OWNED_EVIDENCE_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == OWNED_EVIDENCE_SOURCE_COUNT),
            "caller cannot replace owned evidence source authority")
    return _validate_owned_evidence_source_manifest(manifest, OWNED_EVIDENCE_SOURCE_COUNT)

def validate_owned_evidence_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {OWNED_EVIDENCE_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "owned evidence source selection membership mismatch")
    body = metadata[OWNED_EVIDENCE_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == OWNED_EVIDENCE_SELECTION_SHA256, "owned evidence source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[OWNED_EVIDENCE_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "owned evidence source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_owned_evidence_source_manifest(selected)
    require(selected == OWNED_EVIDENCE_MANIFEST and value["selected"]["source_count"] == OWNED_EVIDENCE_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == OWNED_EVIDENCE_SOURCE_DIGEST, "owned evidence source count or digest mismatch")
    require(value["predecessor"] == {"source_count": BROWSER_BUILD_SOURCE_COUNT, "source_digest_sha256": BROWSER_BUILD_SOURCE_DIGEST, "selection_sha256": BROWSER_BUILD_SELECTION_SHA256}, "owned evidence source predecessor mismatch")
    delta = {path: {"before": BROWSER_BUILD_MANIFEST.get(path), "after": row} for path, row in selected.items() if BROWSER_BUILD_MANIFEST.get(path) != row}
    require(set(selected) == set(BROWSER_BUILD_MANIFEST) and set(delta) == {"hosted/scripts/test-local.py"} and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "owned evidence source delta mismatch")
    inverse = dict(selected)
    for path, change in delta.items():
        if change["before"] is None: inverse.pop(path)
        else: inverse[path] = change["before"]
    require(inverse == BROWSER_BUILD_MANIFEST and canonical_digest(inverse) == BROWSER_BUILD_SOURCE_DIGEST, "owned evidence predecessor inverse mismatch")
    return value


def check_owned_evidence_source(root):
    metadata = {OWNED_EVIDENCE_SOURCE_BASE + name: (root / OWNED_EVIDENCE_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_owned_evidence_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in OWNED_EVIDENCE_MANIFEST}
    validate_owned_evidence_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": OWNED_EVIDENCE_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_owned_evidence_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / OWNED_EVIDENCE_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == OWNED_EVIDENCE_SELECTION_SHA256, "owned evidence source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / OWNED_EVIDENCE_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "owned evidence source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == OWNED_EVIDENCE_SOURCE_DIGEST, "owned evidence source authority shape")
    manifest = json.loads(manifest_body)
    _validate_owned_evidence_source_manifest(manifest, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "owned evidence typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)


def _validate_hosted_compiler_source_manifest(manifest, count):
    require(type(count) is int and count == 247, "hosted compiler closed source count")
    require(isinstance(manifest, dict) and len(manifest) == count, "source path count mismatch")
    console_inputs = ["console/package.json","console/src/api/browser-session-client.ts","console/src/api/cookie-build-client.ts","console/src/api/cookie-workspace-client.ts","console/src/api/workspace-client.ts","console/src/api/workspace-transport.ts","console/src/domain/build-overview.ts","console/src/domain/build-read.ts","console/src/domain/workspace-directory.ts","console/tests/cookie-build-client.test.mjs","console/tsconfig.json"]
    for path, row in manifest.items():
        p = PurePosixPath(path)
        require((path.startswith("hosted/") or path in console_inputs or path in HOSTED_COMPILER_INPUTS) and not p.is_absolute() and ".." not in p.parts and str(p) == path, "unsafe source path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"}, "source row shape")
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES, "source byte bound")
        require(bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "source hash shape")
    require(manifest["hosted/mix.lock"]["sha256"] == FROZEN_LOCK_SHA256, "frozen lock mismatch")
    require(canonical_digest(manifest) == HOSTED_COMPILER_SOURCE_DIGEST, "frozen product digest mismatch")
    return manifest


def validate_hosted_compiler_source_manifest(manifest, expected_digest=HOSTED_COMPILER_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == HOSTED_COMPILER_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == HOSTED_COMPILER_SOURCE_COUNT),
            "caller cannot replace hosted compiler source authority")
    return _validate_hosted_compiler_source_manifest(manifest, HOSTED_COMPILER_SOURCE_COUNT)

def validate_hosted_compiler_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {HOSTED_COMPILER_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "hosted compiler source selection membership mismatch")
    body = metadata[HOSTED_COMPILER_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == HOSTED_COMPILER_SELECTION_SHA256, "hosted compiler source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[HOSTED_COMPILER_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "hosted compiler source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_hosted_compiler_source_manifest(selected)
    require(selected == HOSTED_COMPILER_MANIFEST and value["selected"]["source_count"] == HOSTED_COMPILER_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == HOSTED_COMPILER_SOURCE_DIGEST, "hosted compiler source count or digest mismatch")
    require(value["predecessor"] == {"source_count": OWNED_EVIDENCE_SOURCE_COUNT, "source_digest_sha256": OWNED_EVIDENCE_SOURCE_DIGEST, "selection_sha256": OWNED_EVIDENCE_SELECTION_SHA256}, "hosted compiler source predecessor mismatch")
    delta = {path: {"before": OWNED_EVIDENCE_MANIFEST.get(path), "after": row} for path, row in selected.items() if OWNED_EVIDENCE_MANIFEST.get(path) != row}
    require(set(selected) == set(OWNED_EVIDENCE_MANIFEST) | set(HOSTED_COMPILER_INPUTS) and set(delta) == set(HOSTED_COMPILER_INPUTS) and all(change["before"] is None for change in delta.values()) and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "hosted compiler source delta mismatch")
    inverse = dict(selected)
    for path, change in delta.items():
        if change["before"] is None: inverse.pop(path)
        else: inverse[path] = change["before"]
    require(inverse == OWNED_EVIDENCE_MANIFEST and canonical_digest(inverse) == OWNED_EVIDENCE_SOURCE_DIGEST, "hosted compiler predecessor inverse mismatch")
    return value


def check_hosted_compiler_source(root):
    metadata = {HOSTED_COMPILER_SOURCE_BASE + name: (root / HOSTED_COMPILER_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_hosted_compiler_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in HOSTED_COMPILER_MANIFEST}
    validate_hosted_compiler_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": HOSTED_COMPILER_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_hosted_compiler_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / HOSTED_COMPILER_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == HOSTED_COMPILER_SELECTION_SHA256, "hosted compiler source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / HOSTED_COMPILER_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "hosted compiler source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == HOSTED_COMPILER_SOURCE_DIGEST, "hosted compiler source authority shape")
    manifest = json.loads(manifest_body)
    _validate_hosted_compiler_source_manifest(manifest, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "hosted compiler typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)




PROVIDER_HTTPS_SOURCE_BASE = 'verification/identity-network-current-source-v14/'
PROVIDER_HTTPS_SELECTION_SHA256 = 'd6349039303b6b158bba734d897edd7ee2ae943b9e8d8b0b98204923175447e0'
PROVIDER_HTTPS_SOURCE_DIGEST = '4049b96febf9cce493d6d91fef62b19206db2f2f58d776cddaed67d6267955fc'
PROVIDER_HTTPS_INPUTS = CATALOG_JOIN_INPUTS
PROVIDER_HTTPS_DELTA = {'hosted/lib/mixer_hosted/browser_auth/provider_https_wire.ex': {'before': None, 'after': {'bytes': 5300, 'sha256': 'fdb98c826aa587017154d9540630f590aebd87c7ced0e085ddf7c6e2cce3c69f'}}, 'hosted/lib/mixer_hosted/browser_auth/provider_https.ex': {'before': None, 'after': {'bytes': 11316, 'sha256': '57a03f842737b8c9b8950b8de3230e28b0ad5c649dceec2dd0188c3426dca532'}}, 'hosted/test/support/browser_provider_tls_fixture.ex': {'before': None, 'after': {'bytes': 11381, 'sha256': '42dba3aedf40a5967b0848109e5701476aaba80ae36fa49e4f24c587b3da8b2b'}}, 'hosted/test/mixer_hosted/browser_auth/provider_https_exchange_test.exs': {'before': None, 'after': {'bytes': 11660, 'sha256': 'de8cd26ad7ef50f39546a54555c952834058d9c67444ed2b47839d430ed2ee48'}}}

def _validate_provider_https_source_manifest(manifest, count):
    require(type(count) is int and count == 263, "provider HTTPS closed source count")
    require(isinstance(manifest, dict) and len(manifest) == count, "source path count mismatch")
    console_inputs = ["console/package.json","console/src/api/browser-session-client.ts","console/src/api/cookie-build-client.ts","console/src/api/cookie-workspace-client.ts","console/src/api/workspace-client.ts","console/src/api/workspace-transport.ts","console/src/domain/build-overview.ts","console/src/domain/build-read.ts","console/src/domain/workspace-directory.ts","console/tests/cookie-build-client.test.mjs","console/tsconfig.json"]
    for path, row in manifest.items():
        p = PurePosixPath(path)
        require((path.startswith("hosted/") or path in console_inputs or path in PROVIDER_HTTPS_INPUTS) and not p.is_absolute() and ".." not in p.parts and str(p) == path, "unsafe source path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"}, "source row shape")
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES, "source byte bound")
        require(bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "source hash shape")
    require(manifest["hosted/mix.lock"]["sha256"] == FROZEN_LOCK_SHA256, "frozen lock mismatch")
    require(canonical_digest(manifest) == PROVIDER_HTTPS_SOURCE_DIGEST, "frozen product digest mismatch")
    return manifest


def validate_provider_https_source_manifest(manifest, expected_digest=PROVIDER_HTTPS_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == PROVIDER_HTTPS_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == PROVIDER_HTTPS_SOURCE_COUNT),
            "caller cannot replace provider HTTPS source authority")
    return _validate_provider_https_source_manifest(manifest, PROVIDER_HTTPS_SOURCE_COUNT)

def validate_provider_https_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {PROVIDER_HTTPS_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "provider HTTPS source selection membership mismatch")
    body = metadata[PROVIDER_HTTPS_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == PROVIDER_HTTPS_SELECTION_SHA256, "provider HTTPS source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[PROVIDER_HTTPS_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "provider HTTPS source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_provider_https_source_manifest(selected)
    require(selected == PROVIDER_HTTPS_MANIFEST and value["selected"]["source_count"] == PROVIDER_HTTPS_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == PROVIDER_HTTPS_SOURCE_DIGEST, "provider HTTPS source count or digest mismatch")
    require(value["predecessor"] == {"source_count": CATALOG_JOIN_SOURCE_COUNT, "source_digest_sha256": CATALOG_JOIN_SOURCE_DIGEST, "selection_sha256": CATALOG_JOIN_SELECTION_SHA256}, "provider HTTPS source predecessor mismatch")
    delta = {path: {"before": CATALOG_JOIN_MANIFEST.get(path), "after": row} for path, row in selected.items() if CATALOG_JOIN_MANIFEST.get(path) != row}
    require(set(selected) == set(CATALOG_JOIN_MANIFEST) | {path for path, change in PROVIDER_HTTPS_DELTA.items() if change["before"] is None} and delta == PROVIDER_HTTPS_DELTA and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "provider HTTPS source delta mismatch")
    inverse = dict(selected)
    for path, change in delta.items():
        if change["before"] is None: inverse.pop(path)
        else: inverse[path] = change["before"]
    require(inverse == CATALOG_JOIN_MANIFEST and canonical_digest(inverse) == CATALOG_JOIN_SOURCE_DIGEST, "provider HTTPS predecessor inverse mismatch")
    return value


def check_provider_https_source(root):
    metadata = {PROVIDER_HTTPS_SOURCE_BASE + name: (root / PROVIDER_HTTPS_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_provider_https_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in PROVIDER_HTTPS_MANIFEST}
    validate_provider_https_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": PROVIDER_HTTPS_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_provider_https_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / PROVIDER_HTTPS_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == PROVIDER_HTTPS_SELECTION_SHA256, "provider HTTPS source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / PROVIDER_HTTPS_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "provider HTTPS source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == PROVIDER_HTTPS_SOURCE_DIGEST, "provider HTTPS source authority shape")
    manifest = json.loads(manifest_body)
    _validate_provider_https_source_manifest(manifest, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "provider HTTPS typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)

ORDINARY_BROWSER_SOURCE_BASE = 'verification/identity-network-current-source-v15/'
ORDINARY_BROWSER_SELECTION_SHA256 = "79ae1d49352d6bc02da85f004c5855089ba9eaa3fe7b8d408f4bb7e99358cb8b"
ORDINARY_BROWSER_SOURCE_DIGEST = "7541ccd6dc3369acac10dbfa881914eaf76e0c092a7ceaba142fc26ce00c169e"
ORDINARY_BROWSER_INPUTS = PROVIDER_HTTPS_INPUTS
ORDINARY_BROWSER_DELTA = {"hosted/config/runtime.exs":{"before":{"bytes":549,"sha256":"73cd8edac21bb64c3fba3cd81bb461f2cee651b9f799bd42bfac3e5ffeca6e9f"},"after":{"bytes":695,"sha256":"386315724c984b7a66daa66c5f95bbaa6fdbeacd36296167695b33a5c9933367"}},"hosted/lib/mixer_hosted/application.ex":{"before":{"bytes":1278,"sha256":"bbf02752b982e1437564c266772cd4e5dd7190670a575dd6676dda7fc692803f"},"after":{"bytes":3777,"sha256":"12832d9bd53cceabb657fb115b7ef6678a7cbd0d836ab2e505c50d252a0ba39b"}},"hosted/lib/mixer_hosted/browser_auth/installation.ex":{"before":None,"after":{"bytes":3159,"sha256":"9f8a7c2341d533b596a9be645d9cbeea28d0f78929b9678ea4908ee3d99b1858"}},"hosted/lib/mixer_hosted/browser_auth/store.ex":{"before":{"bytes":24830,"sha256":"a310b0a8ec8fb28fe78f8d69b3758399d88d096a7bd2a97fefbaaca091c188bb"},"after":{"bytes":24845,"sha256":"d265b30252f322fc02da88e2a6e88ced7a19947d77d891ee32655e9387706425"}},"hosted/lib/mixer_hosted/browser_auth/supervisor.ex":{"before":None,"after":{"bytes":1361,"sha256":"41f0dacb08c8212d69b0ca8f63e47c387b121ff6b327579a08d26b2e2b5ade2c"}},"hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex":{"before":{"bytes":1072,"sha256":"cdb7b901a8e521361e1578bf0b47ea521a31c61c681c27d1f164925081238ba2"},"after":{"bytes":1110,"sha256":"aafb1be8c32215a0c34e6ae52a3bbc90e449f3976f95179804e016250bce0eaf"}},"hosted/lib/mixer_hosted_web/browser_http.ex":{"before":{"bytes":7099,"sha256":"4065474f1c12c364dd71f73cfdd1855a29bea2d94f5e32b2346141bd2ea622b7"},"after":{"bytes":6763,"sha256":"929f9affec444dfa23fbe57ec9a5d96a380be759595ba63097253ea62327df02"}},"hosted/lib/mixer_hosted_web/browser_login_http.ex":{"before":{"bytes":4161,"sha256":"1dd605f112835aecdad1f43d6ebd5315beb7b35403cd0aff4d1ad17ba75ae839"},"after":{"bytes":4724,"sha256":"ef1f3408474b9e8c1581253f5cfc4371b2edc1315072bf6677f1d6e6f009facb"}},"hosted/lib/mixer_hosted_web/endpoint.ex":{"before":{"bytes":160,"sha256":"7702c86f462af84fb6ac157d700d1a22352f2eaf117e31565f672dd533313d08"},"after":{"bytes":211,"sha256":"45867999c57d3c9fcaeb79a164640b1755c5c878552f3e5ace0aacf5d870bd48"}},"hosted/test/foundation_integration_test.exs":{"before":{"bytes":6296,"sha256":"852de2acd4dbf623925d5fb7eddc14856e4cd0dc0ed09ca87703e6b1f2294a1b"},"after":{"bytes":6438,"sha256":"b65e549c79bef9028e8cea42741d1a160436f2710a6fc433b9a649c1ab447757"}},"hosted/test/mixer_hosted/browser_auth/initial_admit_queue_test.exs":{"before":None,"after":{"bytes":3835,"sha256":"90aebf785ae06bb4af4a8adacdf87c410d673373a0e49678e610d3fec09c3f43"}},"hosted/test/mixer_hosted/browser_auth/ordinary_console_catalog_navigation_cookie_pg_join_test.exs":{"before":None,"after":{"bytes":16228,"sha256":"4d851130a5ab5bd87da3855ed7b8ac4c38d30fb3bcf8128e81a9f0a085951110"}},"hosted/test/mixer_hosted/browser_auth/private_login_http_test.exs":{"before":{"bytes":61834,"sha256":"97889c149ddc69458b46f2d4e99a64b1ce37f4770e049515349b25d82fdc62f6"},"after":{"bytes":56454,"sha256":"ea8705368c9c5a14d4d6775b76b17546690900a88f53fb71b0d8110c59233ce7"}},"hosted/test/mixer_hosted/browser_auth/run_storage_fixture.py":{"before":{"bytes":8627,"sha256":"bfd5edfa4f4e362e76686fb7de89def23ca79eefe1b1c58f74749f550c9bf92c"},"after":{"bytes":8681,"sha256":"1869f1b7ea80aad44c7fabc970f98e6971c8acfde59851219e4b56827fec9253"}},"hosted/test/mixer_hosted/browser_auth/storage_fixture.exs":{"before":{"bytes":7108,"sha256":"9417342d3d5708d21b216383da8cb4bef381e3572036853e6f099ccf08235a06"},"after":{"bytes":147,"sha256":"d2af04e11201eda3e2caba1635214188c19a9a054967ff4d9f04aba7f7f51c00"}},"hosted/test/mixer_hosted/identity/key_owner_supervisor_fixture_test.exs":{"before":None,"after":{"bytes":4225,"sha256":"f1019c099bafb654c50a74962a3ce90875864cbf52a3fdb2eee79c35075b6adf"}},"hosted/test/mixer_hosted/identity/startup_config_test.exs":{"before":{"bytes":8279,"sha256":"bb9fc59f47c2c4bb15c42608ff52cd3dbe88ed71e73957bda3c4775b96214c3a"},"after":{"bytes":8297,"sha256":"31f2ba324282f06746aba3f47e1b89bfeb2a6fe3f8a878f90df33c9d30f12ea2"}},"hosted/test/mixer_hosted/identity/startup_lifecycle_test.exs":{"before":{"bytes":6531,"sha256":"e88301c119b04528879b0b52e896c73075cd2a390bc17ef9b20a2ddf68430ba2"},"after":{"bytes":6907,"sha256":"15b40da21797e6e019b1e2f433babf45fb1270e2c0da9da5469b21734371c667"}},"hosted/test/runtime_config_test.exs":{"before":{"bytes":3661,"sha256":"bf12eaec3ac8da5b7aec297c16bd3d3e89f62182c3fd00980b60a7c04e3a6daf"},"after":{"bytes":3659,"sha256":"818accb074ee8bdf0492a9495075f7d4c9e4adaeab74a2dd174370b406f6388f"}},"hosted/test/support/browser_login_provider_fixture.ex":{"before":None,"after":{"bytes":5379,"sha256":"2b0107bc357277f080d39ad01b5e6c7fda65d29fcd7fb5ba5a4afe662eb1e9c9"}},"hosted/test/support/browser_storage_fixture.ex":{"before":None,"after":{"bytes":7105,"sha256":"6e44facb19caf863eab5800ffe27d6c5e82816ada26af3c979a5ebf63e9abe0b"}},"hosted/test/support/identity_startup_fixture.ex":{"before":{"bytes":4539,"sha256":"075f77531b83d43567c214777ee458cb630f15e62fbd1f009c46100ccacdd761"},"after":{"bytes":4782,"sha256":"b28d98290cc83605325b81a74986515a5a5544f4393f479b9974cea7e69b84b2"}},"hosted/test/support/initial_admit_queue_fixture.ex":{"before":None,"after":{"bytes":9184,"sha256":"fd9098bd9b3fcc71a46bc60e723875c651968f0b010468da61297d468dd30eb4"}},"hosted/test/support/ordinary_browser_startup_fixture.ex":{"before":None,"after":{"bytes":25298,"sha256":"486fbf75691a8f3e8168442c7727324817c14c8560f0b796b805a0221a5e19a5"}}}

def _validate_ordinary_browser_source_manifest(manifest, count):
    require(type(count) is int and count == 272, "ordinary browser closed source count")
    require(isinstance(manifest, dict) and len(manifest) == count, "source path count mismatch")
    console_inputs = ["console/package.json","console/src/api/browser-session-client.ts","console/src/api/cookie-build-client.ts","console/src/api/cookie-workspace-client.ts","console/src/api/workspace-client.ts","console/src/api/workspace-transport.ts","console/src/domain/build-overview.ts","console/src/domain/build-read.ts","console/src/domain/workspace-directory.ts","console/tests/cookie-build-client.test.mjs","console/tsconfig.json"]
    for path, row in manifest.items():
        p = PurePosixPath(path)
        require((path.startswith("hosted/") or path in console_inputs or path in ORDINARY_BROWSER_INPUTS) and not p.is_absolute() and ".." not in p.parts and str(p) == path, "unsafe source path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"}, "source row shape")
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES, "source byte bound")
        require(bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "source hash shape")
    require(manifest["hosted/mix.lock"]["sha256"] == FROZEN_LOCK_SHA256, "frozen lock mismatch")
    require(canonical_digest(manifest) == ORDINARY_BROWSER_SOURCE_DIGEST, "frozen product digest mismatch")
    return manifest


def validate_ordinary_browser_source_manifest(manifest, expected_digest=ORDINARY_BROWSER_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == ORDINARY_BROWSER_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == ORDINARY_BROWSER_SOURCE_COUNT),
            "caller cannot replace ordinary browser source authority")
    return _validate_ordinary_browser_source_manifest(manifest, ORDINARY_BROWSER_SOURCE_COUNT)

def validate_ordinary_browser_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {ORDINARY_BROWSER_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "ordinary browser source selection membership mismatch")
    body = metadata[ORDINARY_BROWSER_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == ORDINARY_BROWSER_SELECTION_SHA256, "ordinary browser source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[ORDINARY_BROWSER_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "ordinary browser source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_ordinary_browser_source_manifest(selected)
    require(selected == ORDINARY_BROWSER_MANIFEST and value["selected"]["source_count"] == ORDINARY_BROWSER_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == ORDINARY_BROWSER_SOURCE_DIGEST, "ordinary browser source count or digest mismatch")
    require(value["predecessor"] == {"source_count": PROVIDER_HTTPS_SOURCE_COUNT, "source_digest_sha256": PROVIDER_HTTPS_SOURCE_DIGEST, "selection_sha256": PROVIDER_HTTPS_SELECTION_SHA256}, "ordinary browser source predecessor mismatch")
    delta = {path: {"before": PROVIDER_HTTPS_MANIFEST.get(path), "after": row} for path, row in selected.items() if PROVIDER_HTTPS_MANIFEST.get(path) != row}
    require(set(selected) == set(PROVIDER_HTTPS_MANIFEST) | {path for path, change in ORDINARY_BROWSER_DELTA.items() if change["before"] is None} and delta == ORDINARY_BROWSER_DELTA and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "ordinary browser source delta mismatch")
    inverse = dict(selected)
    for path, change in delta.items():
        if change["before"] is None: inverse.pop(path)
        else: inverse[path] = change["before"]
    require(inverse == PROVIDER_HTTPS_MANIFEST and canonical_digest(inverse) == PROVIDER_HTTPS_SOURCE_DIGEST, "ordinary browser predecessor inverse mismatch")
    return value


def check_ordinary_browser_source(root):
    metadata = {ORDINARY_BROWSER_SOURCE_BASE + name: (root / ORDINARY_BROWSER_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_ordinary_browser_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in ORDINARY_BROWSER_MANIFEST}
    validate_ordinary_browser_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": ORDINARY_BROWSER_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_ordinary_browser_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / ORDINARY_BROWSER_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == ORDINARY_BROWSER_SELECTION_SHA256, "ordinary browser source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / ORDINARY_BROWSER_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "ordinary browser source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == ORDINARY_BROWSER_SOURCE_DIGEST, "ordinary browser source authority shape")
    manifest = json.loads(manifest_body)
    _validate_ordinary_browser_source_manifest(manifest, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "ordinary browser typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)


def _validate_catalog_join_source_manifest(manifest, count):
    require(type(count) is int and count == 259, "catalog join closed source count")
    require(isinstance(manifest, dict) and len(manifest) == count, "source path count mismatch")
    console_inputs = ["console/package.json","console/src/api/browser-session-client.ts","console/src/api/cookie-build-client.ts","console/src/api/cookie-workspace-client.ts","console/src/api/workspace-client.ts","console/src/api/workspace-transport.ts","console/src/domain/build-overview.ts","console/src/domain/build-read.ts","console/src/domain/workspace-directory.ts","console/tests/cookie-build-client.test.mjs","console/tsconfig.json"]
    for path, row in manifest.items():
        p = PurePosixPath(path)
        require((path.startswith("hosted/") or path in console_inputs or path in CATALOG_JOIN_INPUTS) and not p.is_absolute() and ".." not in p.parts and str(p) == path, "unsafe source path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"}, "source row shape")
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES, "source byte bound")
        require(bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "source hash shape")
    require(manifest["hosted/mix.lock"]["sha256"] == FROZEN_LOCK_SHA256, "frozen lock mismatch")
    require(canonical_digest(manifest) == CATALOG_JOIN_SOURCE_DIGEST, "frozen product digest mismatch")
    return manifest


def validate_catalog_join_source_manifest(manifest, expected_digest=CATALOG_JOIN_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == CATALOG_JOIN_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == CATALOG_JOIN_SOURCE_COUNT),
            "caller cannot replace catalog join source authority")
    return _validate_catalog_join_source_manifest(manifest, CATALOG_JOIN_SOURCE_COUNT)

def validate_catalog_join_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {CATALOG_JOIN_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "catalog join source selection membership mismatch")
    body = metadata[CATALOG_JOIN_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == CATALOG_JOIN_SELECTION_SHA256, "catalog join source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[CATALOG_JOIN_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "catalog join source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_catalog_join_source_manifest(selected)
    require(selected == CATALOG_JOIN_MANIFEST and value["selected"]["source_count"] == CATALOG_JOIN_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == CATALOG_JOIN_SOURCE_DIGEST, "catalog join source count or digest mismatch")
    require(value["predecessor"] == {"source_count": HOSTED_COMPILER_SOURCE_COUNT, "source_digest_sha256": HOSTED_COMPILER_SOURCE_DIGEST, "selection_sha256": HOSTED_COMPILER_SELECTION_SHA256}, "catalog join source predecessor mismatch")
    delta = {path: {"before": HOSTED_COMPILER_MANIFEST.get(path), "after": row} for path, row in selected.items() if HOSTED_COMPILER_MANIFEST.get(path) != row}
    require(set(selected) == set(HOSTED_COMPILER_MANIFEST) | {path for path, change in CATALOG_JOIN_DELTA.items() if change["before"] is None} and delta == CATALOG_JOIN_DELTA and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "catalog join source delta mismatch")
    inverse = dict(selected)
    for path, change in delta.items():
        if change["before"] is None: inverse.pop(path)
        else: inverse[path] = change["before"]
    require(inverse == HOSTED_COMPILER_MANIFEST and canonical_digest(inverse) == HOSTED_COMPILER_SOURCE_DIGEST, "catalog join predecessor inverse mismatch")
    return value


def check_catalog_join_source(root):
    metadata = {CATALOG_JOIN_SOURCE_BASE + name: (root / CATALOG_JOIN_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_catalog_join_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in CATALOG_JOIN_MANIFEST}
    validate_catalog_join_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": CATALOG_JOIN_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_catalog_join_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / CATALOG_JOIN_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == CATALOG_JOIN_SELECTION_SHA256, "catalog join source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / CATALOG_JOIN_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "catalog join source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == CATALOG_JOIN_SOURCE_DIGEST, "catalog join source authority shape")
    manifest = json.loads(manifest_body)
    _validate_catalog_join_source_manifest(manifest, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "catalog join typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)


def validate_fixture_manifest(body):
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == FIXTURE_PACKET_SHA256, "fixture amendment packet bytes mismatch")
    packet = json.loads(body)
    require(isinstance(packet, dict) and set(packet) == {"schema", "files", "tree_digest_sha256"} and type(packet["schema"]) is int and packet["schema"] == 1, "fixture amendment packet shape")
    files = packet["files"]
    require(isinstance(files, dict) and len(files) == 18 and packet["tree_digest_sha256"] == FIXTURE_PACKET and canonical_digest(files) == FIXTURE_PACKET, "fixture amendment packet seal mismatch")
    for path, row in files.items():
        name = PurePosixPath(path)
        require(not name.is_absolute() and ".." not in name.parts and str(name) == path and "\\" not in path and path != "packet-manifest.json", "unsafe fixture metadata path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"} and type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES and isinstance(row["sha256"], str) and bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "fixture amendment row shape")
    return files


def literal_helper_rows(manifest=None):
    helpers = {"collector-prerequisites.exs": PREREQUISITES_EXS.encode(), "collector-bootstrap.exs": BOOTSTRAP_EXS.encode(), "collector-manifest.exs": MANIFEST_EXS.encode(), "collector-netns.exs": NETNS_EXS.encode(), "collector-observer.exs": OBSERVER_EXS.encode(), "collector-mounts.exs": MOUNTS_EXS.encode(), "frozen-manifest.json": json.dumps(FROZEN_MANIFEST if manifest is None else manifest, sort_keys=True, separators=(",", ":")).encode()}
    return {path: _file_row(body) for path, body in helpers.items()}


def validate_fixture_metadata(metadata):
    """Preserve historical 177-source contracts; admit exactly the reviewed 178."""
    require(isinstance(metadata, dict) and FIXTURE_BASE + "packet-manifest.json" in metadata, "missing fixture amendment seal")
    files = validate_fixture_manifest(metadata[FIXTURE_BASE + "packet-manifest.json"])
    require({path for path in metadata if path.startswith(FIXTURE_BASE)} == {FIXTURE_BASE + "packet-manifest.json"} | {FIXTURE_BASE + path for path in files}, "missing or extra fixture amendment metadata")
    validate_execution_metadata({path: body for path, body in metadata.items() if not path.startswith(FIXTURE_BASE)})
    for path, expected in files.items():
        require(isinstance(metadata[FIXTURE_BASE + path], bytes) and _file_row(metadata[FIXTURE_BASE + path]) == expected, "fixture amendment metadata hash mismatch")
    body = metadata[FIXTURE_BASE + "source-amendment.json"]
    require(hashlib.sha256(body).hexdigest() == FIXTURE_SHA256, "selected fixture amendment drift")
    value = json.loads(body)
    require(set(value) == {"schema", "operation", "predecessor", "selected", "exact_delta", "independent_review", "integration_patch", "preserved", "literal_helpers", "ordinary_phoenix_controls", "remote_execution_only", "runtime_or_GA_accepted"} and type(value["schema"]) is int and value["schema"] == 1 and value["operation"] == "replace-exact-test-fixture-and-add-executable-regression-test", "fixture amendment shape")
    require(value["predecessor"] == {"product_commit": PRODUCT_COMMIT, "source_count": 177, "source_digest_sha256": FROZEN_PRODUCT_DIGEST, "contract_sha256": CONTRACT_SHA256, "image_amendment_sha256": AMENDMENT_SHA256, "execution_amendment_sha256": EXECUTION_SHA256}, "fixture amendment predecessor mismatch")
    predecessor = json.loads(metadata[FIXTURE_BASE + "predecessor-source-manifest.json"])
    selected_body = metadata[FIXTURE_BASE + "selected-source-manifest.json"]
    selected = json.loads(selected_body)
    _validate_source_manifest(predecessor, FROZEN_PRODUCT_DIGEST, 177)
    _validate_source_manifest(selected, FIXTURE_SOURCE_DIGEST, 178)
    require(predecessor == PREDECESSOR_MANIFEST and selected == FIXTURE_MANIFEST, "fixture source manifest binding mismatch")
    require(value["selected"] == {"source_count": 178, "source_digest_sha256": FIXTURE_SOURCE_DIGEST, "manifest": {"path": "selected-source-manifest.json", **_file_row(selected_body)}}, "fixture selected source mismatch")
    fixture = "hosted/test/support/identity_tls_fixture.ex"
    control = "hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs"
    delta = {fixture: {"operation": "replace", "before": predecessor[fixture], "after": selected[fixture]}, control: {"operation": "add", "before": None, "after": selected[control]}}
    require(value["exact_delta"] == delta and set(selected) == set(predecessor) | {control} and {path for path in predecessor if predecessor[path] != selected[path]} == {fixture}, "fixture amendment is not the exact two-row delta")
    review_base = FIXTURE_BASE + "independent-review/"
    review_body = metadata[review_base + "packet-manifest.json"]
    require(value["independent_review"] == {"namespace": "independent-review/", "packet_manifest_sha256": FIXTURE_REVIEW_SHA256, "packet_tree_digest_sha256": FIXTURE_REVIEW_PACKET} and hashlib.sha256(review_body).hexdigest() == FIXTURE_REVIEW_SHA256, "fixture independent review pin mismatch")
    review_packet = json.loads(review_body)
    require(review_packet["tree_digest_sha256"] == FIXTURE_REVIEW_PACKET and canonical_digest(review_packet["files"]) == FIXTURE_REVIEW_PACKET, "fixture independent review seal mismatch")
    require({path.removeprefix(review_base) for path in metadata if path.startswith(review_base)} == set(review_packet["files"]) | {"packet-manifest.json"}, "fixture independent review membership mismatch")
    for path, expected in review_packet["files"].items():
        require(_file_row(metadata[review_base + path]) == expected, "fixture independent review member mismatch")
    review = json.loads(metadata[review_base + "review.json"])
    candidate = review["selected_candidate"]
    require(review["status"] == "source-qualified-accept-for-root-promotion-runtime-unrun" and review["source_blockers"] == [] and candidate["source_count"] == 178 and candidate["source_digest_sha256"] == FIXTURE_SOURCE_DIGEST and candidate["fixture"] == {"path": fixture, **selected[fixture]} and candidate["control"] == {"path": control, **selected[control]}, "fixture review does not accept exact selected source")
    require(value["integration_patch"] == {"path": "integration-candidate.patch", **_file_row(metadata[FIXTURE_BASE + "integration-candidate.patch"])} and value["integration_patch"]["sha256"] == candidate["integration_patch_sha256"], "fixture integration patch mismatch")
    tests = {"hosted/" + path: selected["hosted/" + path] for path in TEST_ROOTS}
    preserved = {"lock_sha256": FROZEN_LOCK_SHA256, "original_test_files": tests, "test_roots": TEST_ROOTS, "expected_methods": EXPECTED_METHODS, "runtime": "all selected image/execution/namespace/resource/bootstrap/custody contracts unchanged"}
    require(canonical_digest(value["preserved"]) == canonical_digest(preserved) and all(predecessor[path] == row for path, row in tests.items()), "fixture amendment changed original method contracts")
    require(value["literal_helpers"] == literal_helper_rows(FIXTURE_MANIFEST), "fixture selected literal helper mismatch")
    require(value["remote_execution_only"] is True and value["runtime_or_GA_accepted"] is False and len(value["ordinary_phoenix_controls"]) == 4, "fixture execution boundary mismatch")
    return value


def validate_format_manifest(body):
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == FORMAT_PACKET_SHA256, "format amendment packet bytes mismatch")
    packet = json.loads(body)
    require(isinstance(packet, dict) and set(packet) == {"schema", "files", "tree_digest_sha256"} and type(packet["schema"]) is int and packet["schema"] == 1, "format amendment packet shape")
    files = packet["files"]
    require(isinstance(files, dict) and len(files) == 7 and packet["tree_digest_sha256"] == FORMAT_PACKET and canonical_digest(files) == FORMAT_PACKET, "format amendment packet seal mismatch")
    for path, row in files.items():
        name = PurePosixPath(path)
        require(not name.is_absolute() and ".." not in name.parts and str(name) == path and "\\" not in path and path != "packet-manifest.json", "unsafe format metadata path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"} and type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES and isinstance(row["sha256"], str) and bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "format amendment row shape")
    return files


def validate_format_metadata(metadata):
    """Bind the exact CI whitespace correction after the immutable semantic review."""
    require(isinstance(metadata, dict) and FORMAT_BASE + "packet-manifest.json" in metadata, "missing format amendment seal")
    files = validate_format_manifest(metadata[FORMAT_BASE + "packet-manifest.json"])
    require({path for path in metadata if path.startswith(FORMAT_BASE)} == {FORMAT_BASE + "packet-manifest.json"} | {FORMAT_BASE + path for path in files}, "missing or extra format amendment metadata")
    accepted = validate_fixture_metadata({path: body for path, body in metadata.items() if not path.startswith(FORMAT_BASE)})
    for path, expected in files.items():
        require(isinstance(metadata[FORMAT_BASE + path], bytes) and _file_row(metadata[FORMAT_BASE + path]) == expected, "format amendment metadata hash mismatch")
    body = metadata[FORMAT_BASE + "source-amendment.json"]
    require(hashlib.sha256(body).hexdigest() == FORMAT_SHA256, "selected format amendment drift")
    value = json.loads(body)
    require(set(value) == {"schema", "operation", "predecessor", "selected", "exact_delta", "format_proof", "integration_patch", "accepted_semantic_review", "preserved", "literal_helpers", "ordinary_phoenix_controls", "binding_scope", "remote_execution_only", "runtime_or_GA_accepted"} and type(value["schema"]) is int and value["schema"] == 1 and value["operation"] == "exact-ci-format-only-source-amendment", "format amendment shape")
    require(value["predecessor"] == {"source_count": 178, "source_digest_sha256": FIXTURE_SOURCE_DIGEST, "amendment_sha256": FIXTURE_SHA256, "packet_manifest_sha256": FIXTURE_PACKET_SHA256, "packet_tree_digest_sha256": FIXTURE_PACKET}, "format predecessor mismatch")
    predecessor = json.loads(metadata[FORMAT_BASE + "predecessor-source-manifest.json"])
    selected_body = metadata[FORMAT_BASE + "selected-source-manifest.json"]
    selected = json.loads(selected_body)
    _validate_source_manifest(predecessor, FIXTURE_SOURCE_DIGEST, 178)
    validate_source_manifest(selected)
    require(predecessor == FIXTURE_MANIFEST and selected == FROZEN_MANIFEST, "format source binding mismatch")
    require(value["selected"] == {"source_count": 178, "source_digest_sha256": SELECTED_SOURCE_DIGEST, "manifest": {"path": "selected-source-manifest.json", **_file_row(selected_body)}}, "format selected source mismatch")
    control = "hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs"
    require(set(selected) == set(predecessor) and {path for path in predecessor if predecessor[path] != selected[path]} == {control}, "format changed additional sources")
    require(value["exact_delta"] == {control: {"operation": "replace", "before": predecessor[control], "after": selected[control]}}, "format delta mismatch")
    before, after = metadata[FORMAT_BASE + "before.exs"], metadata[FORMAT_BASE + "after.exs"]
    proof = json.loads(metadata[FORMAT_BASE + "format-proof.json"])
    old = b'    authority = GenServer.call(fixture, :authority)\n    assert {:ok, socket} = :gen_tcp.connect(authority.ip, authority.port, [:binary, active: false])\n\n    try do\n'
    new = b'    authority = GenServer.call(fixture, :authority)\n\n    assert {:ok, socket} =\n             :gen_tcp.connect(authority.ip, authority.port, [:binary, active: false])\n\n    try do\n'
    require(_file_row(before) == predecessor[control] and _file_row(after) == selected[control] and before.count(old) == 1 and before.replace(old, new) == after, "not exact CI formatter replacement")
    require(b"".join(before.split()) == b"".join(after.split()) and proof["exact_old_block"] == old.decode() and proof["exact_new_block"] == new.decode() and proof["ascii_whitespace_stripped_sha256"] == hashlib.sha256(b"".join(before.split())).hexdigest(), "format changed tokens")
    require(value["format_proof"] == {"path": "format-proof.json", **_file_row(metadata[FORMAT_BASE + "format-proof.json"])} and value["integration_patch"] == {"path": "exact-format.patch", **_file_row(metadata[FORMAT_BASE + "exact-format.patch"])}, "format proof binding mismatch")
    require(value["accepted_semantic_review"] == accepted["independent_review"] and value["preserved"] == accepted["preserved"] and value["ordinary_phoenix_controls"] == accepted["ordinary_phoenix_controls"], "format changed accepted contracts")
    require(value["literal_helpers"] == literal_helper_rows() and value["binding_scope"] == ["delivered-git-blobs", "frozen-manifest-helper", "source-archive", "prepared-source", "restored-source", "compiled-source", "post-test-source"], "format helper or source comparisons drift")
    require(value["remote_execution_only"] is True and value["runtime_or_GA_accepted"] is False, "format execution boundary mismatch")
    return value


SUPERVISED_PROVIDER_SOURCE_BASE = 'verification/identity-network-current-source-v16/'
SUPERVISED_PROVIDER_SELECTION_SHA256 = 'f3d0ae94268cc7887c2bfa712c9f86c06438be6fb9fb41ffa8b5a28ad5305371'
SUPERVISED_PROVIDER_SOURCE_DIGEST = '758ae1c973ec4b58ea0158b5566d6ac81cb1cad6a54762d3e5a23a2ff99896a8'
SUPERVISED_PROVIDER_INPUTS = ORDINARY_BROWSER_INPUTS
SUPERVISED_PROVIDER_DELTA = {'hosted/lib/mixer_hosted/browser_auth/provider_owner.ex': {'before': {'bytes': 3240, 'sha256': '8eb447eee9906b2a0eda58ed2fc5469afbbaa8f3c7495317e474dd6c7eb15331'}, 'after': {'bytes': 13603, 'sha256': 'f4d130a1242820c5419870e5446bb4283d771bb2ba23bc760b1f6870096fd779'}}, 'hosted/lib/mixer_hosted/browser_auth/provider_trust_config.ex': {'before': None, 'after': {'bytes': 3920, 'sha256': '4472a0e554969da8e1c146850685030936dad2397a75028f80f439cf68a766a4'}}, 'hosted/test/mixer_hosted/browser_auth/provider_trust_config_test.exs': {'before': None, 'after': {'bytes': 9245, 'sha256': '5836408664c07b13fab32709457dee075850fafeac1aac17f92002018d682b65'}}, 'hosted/test/mixer_hosted/browser_auth/provider_owner_lifecycle_test.exs': {'before': None, 'after': {'bytes': 41707, 'sha256': '8a631d8c62e3d161034327fa93d24d64f0e1e4747306c91d9cb6e796e5f67786'}}}

def _validate_supervised_provider_source_manifest(manifest, count):
    require(type(count) is int and count == 275, "supervised provider closed source count")
    require(isinstance(manifest, dict) and len(manifest) == count, "source path count mismatch")
    console_inputs = ["console/package.json","console/src/api/browser-session-client.ts","console/src/api/cookie-build-client.ts","console/src/api/cookie-workspace-client.ts","console/src/api/workspace-client.ts","console/src/api/workspace-transport.ts","console/src/domain/build-overview.ts","console/src/domain/build-read.ts","console/src/domain/workspace-directory.ts","console/tests/cookie-build-client.test.mjs","console/tsconfig.json"]
    for path, row in manifest.items():
        p = PurePosixPath(path)
        require((path.startswith("hosted/") or path in console_inputs or path in SUPERVISED_PROVIDER_INPUTS) and not p.is_absolute() and ".." not in p.parts and str(p) == path, "unsafe source path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"}, "source row shape")
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES, "source byte bound")
        require(bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "source hash shape")
    require(manifest["hosted/mix.lock"]["sha256"] == FROZEN_LOCK_SHA256, "frozen lock mismatch")
    require(canonical_digest(manifest) == SUPERVISED_PROVIDER_SOURCE_DIGEST, "frozen product digest mismatch")
    return manifest


def validate_supervised_provider_source_manifest(manifest, expected_digest=SUPERVISED_PROVIDER_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == SUPERVISED_PROVIDER_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == SUPERVISED_PROVIDER_SOURCE_COUNT),
            "caller cannot replace supervised provider source authority")
    return _validate_supervised_provider_source_manifest(manifest, SUPERVISED_PROVIDER_SOURCE_COUNT)

def validate_supervised_provider_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {SUPERVISED_PROVIDER_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "supervised provider source selection membership mismatch")
    body = metadata[SUPERVISED_PROVIDER_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == SUPERVISED_PROVIDER_SELECTION_SHA256, "supervised provider source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[SUPERVISED_PROVIDER_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "supervised provider source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_supervised_provider_source_manifest(selected)
    require(selected == SUPERVISED_PROVIDER_MANIFEST and value["selected"]["source_count"] == SUPERVISED_PROVIDER_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == SUPERVISED_PROVIDER_SOURCE_DIGEST, "supervised provider source count or digest mismatch")
    require(value["predecessor"] == {"source_count": ORDINARY_BROWSER_SOURCE_COUNT, "source_digest_sha256": ORDINARY_BROWSER_SOURCE_DIGEST, "selection_sha256": ORDINARY_BROWSER_SELECTION_SHA256}, "supervised provider source predecessor mismatch")
    delta = {path: {"before": ORDINARY_BROWSER_MANIFEST.get(path), "after": row} for path, row in selected.items() if ORDINARY_BROWSER_MANIFEST.get(path) != row}
    require(set(selected) == set(ORDINARY_BROWSER_MANIFEST) | {path for path, change in SUPERVISED_PROVIDER_DELTA.items() if change["before"] is None} and delta == SUPERVISED_PROVIDER_DELTA and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "supervised provider source delta mismatch")
    inverse = dict(selected)
    for path, change in delta.items():
        if change["before"] is None: inverse.pop(path)
        else: inverse[path] = change["before"]
    require(inverse == ORDINARY_BROWSER_MANIFEST and canonical_digest(inverse) == ORDINARY_BROWSER_SOURCE_DIGEST, "supervised provider predecessor inverse mismatch")
    return value


def check_supervised_provider_source(root):
    metadata = {SUPERVISED_PROVIDER_SOURCE_BASE + name: (root / SUPERVISED_PROVIDER_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_supervised_provider_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in SUPERVISED_PROVIDER_MANIFEST}
    validate_supervised_provider_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": SUPERVISED_PROVIDER_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_supervised_provider_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / SUPERVISED_PROVIDER_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == SUPERVISED_PROVIDER_SELECTION_SHA256, "supervised provider source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / SUPERVISED_PROVIDER_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "supervised provider source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == SUPERVISED_PROVIDER_SOURCE_DIGEST, "supervised provider source authority shape")
    manifest = json.loads(manifest_body)
    _validate_supervised_provider_source_manifest(manifest, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "supervised provider typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)


PROVIDER_IO_SOURCE_BASE = 'verification/identity-network-current-source-v17/'
PROVIDER_IO_SELECTION_SHA256 = '4b3ad5d2b3ef7f5843dd9a996eb02a179f0e80b052a28dd400769750b30f3460'
PROVIDER_IO_SOURCE_DIGEST = '6021237e9cdf0dcc0cdf25ef841e754c93591723045031d06fa7a572e5d34661'
PROVIDER_IO_INPUTS = SUPERVISED_PROVIDER_INPUTS
PROVIDER_IO_DELTA = {'hosted/lib/mixer_hosted/browser_auth/provider_https.ex': {'before': {'bytes': 11316, 'sha256': '57a03f842737b8c9b8950b8de3230e28b0ad5c649dceec2dd0188c3426dca532'}, 'after': {'bytes': 16230, 'sha256': '02fb29c723d7394148a170a40dd39db86f15d007d0777b9f31f938a6032c79c4'}}, 'hosted/lib/mixer_hosted/browser_auth/provider_owner.ex': {'before': {'bytes': 13603, 'sha256': 'f4d130a1242820c5419870e5446bb4283d771bb2ba23bc760b1f6870096fd779'}, 'after': {'bytes': 16519, 'sha256': 'c9aa46dfee58f17368f4089d10b27e1b1eb592ecb1df245ece445dca95313192'}}, 'hosted/lib/mixer_hosted/browser_auth/startup_secrets.ex': {'before': None, 'after': {'bytes': 4256, 'sha256': '2dd8d96d21eb270d986cd55070c0a5135923eca9176e957d48799cd875500990'}}, 'hosted/test/mixer_hosted/browser_auth/startup_secrets_test.exs': {'before': None, 'after': {'bytes': 10282, 'sha256': '3dc94a3b5366d2d15c3dd555b2313e90c2b124f65147c1f362b96b8080e8bbae'}}}

def _validate_provider_io_source_manifest(manifest, count):
    require(type(count) is int and count == 277, "provider IO closed source count")
    require(isinstance(manifest, dict) and len(manifest) == count, "source path count mismatch")
    console_inputs = ["console/package.json","console/src/api/browser-session-client.ts","console/src/api/cookie-build-client.ts","console/src/api/cookie-workspace-client.ts","console/src/api/workspace-client.ts","console/src/api/workspace-transport.ts","console/src/domain/build-overview.ts","console/src/domain/build-read.ts","console/src/domain/workspace-directory.ts","console/tests/cookie-build-client.test.mjs","console/tsconfig.json"]
    for path, row in manifest.items():
        p = PurePosixPath(path)
        require((path.startswith("hosted/") or path in console_inputs or path in PROVIDER_IO_INPUTS) and not p.is_absolute() and ".." not in p.parts and str(p) == path, "unsafe source path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"}, "source row shape")
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES, "source byte bound")
        require(bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "source hash shape")
    require(manifest["hosted/mix.lock"]["sha256"] == FROZEN_LOCK_SHA256, "frozen lock mismatch")
    require(canonical_digest(manifest) == PROVIDER_IO_SOURCE_DIGEST, "frozen product digest mismatch")
    return manifest


def validate_provider_io_source_manifest(manifest, expected_digest=PROVIDER_IO_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == PROVIDER_IO_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == PROVIDER_IO_SOURCE_COUNT),
            "caller cannot replace provider IO source authority")
    return _validate_provider_io_source_manifest(manifest, PROVIDER_IO_SOURCE_COUNT)

def validate_provider_io_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {PROVIDER_IO_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "provider IO source selection membership mismatch")
    body = metadata[PROVIDER_IO_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == PROVIDER_IO_SELECTION_SHA256, "provider IO source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[PROVIDER_IO_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "provider IO source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_provider_io_source_manifest(selected)
    require(selected == PROVIDER_IO_MANIFEST and value["selected"]["source_count"] == PROVIDER_IO_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == PROVIDER_IO_SOURCE_DIGEST, "provider IO source count or digest mismatch")
    require(value["predecessor"] == {"source_count": SUPERVISED_PROVIDER_SOURCE_COUNT, "source_digest_sha256": SUPERVISED_PROVIDER_SOURCE_DIGEST, "selection_sha256": SUPERVISED_PROVIDER_SELECTION_SHA256}, "provider IO source predecessor mismatch")
    delta = {path: {"before": SUPERVISED_PROVIDER_MANIFEST.get(path), "after": row} for path, row in selected.items() if SUPERVISED_PROVIDER_MANIFEST.get(path) != row}
    require(set(selected) == set(SUPERVISED_PROVIDER_MANIFEST) | {path for path, change in PROVIDER_IO_DELTA.items() if change["before"] is None} and delta == PROVIDER_IO_DELTA and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "provider IO source delta mismatch")
    inverse = dict(selected)
    for path, change in delta.items():
        if change["before"] is None: inverse.pop(path)
        else: inverse[path] = change["before"]
    require(inverse == SUPERVISED_PROVIDER_MANIFEST and canonical_digest(inverse) == SUPERVISED_PROVIDER_SOURCE_DIGEST, "provider IO predecessor inverse mismatch")
    return value


def check_provider_io_source(root):
    metadata = {PROVIDER_IO_SOURCE_BASE + name: (root / PROVIDER_IO_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_provider_io_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in PROVIDER_IO_MANIFEST}
    validate_provider_io_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": PROVIDER_IO_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_provider_io_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / PROVIDER_IO_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == PROVIDER_IO_SELECTION_SHA256, "provider IO source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / PROVIDER_IO_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "provider IO source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == PROVIDER_IO_SOURCE_DIGEST, "provider IO source authority shape")
    manifest = json.loads(manifest_body)
    _validate_provider_io_source_manifest(manifest, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "provider IO typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)


CONFIGURED_STARTUP_SOURCE_BASE = 'verification/identity-network-current-source-v18/'
CONFIGURED_STARTUP_SELECTION_SHA256 = '7af785eb990044eb7528cb8e5cca2db9baff8fc6fde06aa981775e7d8ec49470'
CONFIGURED_STARTUP_SOURCE_DIGEST = '776dd25ade6103b33dada33cca0d84a312470d7119c376026f2699212edd490f'
CONFIGURED_STARTUP_INPUTS = PROVIDER_IO_INPUTS
CONFIGURED_STARTUP_DELTA = {'hosted/lib/mixer_hosted/browser_auth/installation.ex': {'before': {'bytes': 3159, 'sha256': '9f8a7c2341d533b596a9be645d9cbeea28d0f78929b9678ea4908ee3d99b1858'}, 'after': {'bytes': 5628, 'sha256': 'c9148d2e7547b6ee7eb3cae9851ebfabfb061f855fafcb364b143ec51b699e7e'}}, 'hosted/lib/mixer_hosted/browser_auth/supervisor.ex': {'before': {'bytes': 1361, 'sha256': '41f0dacb08c8212d69b0ca8f63e47c387b121ff6b327579a08d26b2e2b5ade2c'}, 'after': {'bytes': 2315, 'sha256': '0be221930726bdc9b266de3ea4b703ebb4a74617dcd2b9fe51a806127c16fe50'}}, 'hosted/scripts/check-configured-startup.exs': {'before': None, 'after': {'bytes': 17061, 'sha256': 'ebe446f3e18f72a32719a340802d42adb18c6bcc58df0148331fba87815a84a0'}}, 'hosted/test/mixer_hosted/browser_auth/ordinary_console_catalog_navigation_cookie_pg_join_test.exs': {'before': {'bytes': 16228, 'sha256': '4d851130a5ab5bd87da3855ed7b8ac4c38d30fb3bcf8128e81a9f0a085951110'}, 'after': {'bytes': 16203, 'sha256': 'c90b4209b38f8948cf783669ea005274eb3f43c94f5a6fb35ae5cd2be108de49'}}, 'hosted/test/mixer_hosted/browser_auth/provider_owner_lifecycle_test.exs': {'before': {'bytes': 41707, 'sha256': '8a631d8c62e3d161034327fa93d24d64f0e1e4747306c91d9cb6e796e5f67786'}, 'after': {'bytes': 41700, 'sha256': '9fa8965190cd67f28a8148acf9f0638372b15a68cd839303617b4f09d74181c0'}}, 'hosted/test/mixer_hosted/browser_auth/provider_trust_config_test.exs': {'before': {'bytes': 9245, 'sha256': '5836408664c07b13fab32709457dee075850fafeac1aac17f92002018d682b65'}, 'after': {'bytes': 9232, 'sha256': '435be7bdba21bab5d0d04404775eb32341f27e71611c77b7375bae8d15da625c'}}}

def _validate_configured_startup_source_manifest(manifest, count):
    require(type(count) is int and count == 278, "configured startup closed source count")
    require(isinstance(manifest, dict) and len(manifest) == count, "source path count mismatch")
    console_inputs = ["console/package.json","console/src/api/browser-session-client.ts","console/src/api/cookie-build-client.ts","console/src/api/cookie-workspace-client.ts","console/src/api/workspace-client.ts","console/src/api/workspace-transport.ts","console/src/domain/build-overview.ts","console/src/domain/build-read.ts","console/src/domain/workspace-directory.ts","console/tests/cookie-build-client.test.mjs","console/tsconfig.json"]
    for path, row in manifest.items():
        p = PurePosixPath(path)
        require((path.startswith("hosted/") or path in console_inputs or path in CONFIGURED_STARTUP_INPUTS) and not p.is_absolute() and ".." not in p.parts and str(p) == path, "unsafe source path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"}, "source row shape")
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES, "source byte bound")
        require(bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "source hash shape")
    require(manifest["hosted/mix.lock"]["sha256"] == FROZEN_LOCK_SHA256, "frozen lock mismatch")
    require(canonical_digest(manifest) == CONFIGURED_STARTUP_SOURCE_DIGEST, "frozen product digest mismatch")
    return manifest


def validate_configured_startup_source_manifest(manifest, expected_digest=CONFIGURED_STARTUP_SOURCE_DIGEST, expected_count=None):
    require(expected_digest == CONFIGURED_STARTUP_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == CONFIGURED_STARTUP_SOURCE_COUNT),
            "caller cannot replace configured startup source authority")
    return _validate_configured_startup_source_manifest(manifest, CONFIGURED_STARTUP_SOURCE_COUNT)

def validate_configured_startup_source_metadata(metadata):
    require(isinstance(metadata, dict) and set(metadata) == {CONFIGURED_STARTUP_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")}, "configured startup source selection membership mismatch")
    body = metadata[CONFIGURED_STARTUP_SOURCE_BASE + "selection.json"]
    require(isinstance(body, bytes) and hashlib.sha256(body).hexdigest() == CONFIGURED_STARTUP_SELECTION_SHA256, "configured startup source selection pin mismatch")
    value = json.loads(body)
    selected_body = metadata[CONFIGURED_STARTUP_SOURCE_BASE + "selected-source-manifest.json"]
    require(isinstance(selected_body, bytes) and _file_row(selected_body) == {key: value["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "configured startup source manifest bytes mismatch")
    selected = json.loads(selected_body)
    validate_configured_startup_source_manifest(selected)
    require(selected == CONFIGURED_STARTUP_MANIFEST and value["selected"]["source_count"] == CONFIGURED_STARTUP_SOURCE_COUNT and value["selected"]["source_digest_sha256"] == CONFIGURED_STARTUP_SOURCE_DIGEST, "configured startup source count or digest mismatch")
    require(value["predecessor"] == {"source_count": PROVIDER_IO_SOURCE_COUNT, "source_digest_sha256": PROVIDER_IO_SOURCE_DIGEST, "selection_sha256": PROVIDER_IO_SELECTION_SHA256}, "configured startup source predecessor mismatch")
    delta = {path: {"before": PROVIDER_IO_MANIFEST.get(path), "after": row} for path, row in selected.items() if PROVIDER_IO_MANIFEST.get(path) != row}
    require(set(selected) == set(PROVIDER_IO_MANIFEST) | {path for path, change in CONFIGURED_STARTUP_DELTA.items() if change["before"] is None} and delta == CONFIGURED_STARTUP_DELTA and value["exact_delta"] == delta and value["runtime_or_GA_accepted"] is False, "configured startup source delta mismatch")
    inverse = dict(selected)
    for path, change in delta.items():
        if change["before"] is None: inverse.pop(path)
        else: inverse[path] = change["before"]
    require(inverse == PROVIDER_IO_MANIFEST and canonical_digest(inverse) == PROVIDER_IO_SOURCE_DIGEST, "configured startup predecessor inverse mismatch")
    return value


def check_configured_startup_source(root):
    metadata = {CONFIGURED_STARTUP_SOURCE_BASE + name: (root / CONFIGURED_STARTUP_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
    selection = validate_configured_startup_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in CONFIGURED_STARTUP_MANIFEST}
    validate_configured_startup_source_manifest(observed)
    return {"identity": selection["identity"], "source_count": len(observed), "source_digest_sha256": canonical_digest(observed), "selection_sha256": CONFIGURED_STARTUP_SELECTION_SHA256, "runtime_or_GA_accepted": False}


def _load_configured_startup_source_authority():
    # The closed count comes from independently pinned metadata, never a caller
    # manifest or a manually maintained CURRENT_SOURCE_COUNT literal.
    root = Path(__file__).resolve().parents[2]
    body = (root / CONFIGURED_STARTUP_SOURCE_BASE / "selection.json").read_bytes()
    require(hashlib.sha256(body).hexdigest() == CONFIGURED_STARTUP_SELECTION_SHA256, "configured startup source selection pin mismatch")
    selection = json.loads(body)
    manifest_body = (root / CONFIGURED_STARTUP_SOURCE_BASE / "selected-source-manifest.json").read_bytes()
    require(_file_row(manifest_body) == {key: selection["selected"]["manifest"][key] for key in ("bytes", "sha256")}, "configured startup source manifest bytes mismatch")
    count = selection["selected"]["source_count"]
    require(type(count) is int and count > 0 and selection["selected"]["source_digest_sha256"] == CONFIGURED_STARTUP_SOURCE_DIGEST, "configured startup source authority shape")
    manifest = json.loads(manifest_body)
    _validate_configured_startup_source_manifest(manifest, count)
    require(type(selection["schema"]) is int and selection["schema"] == 1 and count == len(manifest), "configured startup typed authority membership")
    return CurrentSourceAuthority(count, canonical_digest(manifest), manifest)


PUBLIC_SIGNIN_SOURCE_BASE = 'verification/identity-network-current-source-v19/'
PUBLIC_SIGNIN_SELECTION_SHA256 = '81350b91385040121791f93ba6b44b39d8fe4429e79b891727e9c797624a75a7'
PUBLIC_SIGNIN_SOURCE_DIGEST = 'dd08dae24b94f7f0d9a2075ce427ee6dad895c6e68d4fcae9ad7691e78997867'
PUBLIC_SIGNIN_PARENT_CONTRACT_SHA256 = 'b476fe0db6cae466bf0be3801e7ffc69632d7cd3ea75cbe106eb9047d24fbdfe'
PUBLIC_SIGNIN_PRODUCT_MAP_SHA256 = '5920b6a5705465a786fa6589dedfafeb2e8704786414ed93b708452659e046e7'
PUBLIC_SIGNIN_DELTA = {'hosted/lib/mixer_hosted_web/browser_login_http.ex': {'before': {'bytes': 4724, 'sha256': 'ef1f3408474b9e8c1581253f5cfc4371b2edc1315072bf6677f1d6e6f009facb'}, 'after': {'bytes': 5300, 'sha256': '6255155b291327d0a8268d767477b1b4399bd66b5663e748d5d6b58780e2675f'}}, 'console/src/App.tsx': {'before': None, 'after': {'bytes': 5720, 'sha256': 'e92ef3796bfdf1adf81ae8fc0ed3c12f662e6e724ada3841d7327b84c5fbc4c6'}}, 'console/src/main.tsx': {'before': None, 'after': {'bytes': 667, 'sha256': '25b1c1dc079585dcc8c032e96d17e0c4c65e3ae009c3638125c4e7d5be1b7d58'}}, 'console/src/styles.css': {'before': None, 'after': {'bytes': 10472, 'sha256': 'b9c7c7219c16fdfd52d0329de062102241baae16fe7f861e2dfabf2cbf2acaf2'}}, 'console/src/api/browser-login-client.ts': {'before': None, 'after': {'bytes': 5081, 'sha256': 'cda65a5bc6289047715082163d59bb07a63934342a2076023c7c95c9bed55546'}}, 'console/src/state/sign-in-action.ts': {'before': None, 'after': {'bytes': 1722, 'sha256': 'c52a614cef0fb2893c91e778b022780d91b957febce0b9fec6aaea38aabf7b4f'}}, 'console/src/components/SignIn.tsx': {'before': None, 'after': {'bytes': 2297, 'sha256': 'd8958b4d291c85d65495ed9d65dcde298cbfa77f1d6542911a721e4ec2124aa1'}}, 'console/tests/browser-login.test.mjs': {'before': None, 'after': {'bytes': 7063, 'sha256': '461c2ea40c48ca4d641c5fb9c1602294019a2d1a9ffe9c6fb02a2717adcf2c36'}}, 'hosted/test/mixer_hosted/browser_auth/browser_login_json_http_test.exs': {'before': None, 'after': {'bytes': 4670, 'sha256': '1a9063d05d3f76307a6121fa94af9d490e2263c050ea3eb8543cca196606bb12'}}}


def _public_signin_row(value):
    require(type(value) is dict and set(value) == {'bytes', 'sha256'}, 'public signin row shape')
    require(type(value['bytes']) is int and 0 <= value['bytes'] <= MAX_COMMAND_BYTES, 'public signin byte bound')
    require(type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']) is not None, 'public signin hash shape')


def _validate_public_signin_source_manifest(manifest, count):
    require(type(count) is int and count == 286, 'public signin closed source count')
    require(type(manifest) is dict and len(manifest) == count, 'public signin source count')
    require(set(manifest) == set(CONFIGURED_STARTUP_MANIFEST) | set(PUBLIC_SIGNIN_DELTA), 'public signin source membership')
    for path, value in manifest.items():
        require(type(path) is str and not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts and str(PurePosixPath(path)) == path, 'public signin unsafe path')
        _public_signin_row(value)
    delta = {path: {'before': CONFIGURED_STARTUP_MANIFEST.get(path), 'after': value}
             for path, value in manifest.items() if CONFIGURED_STARTUP_MANIFEST.get(path) != value}
    require(delta == PUBLIC_SIGNIN_DELTA, 'public signin exact delta')
    inverse = dict(manifest)
    for path, change in delta.items():
        if change['before'] is None:
            inverse.pop(path)
        else:
            inverse[path] = change['before']
    require(inverse == CONFIGURED_STARTUP_MANIFEST and canonical_digest(inverse) == CONFIGURED_STARTUP_SOURCE_DIGEST, 'public signin complete v18 inverse')
    require(canonical_digest(manifest) == PUBLIC_SIGNIN_SOURCE_DIGEST, 'public signin frozen source digest')
    return manifest


def validate_public_signin_source_manifest(manifest, expected_digest=PUBLIC_SIGNIN_SOURCE_DIGEST, expected_count=None):
    require(type(expected_digest) is str and expected_digest == PUBLIC_SIGNIN_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == PUBLIC_SIGNIN_SOURCE_COUNT), 'caller cannot replace public signin authority')
    return _validate_public_signin_source_manifest(manifest, PUBLIC_SIGNIN_SOURCE_COUNT)


def _public_signin_metadata(metadata):
    require(type(metadata) is dict and set(metadata) == {PUBLIC_SIGNIN_SOURCE_BASE + name for name in ('selection.json', 'selected-source-manifest.json')}, 'public signin metadata membership')
    body = metadata[PUBLIC_SIGNIN_SOURCE_BASE + 'selection.json']
    require(type(body) is bytes and hashlib.sha256(body).hexdigest() == PUBLIC_SIGNIN_SELECTION_SHA256, 'public signin selection pin mismatch')
    try:
        value = json.loads(body)
    except (ValueError, TypeError) as error:
        raise CollectorError('public signin selection JSON') from error
    require(type(value) is dict and set(value) == {'schema', 'identity', 'operation', 'scope', 'selected', 'predecessor', 'exact_delta', 'runtime_or_GA_accepted', 'parent_contract_sha256', 'product_map_sha256'}, 'public signin selection shape')
    require(type(value['schema']) is int and value['schema'] == 1 and value['identity'] == 'hosted-current-public-console-signin-v19', 'public signin typed schema')
    require(value['runtime_or_GA_accepted'] is False and value['parent_contract_sha256'] == PUBLIC_SIGNIN_PARENT_CONTRACT_SHA256 and value['product_map_sha256'] == PUBLIC_SIGNIN_PRODUCT_MAP_SHA256, 'public signin scope contract')
    predecessor = value['predecessor']
    require(type(predecessor) is dict and set(predecessor) == {'source_count', 'source_digest_sha256', 'selection_sha256'}, 'public signin predecessor shape')
    require(type(predecessor['source_count']) is int and predecessor == {'source_count': CONFIGURED_STARTUP_SOURCE_COUNT, 'source_digest_sha256': CONFIGURED_STARTUP_SOURCE_DIGEST, 'selection_sha256': CONFIGURED_STARTUP_SELECTION_SHA256}, 'public signin typed predecessor')
    selected = value['selected']
    require(type(selected) is dict and set(selected) == {'source_count', 'source_digest_sha256', 'manifest'}, 'public signin selected shape')
    require(type(selected['source_count']) is int and selected['source_count'] == 286 and selected['source_digest_sha256'] == PUBLIC_SIGNIN_SOURCE_DIGEST, 'public signin selected count digest')
    reference = selected['manifest']
    require(type(reference) is dict and set(reference) == {'path', 'bytes', 'sha256'} and reference['path'] == 'selected-source-manifest.json', 'public signin manifest reference')
    _public_signin_row({key: reference[key] for key in ('bytes', 'sha256')})
    manifest_body = metadata[PUBLIC_SIGNIN_SOURCE_BASE + 'selected-source-manifest.json']
    require(type(manifest_body) is bytes and _file_row(manifest_body) == {key: reference[key] for key in ('bytes', 'sha256')}, 'public signin manifest byte pin')
    try:
        manifest = json.loads(manifest_body)
    except (ValueError, TypeError) as error:
        raise CollectorError('public signin manifest JSON') from error
    _validate_public_signin_source_manifest(manifest, selected['source_count'])
    delta = value['exact_delta']
    require(type(delta) is dict and set(delta) == set(PUBLIC_SIGNIN_DELTA), 'public signin delta membership')
    for path, change in delta.items():
        require(type(change) is dict and set(change) == {'before', 'after'}, 'public signin delta row')
        if change['before'] is not None:
            _public_signin_row(change['before'])
        _public_signin_row(change['after'])
    require(delta == PUBLIC_SIGNIN_DELTA, 'public signin typed inverse delta')
    return value, manifest


def validate_public_signin_source_metadata(metadata):
    value, manifest = _public_signin_metadata(metadata)
    require(manifest == PUBLIC_SIGNIN_MANIFEST, 'public signin installed manifest')
    return value


def check_public_signin_source(root):
    metadata = {PUBLIC_SIGNIN_SOURCE_BASE + name: (root / PUBLIC_SIGNIN_SOURCE_BASE / name).read_bytes() for name in ('selection.json', 'selected-source-manifest.json')}
    selection = validate_public_signin_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in PUBLIC_SIGNIN_MANIFEST}
    validate_public_signin_source_manifest(observed)
    return {'identity': selection['identity'], 'source_count': len(observed), 'source_digest_sha256': canonical_digest(observed), 'selection_sha256': PUBLIC_SIGNIN_SELECTION_SHA256, 'runtime_or_GA_accepted': False}


def _load_public_signin_source_authority():
    root = Path(__file__).resolve().parents[2]
    metadata = {PUBLIC_SIGNIN_SOURCE_BASE + name: (root / PUBLIC_SIGNIN_SOURCE_BASE / name).read_bytes() for name in ('selection.json', 'selected-source-manifest.json')}
    value, manifest = _public_signin_metadata(metadata)
    return CurrentSourceAuthority(value['selected']['source_count'], canonical_digest(manifest), manifest)


CONSOLE_COHERENCE_SOURCE_BASE = 'verification/identity-network-current-source-v20/'
CONSOLE_COHERENCE_SELECTION_SHA256 = '86bd7b4d6bc7c8176029f7c8c40ba6204e108187ea70ce08b70bca95ad9a2818'
CONSOLE_COHERENCE_SOURCE_DIGEST = '957e64f869982b0172e452f1f59a990c784984667aac835044d5ed14f4e11fe0'
CONSOLE_COHERENCE_PARENT_CONTRACT_SHA256 = 'aded4f2708f24767502663ae28c16a4997e2fe685103845a522876f2ef9d91c3'
CONSOLE_COHERENCE_PRODUCT_MAP_SHA256 = 'b43fe08f8b6b76159ebca669c589106fd3a7b7add04fedd60b8c6c6ee7186285'
CONSOLE_COHERENCE_DELTA = {'console/src/components/ApplicationBuildPage.tsx': {'before': None, 'after': {'bytes': 11229, 'sha256': '88c1032fc3758da8acdd166c1bef3e9ede2a55d5107749bd29964a87f3a94fce'}}, 'console/src/state/build-selection-controller.ts': {'before': None, 'after': {'bytes': 17475, 'sha256': '034a1811233df08970f5f30a78f9ee70e46f13765fc2f0b0f7f329d0b547e2b3'}}, 'console/tests/application-build-page.test.mjs': {'before': None, 'after': {'bytes': 18004, 'sha256': 'df7babc4e38bf72a085aa3327bee06de3b8cca20867659f511f88680172a0be2'}}, 'console/tests/build-selection-controller.test.mjs': {'before': None, 'after': {'bytes': 24692, 'sha256': 'd534d18a38d69f933287255ed8d22d03bb267f3289a09deb1e4e52ba7502510d'}}}


def _console_coherence_row(value):
    require(type(value) is dict and set(value) == {'bytes', 'sha256'}, 'console coherence row shape')
    require(type(value['bytes']) is int and 0 <= value['bytes'] <= MAX_COMMAND_BYTES, 'console coherence byte bound')
    require(type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']) is not None, 'console coherence hash shape')


def _validate_console_coherence_source_manifest(manifest, count):
    require(type(count) is int and count == 290, 'console coherence closed source count')
    require(type(manifest) is dict and len(manifest) == count, 'console coherence source count')
    require(set(manifest) == set(PUBLIC_SIGNIN_MANIFEST) | set(CONSOLE_COHERENCE_DELTA), 'console coherence source membership')
    for path, value in manifest.items():
        require(type(path) is str and not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts and str(PurePosixPath(path)) == path, 'console coherence unsafe path')
        _console_coherence_row(value)
    delta = {path: {'before': PUBLIC_SIGNIN_MANIFEST.get(path), 'after': value}
             for path, value in manifest.items() if PUBLIC_SIGNIN_MANIFEST.get(path) != value}
    require(delta == CONSOLE_COHERENCE_DELTA, 'console coherence exact delta')
    inverse = dict(manifest)
    for path, change in delta.items():
        if change['before'] is None:
            inverse.pop(path)
        else:
            inverse[path] = change['before']
    require(inverse == PUBLIC_SIGNIN_MANIFEST and canonical_digest(inverse) == PUBLIC_SIGNIN_SOURCE_DIGEST, 'console coherence complete v19 inverse')
    require(canonical_digest(manifest) == CONSOLE_COHERENCE_SOURCE_DIGEST, 'console coherence frozen source digest')
    return manifest


def validate_console_coherence_source_manifest(manifest, expected_digest=CONSOLE_COHERENCE_SOURCE_DIGEST, expected_count=None):
    require(type(expected_digest) is str and expected_digest == CONSOLE_COHERENCE_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == CONSOLE_COHERENCE_SOURCE_COUNT), 'caller cannot replace console coherence authority')
    return _validate_console_coherence_source_manifest(manifest, CONSOLE_COHERENCE_SOURCE_COUNT)


def _console_coherence_metadata(metadata):
    require(type(metadata) is dict and set(metadata) == {CONSOLE_COHERENCE_SOURCE_BASE + name for name in ('selection.json', 'selected-source-manifest.json')}, 'console coherence metadata membership')
    body = metadata[CONSOLE_COHERENCE_SOURCE_BASE + 'selection.json']
    require(type(body) is bytes and hashlib.sha256(body).hexdigest() == CONSOLE_COHERENCE_SELECTION_SHA256, 'console coherence selection pin mismatch')
    try:
        value = json.loads(body)
    except (ValueError, TypeError) as error:
        raise CollectorError('console coherence selection JSON') from error
    require(type(value) is dict and set(value) == {'schema', 'identity', 'operation', 'scope', 'selected', 'predecessor', 'exact_delta', 'runtime_or_GA_accepted', 'parent_contract_sha256', 'product_map_sha256'}, 'console coherence selection shape')
    require(type(value['schema']) is int and value['schema'] == 1 and value['identity'] == 'hosted-current-console-coherence-v20', 'console coherence typed schema')
    require(value['runtime_or_GA_accepted'] is False and value['parent_contract_sha256'] == CONSOLE_COHERENCE_PARENT_CONTRACT_SHA256 and value['product_map_sha256'] == CONSOLE_COHERENCE_PRODUCT_MAP_SHA256, 'console coherence scope contract')
    predecessor = value['predecessor']
    require(type(predecessor) is dict and set(predecessor) == {'source_count', 'source_digest_sha256', 'selection_sha256'}, 'console coherence predecessor shape')
    require(type(predecessor['source_count']) is int and predecessor == {'source_count': PUBLIC_SIGNIN_SOURCE_COUNT, 'source_digest_sha256': PUBLIC_SIGNIN_SOURCE_DIGEST, 'selection_sha256': PUBLIC_SIGNIN_SELECTION_SHA256}, 'console coherence typed predecessor')
    selected = value['selected']
    require(type(selected) is dict and set(selected) == {'source_count', 'source_digest_sha256', 'manifest'}, 'console coherence selected shape')
    require(type(selected['source_count']) is int and selected['source_count'] == 290 and selected['source_digest_sha256'] == CONSOLE_COHERENCE_SOURCE_DIGEST, 'console coherence selected count digest')
    reference = selected['manifest']
    require(type(reference) is dict and set(reference) == {'path', 'bytes', 'sha256'} and reference['path'] == 'selected-source-manifest.json', 'console coherence manifest reference')
    _console_coherence_row({key: reference[key] for key in ('bytes', 'sha256')})
    manifest_body = metadata[CONSOLE_COHERENCE_SOURCE_BASE + 'selected-source-manifest.json']
    require(type(manifest_body) is bytes and _file_row(manifest_body) == {key: reference[key] for key in ('bytes', 'sha256')}, 'console coherence manifest byte pin')
    try:
        manifest = json.loads(manifest_body)
    except (ValueError, TypeError) as error:
        raise CollectorError('console coherence manifest JSON') from error
    _validate_console_coherence_source_manifest(manifest, selected['source_count'])
    delta = value['exact_delta']
    require(type(delta) is dict and set(delta) == set(CONSOLE_COHERENCE_DELTA), 'console coherence delta membership')
    for path, change in delta.items():
        require(type(change) is dict and set(change) == {'before', 'after'}, 'console coherence delta row')
        if change['before'] is not None:
            _console_coherence_row(change['before'])
        _console_coherence_row(change['after'])
    require(delta == CONSOLE_COHERENCE_DELTA, 'console coherence typed inverse delta')
    return value, manifest


def validate_console_coherence_source_metadata(metadata):
    value, manifest = _console_coherence_metadata(metadata)
    require(manifest == CONSOLE_COHERENCE_MANIFEST, 'console coherence installed manifest')
    return value


def check_console_coherence_source(root):
    metadata = {CONSOLE_COHERENCE_SOURCE_BASE + name: (root / CONSOLE_COHERENCE_SOURCE_BASE / name).read_bytes() for name in ('selection.json', 'selected-source-manifest.json')}
    selection = validate_console_coherence_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in CONSOLE_COHERENCE_MANIFEST}
    validate_console_coherence_source_manifest(observed)
    return {'identity': selection['identity'], 'source_count': len(observed), 'source_digest_sha256': canonical_digest(observed), 'selection_sha256': CONSOLE_COHERENCE_SELECTION_SHA256, 'runtime_or_GA_accepted': False}


def _load_console_coherence_source_authority():
    root = Path(__file__).resolve().parents[2]
    metadata = {CONSOLE_COHERENCE_SOURCE_BASE + name: (root / CONSOLE_COHERENCE_SOURCE_BASE / name).read_bytes() for name in ('selection.json', 'selected-source-manifest.json')}
    value, manifest = _console_coherence_metadata(metadata)
    return CurrentSourceAuthority(value['selected']['source_count'], canonical_digest(manifest), manifest)


BUILD_CLOCK_SOURCE_BASE = 'verification/identity-network-current-source-v21/'
BUILD_CLOCK_SELECTION_SHA256 = '0e16b7b275af0be897e1344117d479b0e52068625f1516c19d665d7ac13f3117'
BUILD_CLOCK_SOURCE_DIGEST = '13cbf07d04bcbceaaaebb6278166bc18630e4d63f0fcf9857bca3e7319203463'
BUILD_CLOCK_PARENT_CONTRACT_SHA256 = '04e3509284e6d498d9b872c9c68a05debcb6d88250ee472737c916142ed543a4'
BUILD_CLOCK_PRODUCT_MAP_SHA256 = '7cc121e0acaf68f40c284981fd2d942ed2f0edf52588af8f3a11224a69d7f0d5'
BUILD_CLOCK_DELTA = {'hosted/lib/mixer_hosted/customer_builds/context.ex': {'before': {'bytes': 7552, 'sha256': '4a1b3604ad5616b7060e9678e1031e3c0afa19c5f90d75144f0cc66970024212'}, 'after': {'bytes': 7839, 'sha256': 'f6660527b4fafe9b8d97e67a2af0bb8ef43a61f2527067ffba422c10cf397eab'}}}


def _build_clock_row(value):
    require(type(value) is dict and set(value) == {'bytes', 'sha256'}, 'build clock row shape')
    require(type(value['bytes']) is int and 0 <= value['bytes'] <= MAX_COMMAND_BYTES, 'build clock byte bound')
    require(type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']) is not None, 'build clock hash shape')


def _validate_build_clock_source_manifest(manifest, count):
    require(type(count) is int and count == 290, 'build clock closed source count')
    require(type(manifest) is dict and len(manifest) == count, 'build clock source count')
    require(set(manifest) == set(CONSOLE_COHERENCE_MANIFEST) | set(BUILD_CLOCK_DELTA), 'build clock source membership')
    for path, value in manifest.items():
        require(type(path) is str and not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts and str(PurePosixPath(path)) == path, 'build clock unsafe path')
        _build_clock_row(value)
    delta = {path: {'before': CONSOLE_COHERENCE_MANIFEST.get(path), 'after': value}
             for path, value in manifest.items() if CONSOLE_COHERENCE_MANIFEST.get(path) != value}
    require(delta == BUILD_CLOCK_DELTA, 'build clock exact delta')
    inverse = dict(manifest)
    for path, change in delta.items():
        if change['before'] is None:
            inverse.pop(path)
        else:
            inverse[path] = change['before']
    require(inverse == CONSOLE_COHERENCE_MANIFEST and canonical_digest(inverse) == CONSOLE_COHERENCE_SOURCE_DIGEST, 'build clock complete v20 inverse')
    require(canonical_digest(manifest) == BUILD_CLOCK_SOURCE_DIGEST, 'build clock frozen source digest')
    return manifest


def validate_build_clock_source_manifest(manifest, expected_digest=BUILD_CLOCK_SOURCE_DIGEST, expected_count=None):
    require(type(expected_digest) is str and expected_digest == BUILD_CLOCK_SOURCE_DIGEST and
            (expected_count is None or type(expected_count) is int and expected_count == BUILD_CLOCK_SOURCE_COUNT), 'caller cannot replace build clock authority')
    return _validate_build_clock_source_manifest(manifest, BUILD_CLOCK_SOURCE_COUNT)


def _build_clock_metadata(metadata):
    require(type(metadata) is dict and set(metadata) == {BUILD_CLOCK_SOURCE_BASE + name for name in ('selection.json', 'selected-source-manifest.json')}, 'build clock metadata membership')
    body = metadata[BUILD_CLOCK_SOURCE_BASE + 'selection.json']
    require(type(body) is bytes and hashlib.sha256(body).hexdigest() == BUILD_CLOCK_SELECTION_SHA256, 'build clock selection pin mismatch')
    try:
        value = json.loads(body)
    except (ValueError, TypeError) as error:
        raise CollectorError('build clock selection JSON') from error
    require(type(value) is dict and set(value) == {'schema', 'identity', 'operation', 'scope', 'selected', 'predecessor', 'exact_delta', 'runtime_or_GA_accepted', 'parent_contract_sha256', 'product_map_sha256'}, 'build clock selection shape')
    require(type(value['schema']) is int and value['schema'] == 1 and value['identity'] == 'hosted-current-build-clock-v21', 'build clock typed schema')
    require(value['runtime_or_GA_accepted'] is False and value['parent_contract_sha256'] == BUILD_CLOCK_PARENT_CONTRACT_SHA256 and value['product_map_sha256'] == BUILD_CLOCK_PRODUCT_MAP_SHA256, 'build clock scope contract')
    predecessor = value['predecessor']
    require(type(predecessor) is dict and set(predecessor) == {'source_count', 'source_digest_sha256', 'selection_sha256'}, 'build clock predecessor shape')
    require(type(predecessor['source_count']) is int and predecessor == {'source_count': CONSOLE_COHERENCE_SOURCE_COUNT, 'source_digest_sha256': CONSOLE_COHERENCE_SOURCE_DIGEST, 'selection_sha256': CONSOLE_COHERENCE_SELECTION_SHA256}, 'build clock typed predecessor')
    selected = value['selected']
    require(type(selected) is dict and set(selected) == {'source_count', 'source_digest_sha256', 'manifest'}, 'build clock selected shape')
    require(type(selected['source_count']) is int and selected['source_count'] == 290 and selected['source_digest_sha256'] == BUILD_CLOCK_SOURCE_DIGEST, 'build clock selected count digest')
    reference = selected['manifest']
    require(type(reference) is dict and set(reference) == {'path', 'bytes', 'sha256'} and reference['path'] == 'selected-source-manifest.json', 'build clock manifest reference')
    _build_clock_row({key: reference[key] for key in ('bytes', 'sha256')})
    manifest_body = metadata[BUILD_CLOCK_SOURCE_BASE + 'selected-source-manifest.json']
    require(type(manifest_body) is bytes and _file_row(manifest_body) == {key: reference[key] for key in ('bytes', 'sha256')}, 'build clock manifest byte pin')
    try:
        manifest = json.loads(manifest_body)
    except (ValueError, TypeError) as error:
        raise CollectorError('build clock manifest JSON') from error
    _validate_build_clock_source_manifest(manifest, selected['source_count'])
    delta = value['exact_delta']
    require(type(delta) is dict and set(delta) == set(BUILD_CLOCK_DELTA), 'build clock delta membership')
    for path, change in delta.items():
        require(type(change) is dict and set(change) == {'before', 'after'}, 'build clock delta row')
        if change['before'] is not None:
            _build_clock_row(change['before'])
        _build_clock_row(change['after'])
    require(delta == BUILD_CLOCK_DELTA, 'build clock typed inverse delta')
    return value, manifest


def validate_build_clock_source_metadata(metadata):
    value, manifest = _build_clock_metadata(metadata)
    require(manifest == BUILD_CLOCK_MANIFEST, 'build clock installed manifest')
    return value


def check_build_clock_source(root):
    metadata = {BUILD_CLOCK_SOURCE_BASE + name: (root / BUILD_CLOCK_SOURCE_BASE / name).read_bytes() for name in ('selection.json', 'selected-source-manifest.json')}
    selection = validate_build_clock_source_metadata(metadata)
    observed = {path: _file_row((root / path).read_bytes()) for path in BUILD_CLOCK_MANIFEST}
    validate_build_clock_source_manifest(observed)
    return {'identity': selection['identity'], 'source_count': len(observed), 'source_digest_sha256': canonical_digest(observed), 'selection_sha256': BUILD_CLOCK_SELECTION_SHA256, 'runtime_or_GA_accepted': False}


def _load_build_clock_source_authority():
    root = Path(__file__).resolve().parents[2]
    metadata = {BUILD_CLOCK_SOURCE_BASE + name: (root / BUILD_CLOCK_SOURCE_BASE / name).read_bytes() for name in ('selection.json', 'selected-source-manifest.json')}
    value, manifest = _build_clock_metadata(metadata)
    return CurrentSourceAuthority(value['selected']['source_count'], canonical_digest(manifest), manifest)


def validate_source_unchanged(before, after):
    require(isinstance(before, dict) and isinstance(after, dict) and canonical_digest(before) == canonical_digest(after), "source/dependency/tool mutation")
    return after


def validate_generated_dag_row(row):
    require(isinstance(row, dict) and set(row) == {"bytes", "sha256", "type", "links", "uid", "gid", "mode", "parents"}, "generated DAG row shape")
    require(type(row["bytes"]) is int and 0 < row["bytes"] <= MAX_GENERATED_DAG_BYTES and isinstance(row["sha256"], str) and bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "generated DAG byte/hash bound")
    identity = {key: row[key] for key in ("type", "links", "uid", "gid", "mode")}
    require(canonical_digest(identity) == canonical_digest({"type": "regular", "links": 1, "uid": 0, "gid": 0, "mode": 0o644}), "generated DAG file identity")
    parents = {path: {"type": "directory", "uid": 0, "gid": 0, "mode": 0o755} for path in GENERATED_DAG_PARENTS}
    require(canonical_digest(row["parents"]) == canonical_digest(parents), "generated DAG parent identity")
    return row


def validate_compiled_source_unchanged(prepared, compiled):
    """Admit one fresh opaque compiler output; keep every prepared input exact."""
    require(isinstance(prepared, dict) and isinstance(compiled, dict) and set(prepared) == set(compiled) == {"source", "deps", "tools", "helpers"}, "compiled manifest sections")
    require(all(isinstance(value, dict) for value in [*prepared.values(), *compiled.values()]), "compiled manifest section shape")
    validate_build_clock_source_manifest(prepared["source"])
    require(GENERATED_DAG_PATH not in prepared["deps"], "generated DAG present before compilation")
    require(all(prepared["deps"].get(path) == row for path, row in TELEMETRY_INPUTS.items()), "locked telemetry compiler inputs missing or changed")
    validate_generated_dag_row(compiled["deps"].get(GENERATED_DAG_PATH))
    inputs = {**compiled, "deps": {path: row for path, row in compiled["deps"].items() if path != GENERATED_DAG_PATH}}
    validate_source_unchanged(prepared, inputs)
    return compiled


def validate_environment(caller_env):
    forbidden = ("MIXER_", "ERL_", "ELIXIR_", "MIX_", "HEX_", "AWS_")
    for key in caller_env:
        require(not key.startswith(forbidden) and key not in {"GITHUB_TOKEN", "GH_TOKEN", "BASH_ENV", "ENV", "LD_PRELOAD", "LD_LIBRARY_PATH"}, "inherited startup, isolation, or secret environment refused: " + key)
    return dict(TEST_ENV)


def validate_image_inspect(role, inspected):
    require(role in CAPS, "unknown image role")
    expected = IMAGES["pg" if role == "pg" else "test"]
    require(inspected.get("Id") == expected["config"], "image config mismatch")
    require(inspected.get("Os") == "linux" and inspected.get("Architecture") == "amd64", "image platform mismatch")
    # Docker normalizes library/postgres to postgres in RepoDigests.
    digests = [entry.split("@")[-1] for entry in inspected.get("RepoDigests", [])]
    require(expected["ref"].split("@")[-1] in digests, "image manifest mismatch")
    return inspected


@dataclasses.dataclass
class OwnedContainer:
    cid: str
    name: str
    role: str
    image_id: str
    label: str
    state: str = "owned"


class OwnedRegistry:
    def __init__(self):
        self.records = []
        self.unresolved = []

    def reserve(self, name, role, image_id, label):
        require(bool(re.fullmatch(r"mixer-identity-net-[0-9]+-[0-9]+-[0-9a-f]{32}-(prepare|test|pg)", name)), "unsafe owned name")
        require(role in CAPS and image_id == IMAGES["pg" if role == "pg" else "test"]["config"], "reservation identity mismatch")
        require(len(self.records) + len(self.unresolved) < 3, "container creation count exceeded")
        require(not any(r["name"] == name for r in self.unresolved) and not any(r.name == name for r in self.records), "duplicate reservation")
        self.unresolved.append({"name": name, "role": role, "image_id": image_id, "label": label, "state": "creating"})

    def add(self, cid, name, role, image_id, label):
        require(bool(re.fullmatch("[0-9a-f]{64}", cid)), "missing/invalid exact create CID")
        selected = [r for r in self.unresolved if r["name"] == name and r["state"] == "creating"]
        require(len(selected) == 1 and selected[0] == {"name": name, "role": role, "image_id": image_id, "label": label, "state": "creating"}, "unreserved create response")
        require(not any(r.cid == cid for r in self.records), "duplicate CID")
        self.unresolved.remove(selected[0])
        row = OwnedContainer(cid, name, role, image_id, label)
        self.records.append(row)
        return row

    def refuse(self, cid, reason):
        rows = [row for row in self.records if row.cid == cid]
        require(len(rows) == 1, "unknown refusal CID")
        rows[0].state = "identity_lost"

    def creation_unknown(self, name, reason):
        rows = [row for row in self.unresolved if row["name"] == name]
        require(len(rows) == 1, "unknown create reservation")
        rows[0].update(state="unknown", reason=str(reason))


def _caps(values):
    return {v.removeprefix("CAP_") for v in values or []}


def validate_owned_identity(inspected, owned):
    require(owned.role in CAPS and owned.state == "owned", "owned role/state mismatch")
    require(inspected.get("Id") == owned.cid and inspected.get("Image") == owned.image_id, "exact owned identity mismatch")
    require(inspected.get("Name", "").lstrip("/") == owned.name, "owned name mismatch")
    labels = inspected.get("Config", {}).get("Labels", {})
    require(labels.get("mixer.identity.run") == owned.label and labels.get("mixer.identity.role") == owned.role, "owned labels mismatch")


def validate_container_inspect(role, inspected, owned, test_cid=None):
    require(role == owned.role and owned.state == "owned", "container role/state mismatch")
    validate_owned_identity(inspected, owned)
    config = inspected.get("HostConfig", {})
    network = {"prepare": "bridge", "test": "none", "pg": "container:" + (test_cid or "")}[role]
    require(config.get("NetworkMode") == network and (role != "pg" or bool(test_cid)), "container network mismatch")
    require(config.get("ReadonlyRootfs") is True and config.get("Privileged") is False, "root/privilege mismatch")
    require(_caps(config.get("CapDrop")) == {"ALL"} and _caps(config.get("CapAdd")) == CAPS[role], "capability mismatch")
    require(config.get("SecurityOpt") == ["no-new-privileges:true"], "security option mismatch")
    for field in ("Binds", "Devices", "DeviceRequests", "PortBindings", "VolumesFrom", "ExtraHosts", "Links"):
        require(not config.get(field), "forbidden container setting: " + field)
    for field in ("PidMode", "IpcMode", "UTSMode", "UsernsMode"):
        require(config.get(field) not in {"host"}, "host namespace forbidden")
    require(not any((inspected.get("NetworkSettings", {}).get("Ports") or {}).values()), "published ports forbidden")
    require(config.get("Tmpfs") == TMPFS[role], "tmpfs contract mismatch")
    for mount in inspected.get("Mounts", []):
        require(mount.get("Type") == "tmpfs" and mount.get("Destination") in TMPFS[role], "host/anonymous mount forbidden")
    memory, cpus, pids = RESOURCES[role]
    require(config.get("Memory") == memory and config.get("MemorySwap") == memory and config.get("NanoCpus") == cpus * 1000000000 and config.get("PidsLimit") == pids, "resource limit mismatch")
    require(config.get("Ulimits") == [{"Name": "nofile", "Soft": 4096, "Hard": 4096}], "nofile mismatch")
    require(inspected.get("State", {}).get("OOMKilled") is not True, "container OOM")
    return inspected


PG_ENV = {"PATH": BASE_ENV["PATH"] + ":/usr/lib/postgresql/16/bin", "GOSU_VERSION": "1.19", "LANG": "en_US.utf8", "PG_MAJOR": "16", "PG_VERSION": "16.15-1.pgdg12+2", "PGDATA": "/var/lib/postgresql/data", "POSTGRES_USER": "mixer_fixture", "POSTGRES_DB": "mixer_startup_test", "POSTGRES_HOST_AUTH_METHOD": "trust"}


def validate_container_environment(role, inspected):
    values = inspected.get("Config", {}).get("Env", [])
    require(isinstance(values, list) and all(isinstance(v, str) and "=" in v for v in values), "container environment missing")
    actual = dict(v.split("=", 1) for v in values)
    require(len(actual) == len(values) and actual == (PG_ENV if role == "pg" else BASE_ENV), "actual container environment differs from allowlist")
    return actual


def validate_namespace(evidence, host_netns):
    require(evidence.get("interfaces") == ["lo"] and evidence.get("default_routes") == [], "external interface/route")
    require(bool(re.fullmatch(r"net:\[[0-9]+\]", evidence.get("netns", ""))) and evidence["netns"] != host_netns, "host/unknown network namespace")
    require(evidence.get("public_address") == "8.8.8.8" and evidence.get("setup_socket_closed") is True and evidence.get("open_setup_sockets", 0) == 0, "loopback setup incomplete")
    require(type(evidence.get("open_setup_sockets")) is int and evidence["open_setup_sockets"] == 0, "setup socket observation missing")
    for field in ("cap_eff", "cap_prm", "cap_bnd"):
        require(isinstance(evidence.get(field), str) and bool(re.fullmatch("[0-9a-fA-F]{16}", evidence[field])) and int(evidence[field], 16) == 0x1400, "actual capability mismatch")
    return evidence


def safe_members(archive, max_bytes=MAX_ARCHIVE_BYTES):
    require(0 < max_bytes <= MAX_ARCHIVE_BYTES, "archive cap override")
    members, names, total = [], set(), 0
    for member in archive:
        p = PurePosixPath(member.name)
        require(member.isfile() and not p.is_absolute() and ".." not in p.parts and str(p) == member.name and bool(p.parts) and "\\" not in member.name and not any(ord(c) < 32 for c in member.name), "unsafe archive member")
        require(member.name not in names, "duplicate archive member")
        require(not member.pax_headers, "extended archive metadata refused")
        total += member.size
        require(0 <= member.size <= max_bytes and total <= max_bytes and len(members) < 100000, "archive size/member cap")
        names.add(member.name)
        members.append(member)
    require(bool(members), "empty archive")
    return members


def validate_transfer_archive(data):
    """Validate the complete bounded stdin before any container operation."""
    require(type(data) is bytes and 0 < len(data) <= MAX_ARCHIVE_BYTES, "transfer archive byte cap/type")
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            members = safe_members(archive)
            for member in members:
                require(member.type in {tarfile.REGTYPE, tarfile.AREGTYPE} and member.sparse is None and member.offset_data == member.offset + 512, "transfer requires plain regular-file headers")
                require(0 <= member.mode <= 0o777, "transfer special permissions refused")
                body = archive.extractfile(member)
                remaining = member.size
                while remaining:
                    chunk = body.read(min(65536, remaining))
                    require(bool(chunk), "truncated transfer member")
                    remaining -= len(chunk)
            end = archive.offset
        require(len(data) % 512 == 0 and len(data) >= end + 1024 and not any(data[end:]), "incomplete/trailing transfer archive")
    except (tarfile.TarError, EOFError, OSError) as error:
        raise CollectorError("malformed transfer archive: " + str(error)) from error
    return data


def validate_prepared_archive(data, manifest):
    require(len(data) <= MAX_ARCHIVE_BYTES and set(manifest) == {"source", "deps", "tools", "helpers"}, "prepared archive/manifest shape")
    validate_build_clock_source_manifest(manifest["source"])
    expected = {}
    for section, rows in manifest.items():
        require(isinstance(rows, dict) and rows, "empty prepared section")
        for path, row in rows.items():
            require(path not in expected, "duplicate prepared manifest path")
            require(not any(part in {"_build", "evidence", "downloads", "home", "cache"} or part.startswith("mixer-key-owner-tls-") for part in PurePosixPath(path).parts), "forbidden prepared payload")
            if section == "deps":
                require(path.startswith("hosted/deps/"), "dependency injection path")
            if section == "tools":
                require(path == "tooling/rebar3" or path.startswith("tooling/mix/archives/hex-2.5.1/"), "bootstrap injection path")
            if section == "helpers":
                require(path in {"collector-prerequisites.exs", "collector-bootstrap.exs", "collector-manifest.exs", "collector-netns.exs", "collector-observer.exs", "collector-mounts.exs", "frozen-manifest.json"}, "helper injection path")
            expected[path] = row
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        members = safe_members(archive)
        require({m.name for m in members} == set(expected), "prepared archive path mismatch")
        for member in members:
            require(type(member.mtime) is int and member.mtime == PREPARED_MTIME, "prepared archive timestamp mismatch")
            body = archive.extractfile(member).read()
            require(expected[member.name] == {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}, "prepared archive hash mismatch")
            if member.name == "tooling/rebar3":
                require(hashlib.sha512(body).hexdigest() == BOOTSTRAP["rebar"]["sha512"], "installed Rebar artifact pin mismatch")
    helper_bytes = {"collector-prerequisites.exs": PREREQUISITES_EXS.encode(), "collector-bootstrap.exs": BOOTSTRAP_EXS.encode(), "collector-manifest.exs": MANIFEST_EXS.encode(), "collector-netns.exs": NETNS_EXS.encode(), "collector-observer.exs": OBSERVER_EXS.encode(), "collector-mounts.exs": MOUNTS_EXS.encode(), "frozen-manifest.json": json.dumps(BUILD_CLOCK_MANIFEST, sort_keys=True, separators=(",", ":")).encode()}
    require(manifest["helpers"] == {path: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for path, body in helper_bytes.items()}, "collector helper mutation")
    return expected


SEMANTICS = {
    "production-DNS-rebinding.json": {"initialQueries": 2, "authenticatedPeer": "8.8.8.8:443", "publicConnections": 1, "forbiddenSinkConnections": 0, "newPrivateAnswerRejectedBeforeConnect": True, "namespace": "disposable network-none Linux lo:1; no product resolver or loopback bypass"},
    "startup-production-network.json": {"actualApplication": True, "endpointLiveness": 200, "namespace": "owned Linux network-none NET_ADMIN; 8.8.8.8 on lo:1", "resolver": "127.0.0.1:53", "destination": "8.8.8.8:443", "startupDNSQueries": 0, "startupConnections": 0, "coldTokenAdmitted": True, "coldDNSQueries": 2, "coldConnections": 1, "oldLeaseRejectedAfterRestart": True, "restartColdAdmission": True, "shutdownInflightCancelled": True, "allThreeConnectionsClosed": True, "fixtureKeyDirectoryRemoved": True, "publicAdapter": "ConfiguredVerifier.authenticate/2", "productionPolicyBypasses": 0},
}


def validate_events(events, exit_code, semantic):
    require(exit_code == 0 and isinstance(events, list), "test exit/events missing")
    require(len(events) == 6 and events[0].get("event") == "suite_started" and events[-1].get("event") == "suite_finished", "incomplete/extra suite events")
    seen = []
    for offset in (1, 3):
        start, finish = events[offset:offset + 2]
        identity = (start.get("module"), start.get("name"))
        require(start.get("event") == "test_started" and finish.get("event") == "test_finished" and identity == (finish.get("module"), finish.get("name")), "test event ordering/identity")
        require(identity in EXPECTED_METHODS and finish.get("state", "missing") is None, "missing/extra/skipped/failed method")
        seen.append(identity)
    require(len(set(seen)) == 2, "duplicate method")
    require(all(type(events[-1].get(k)) is int and events[-1][k] == v for k, v in {"total": 2, "failures": 0, "skipped": 0, "excluded": 0, "invalid": 0}.items()), "suite accounting mismatch")
    require(set(semantic) == set(SEMANTICS), "semantic receipt count/name mismatch")
    for name, expected in SEMANTICS.items():
        # JSON true must not satisfy a numeric assertion (bool subclasses int).
        require(set(semantic[name]) == set(expected) and all(type(semantic[name][k]) is type(v) and semantic[name][k] == v for k, v in expected.items()), "semantic disagreement: " + name)
    return {"methods": 2, "no_skips": True, "semantic_receipts": sorted(semantic)}


def validate_command_result(returncode, stdout, stderr, *, limit=MAX_COMMAND_BYTES, oom=False):
    require(len(stdout) + len(stderr) <= limit, "output incomplete: cap reached")
    require(not oom, "OOM invalidates command")
    require(returncode == 0, "nonzero/timeout command")
    return True


def cleanup_plan(records):
    require(all(isinstance(r, OwnedContainer) and r.role in CAPS for r in records), "malformed cleanup registry")
    require(len({r.cid for r in records}) == len(records) and len({r.role for r in records}) == len(records) and len({r.name for r in records}) == len(records), "duplicate cleanup identity")
    require(all(r.state in {"owned", "removed"} for r in records), "cleanup identity unknown; no alternate route")
    result = []
    for role in ("pg", "test", "prepare"):
        for row in records:
            if row.role == role and row.state == "owned":
                require(bool(re.fullmatch("[0-9a-f]{64}", row.cid)), "invalid cleanup CID")
                result.extend([["docker", "stop", "--time", "2", row.cid], ["docker", "rm", "--volumes", row.cid]])
    return result


class Budget:
    def __init__(self, start=None, clock=time.monotonic, total=660, reserve=30):
        require(0 < reserve < total <= 660, "budget contract")
        self.clock, self.start, self.total, self.reserve = clock, clock() if start is None else start, total, reserve

    def remaining(self, timeout, cleanup=False):
        remaining = self.start + self.total - self.clock() - (0 if cleanup else self.reserve)
        require(type(timeout) in {int, float} and 0 < timeout <= 180 and remaining > 0, "aggregate deadline/cleanup reserve reached")
        return min(timeout, remaining)


MOUNTS_EXS = r'''
[role] = System.argv()
paths = case role do
  "prepare" -> ["/workspace", "/workspace/tooling", "/tmp"]
  "test" -> ["/workspace", "/workspace/tooling", "/tmp", "/run"]
end
source = "/proc/self/mountinfo"
{:ok, io} = File.open(source, [:read, :binary])
bytes = try do
  data = IO.binread(io, 65_537)
  true = is_binary(data) and byte_size(data) > 0 and byte_size(data) <= 65_536
  data
after
  :ok = File.close(io)
end
lines = String.split(bytes, "\n", trim: true)
true = length(lines) <= 1024
selected = Enum.filter(lines, fn line ->
  [_id, _parent, _device, _root, path, _flags | _] = String.split(line)
  Enum.any?(paths, fn selected_path -> path == selected_path or String.starts_with?(path, selected_path <> "/") end)
end)
true = length(selected) <= 32 and Enum.all?(selected, &(byte_size(&1) <= 4096))
modes = Map.new(paths, fn path ->
  %{type: :directory, mode: mode} = File.stat!(path)
  {path, Bitwise.band(mode, 0o7777)}
end)
result = %{"role" => role, "source" => source, "read_bytes" => byte_size(bytes), "read_sha256" => Base.encode16(:crypto.hash(:sha256, bytes), case: :lower), "selected_lines" => selected, "path_modes" => modes}
IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(result)))
'''


PREREQUISITES_EXS = r'''
emit = fn value -> IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(value))) end
hash = fn path -> :crypto.hash(:sha256, File.read!(path)) |> Base.encode16(case: :lower) end
tools = ["/usr/bin/env", "/usr/bin/tar", "/usr/bin/openssl", "/usr/local/bin/elixir", "/usr/local/bin/mix", "/usr/local/bin/erl", "/usr/local/bin/escript"]
rows = Map.new(tools, fn path ->
  %{type: :regular, mode: mode, size: size} = File.stat!(path)
  true = Bitwise.band(mode, 0o111) != 0
  {path, %{"sha256" => hash.(path), "bytes" => size}}
end)
"/usr/bin/openssl" = System.find_executable("openssl")
"1.20.4" = System.version()
"29" = to_string(:erlang.system_info(:otp_release))
otp_path = Path.join([to_string(:code.root_dir()), "releases", "29", "OTP_VERSION"])
"29.1.1" = File.read!(otp_path) |> String.trim()
{mix, 0} = System.cmd("/usr/local/bin/mix", ["--version"], stderr_to_stdout: true)
true = String.contains?(mix, "Mix 1.20.4")
{openssl, 0} = System.cmd("/usr/bin/openssl", ["version", "-a"], stderr_to_stdout: true)
true = String.starts_with?(openssl, "OpenSSL 3.0.22 ")
{tar, 0} = System.cmd("/usr/bin/tar", ["--version"], stderr_to_stdout: true)
true = byte_size(tar) < 65536 and String.starts_with?(tar, "tar (GNU tar) 1.34")
{:ok, _} = Application.ensure_all_started(:ssl)
ca_path = "/etc/ssl/certs/ca-certificates.crt"
%{type: :regular, size: 224449} = File.stat!(ca_path)
"714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5" = hash.(ca_path)
:ok = :public_key.cacerts_load(ca_path)
roots = :public_key.cacerts_get()
true = is_list(roots) and length(roots) > 0
root_hashes = Enum.map(roots, fn {:cert, der, _decoded} -> :crypto.hash(:sha256, der) |> Base.encode16(case: :lower) end) |> Enum.sort()
bundle_hashes = Enum.map(:public_key.pem_decode(File.read!(ca_path)), fn {:Certificate, der, :not_encrypted} -> :crypto.hash(:sha256, der) |> Base.encode16(case: :lower) end) |> Enum.sort()
true = root_hashes == bundle_hashes
libraries = Enum.map(:crypto.info_lib(), fn {name, number, version} -> %{"name" => to_string(name), "number" => number, "version" => to_string(version)} end)
[%{"name" => "OpenSSL", "number" => number, "version" => crypto_version}] = libraries
true = is_integer(number) and number > 0 and String.starts_with?(crypto_version, "OpenSSL 3.0.22 ")
ca = %{"path" => ca_path, "bytes" => 224449, "sha256" => hash.(ca_path), "load" => "explicit-selected-bundle", "loaded_count" => length(roots), "loaded_der_sha256" => root_hashes}
versions = %{"/usr/bin/tar" => tar}
emit.(%{"elixir" => System.version(), "otp_patch" => File.read!(otp_path) |> String.trim(), "mix" => mix, "openssl" => openssl, "crypto" => inspect(:crypto.info_lib()), "crypto_libraries" => libraries, "tools" => rows, "versions" => versions, "ca" => ca})
'''

MANIFEST_EXS = r'''
defmodule MixerIdentityNetworkCollector.Manifest do
  @generated "/workspace/hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl/source.dag"
  @generated_parents ["/workspace", "/workspace/hosted", "/workspace/hosted/deps", "/workspace/hosted/deps/telemetry", "/workspace/hosted/deps/telemetry/_build", "/workspace/hosted/deps/telemetry/_build/prod", "/workspace/hosted/deps/telemetry/_build/prod/lib", "/workspace/hosted/deps/telemetry/_build/prod/lib/.rebar3", "/workspace/hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl"]
  def files(path) do
    case File.lstat!(path).type do
      :regular -> [path]
      :directory -> File.ls!(path) |> Enum.sort() |> Enum.flat_map(&files(Path.join(path, &1)))
      _ -> raise "non-regular source/dependency/tool input"
    end
  end
  def generated_identity do
    parents = Map.new(@generated_parents, fn path ->
      %{type: :directory, uid: 0, gid: 0, mode: mode} = File.lstat!(path)
      0o755 = Bitwise.band(mode, 0o7777)
      {path, %{"type" => "directory", "uid" => 0, "gid" => 0, "mode" => 0o755}}
    end)
    %{type: :regular, links: 1, uid: 0, gid: 0, mode: mode, size: size} = File.lstat!(@generated)
    0o644 = Bitwise.band(mode, 0o7777)
    true = size > 0 and size <= 65536
    %{"type" => "regular", "links" => 1, "uid" => 0, "gid" => 0, "mode" => 0o644, "parents" => parents}
  end
  def entry(path) do
    identity = if path == @generated, do: generated_identity(), else: %{}
    bytes = File.read!(path)
    if path == @generated do
      true = byte_size(bytes) > 0 and byte_size(bytes) <= 65536
    end
    Map.merge(identity, %{"bytes" => byte_size(bytes), "sha256" => Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)})
  end
  def export_generated do
    generated_identity()
    bytes = File.read!(@generated)
    true = byte_size(bytes) > 0 and byte_size(bytes) <= 65536
    :ok = :io.setopts(:standard_io, encoding: :latin1)
    :ok = IO.binwrite(bytes)
  end
  def run do
    frozen = File.read!("/workspace/frozen-manifest.json") |> :json.decode()
    source = Map.new(frozen, fn {path, expected} ->
      actual = entry("/workspace/" <> path)
      ^expected = actual
      {path, actual}
    end)
    deps = Map.new(files("/workspace/hosted/deps"), fn path -> {Path.relative_to(path, "/workspace"), entry(path)} end)
    tools = Map.new(Enum.flat_map(["/workspace/tooling/mix", "/workspace/tooling/rebar3"], &files/1), fn path -> {Path.relative_to(path, "/workspace"), entry(path)} end)
    helpers = Map.new(Path.wildcard("/workspace/collector-*.exs") ++ ["/workspace/frozen-manifest.json"], fn path -> {Path.relative_to(path, "/workspace"), entry(path)} end)
    value = %{"source" => source, "deps" => deps, "tools" => tools, "helpers" => helpers}
    if System.argv() == ["archive-list"] do
      names = Map.keys(source) ++ Map.keys(deps) ++ Map.keys(tools) ++ Map.keys(helpers)
      true = Enum.all?(names, &(not String.contains?(&1, ["\n", "\r", "\0"])))
      File.write!("/workspace/archive-files.txt", Enum.join(Enum.sort(names), "\n") <> "\n", [:exclusive])
    end
    IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(value)))
  end
end
case System.argv() do
  ["export-generated"] -> MixerIdentityNetworkCollector.Manifest.export_generated()
  args when args in [[], ["archive-list"]] -> MixerIdentityNetworkCollector.Manifest.run()
end
'''

NETNS_EXS = r'''
{:ok, socket} = :socket.open(:inet, :dgram, :udp)
:ok = :socket.ioctl(socket, :sifaddr, ~c"lo:1", %{family: :inet, addr: {8, 8, 8, 8}, port: 0})
{:ok, %{addr: {8, 8, 8, 8}}} = :socket.ioctl(socket, :gifaddr, ~c"lo:1")
:ok = :socket.close(socket)
interfaces = File.read!("/proc/net/dev") |> String.split("\n") |> Enum.drop(2) |> Enum.filter(&String.contains?(&1, ":")) |> Enum.map(&(String.split(&1, ":") |> hd() |> String.trim())) |> Enum.sort()
routes = File.read!("/proc/net/route") |> String.split("\n", trim: true) |> Enum.drop(1) |> Enum.map(&String.split/1)
defaults = Enum.filter(routes, &(Enum.at(&1, 1) == "00000000"))
true = Enum.all?(routes, &(hd(&1) == "lo"))
ipv6 = File.read!("/proc/net/ipv6_route")
true = Enum.all?(String.split(ipv6, "\n", trim: true), &(String.split(&1) |> List.last() == "lo"))
status = File.read!("/proc/self/status") |> String.split("\n")
cap = fn key -> Enum.find_value(status, fn line -> case String.split(line, ":", parts: 2) do [^key, value] -> String.trim(value); _ -> nil end end) end
{:ok, netns} = File.read_link("/proc/self/ns/net")
IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(%{"interfaces" => interfaces, "default_routes" => defaults, "routes" => routes, "ipv6_routes" => ipv6, "netns" => netns, "public_address" => "8.8.8.8", "setup_socket_closed" => true, "open_setup_sockets" => 0, "cap_eff" => cap.("CapEff"), "cap_prm" => cap.("CapPrm"), "cap_bnd" => cap.("CapBnd")})))
'''

OBSERVER_EXS = r'''
defmodule MixerIdentityNetworkCollector.Observer do
  use GenServer
  def init(_options) do
    {:ok, output} = File.open("/workspace/evidence/events.jsonl", [:write, :exclusive])
    {:ok, %{output: output, bytes: 0, total: 0, failures: 0, skipped: 0, excluded: 0, invalid: 0}}
  end
  defp record(value, state) do
    line = Jason.encode!(value) <> "\n"
    true = byte_size(line) < 1048576 and state.bytes + byte_size(line) < 2097152
    :ok = IO.binwrite(state.output, line)
    %{state | bytes: state.bytes + byte_size(line)}
  end
  def handle_cast({:suite_started, _}, state), do: {:noreply, record(%{event: "suite_started"}, state)}
  def handle_cast({:test_started, test}, state), do: {:noreply, record(%{event: "test_started", module: Atom.to_string(test.module), name: Atom.to_string(test.name)}, state)}
  def handle_cast({:test_finished, test}, state) do
    category = case test.state do nil -> nil; {kind, _} -> kind; _ -> :failed end
    state = %{state | total: state.total + 1}
    state = case category do
      nil -> state
      :skipped -> %{state | skipped: state.skipped + 1}
      :excluded -> %{state | excluded: state.excluded + 1}
      :invalid -> %{state | invalid: state.invalid + 1}
      _ -> %{state | failures: state.failures + 1}
    end
    {:noreply, record(%{event: "test_finished", module: Atom.to_string(test.module), name: Atom.to_string(test.name), state: if(test.state == nil, do: nil, else: inspect(test.state, limit: 100))}, state)}
  end
  def handle_cast({:suite_finished, _times}, state) do
    modules = for {module, path} <- :code.all_loaded() do
      path = if is_list(path), do: List.to_string(path), else: inspect(path)
      hash = if File.regular?(path), do: Base.encode16(:crypto.hash(:sha256, File.read!(path)), case: :lower), else: nil
      %{module: Atom.to_string(module), path: path, sha256: hash}
    end
    apps = for {app, _description, version} <- :application.loaded_applications(), do: %{application: Atom.to_string(app), version: to_string(version)}
    otp = Path.join([to_string(:code.root_dir()), "releases", to_string(:erlang.system_info(:otp_release)), "OTP_VERSION"])
    identity = %{modules: Enum.sort_by(modules, & &1.module), applications: Enum.sort_by(apps, & &1.application), elixir: System.version(), otp_patch: File.read!(otp) |> String.trim(), vm: to_string(:erlang.system_info(:system_version)), architecture: to_string(:erlang.system_info(:system_architecture)), crypto: inspect(:crypto.info_lib())}
    :ok = File.write!("/workspace/evidence/runtime.json", Jason.encode!(identity, pretty: true), [:exclusive])
    final = state |> Map.take([:total, :failures, :skipped, :excluded, :invalid]) |> Map.put(:event, "suite_finished")
    state = record(final, state)
    :ok = File.close(state.output)
    {:noreply, state}
  end
  def handle_cast(_event, state), do: {:noreply, state}
end
'''

BOOTSTRAP_EXS = r'''
defmodule MixerIdentityNetworkCollector.Bootstrap do
  @cap 16_777_216
  def remaining(deadline) do
    left = deadline - System.monotonic_time(:millisecond)
    if left <= 0, do: raise("bootstrap artifact deadline")
    left
  end
  def line(socket, deadline, bytes \\ <<>>) do
    true = byte_size(bytes) < 8192
    {:ok, byte} = :ssl.recv(socket, 1, remaining(deadline))
    next = bytes <> byte
    if String.ends_with?(next, "\r\n"), do: next, else: line(socket, deadline, next)
  end
  def headers(socket, deadline, bytes, rows) do
    true = bytes < 65_536 and length(rows) < 128
    next = line(socket, deadline)
    true = bytes + byte_size(next) <= 65_536
    if next == "\r\n" do
      rows
    else
      [name, value] = String.split(String.trim_trailing(next, "\r\n"), ":", parts: 2)
      true = String.match?(name, ~r/\A[A-Za-z0-9-]+\z/)
      headers(socket, deadline, bytes + byte_size(next), [{String.downcase(name), String.trim(value)} | rows])
    end
  end
  def body(_socket, _io, 0, hash, _deadline), do: :crypto.hash_final(hash)
  def body(socket, io, left, hash, deadline) do
    count = min(left, 65_536)
    {:ok, bytes} = :ssl.recv(socket, count, remaining(deadline))
    ^count = byte_size(bytes)
    :ok = IO.binwrite(io, bytes)
    body(socket, io, left - count, :crypto.hash_update(hash, bytes), deadline)
  end
  def download(url, path, expected) do
    %URI{scheme: "https", host: "builds.hex.pm", port: 443, path: request_path, query: nil, userinfo: nil, fragment: nil} = URI.parse(url)
    true = String.starts_with?(request_path, "/installs/") and not String.contains?(request_path, ["\r", "\n"])
    deadline = System.monotonic_time(:millisecond) + 25_000
    options = [verify: :verify_peer, cacerts: :public_key.cacerts_get(), server_name_indication: ~c"builds.hex.pm", customize_hostname_check: [match_fun: :public_key.pkix_verify_hostname_match_fun(:https)], versions: [:"tlsv1.3", :"tlsv1.2"], active: false, mode: :binary, packet: :raw, send_timeout: 5000, send_timeout_close: true]
    {:ok, socket} = :ssl.connect(~c"builds.hex.pm", 443, options, min(10_000, remaining(deadline)))
    try do
      :ok = :ssl.send(socket, "GET " <> request_path <> " HTTP/1.1\r\nHost: builds.hex.pm\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n")
      status = line(socket, deadline)
      true = String.starts_with?(status, ["HTTP/1.1 200 ", "HTTP/1.0 200 "])
      values = headers(socket, deadline, byte_size(status), [])
      [] = for {"transfer-encoding", value} <- values, do: value
      encoding = for {"content-encoding", value} <- values, do: String.downcase(value)
      true = encoding in [[], ["identity"]]
      [length_text] = for {"content-length", value} <- values, do: value
      true = String.match?(length_text, ~r/\A[0-9]{1,8}\z/)
      length = String.to_integer(length_text)
      true = length > 0 and length <= @cap
      {:ok, io} = File.open(path, [:write, :binary, :exclusive])
      actual = try do
        body(socket, io, length, :crypto.hash_init(:sha512), deadline) |> Base.encode16(case: :lower)
      after
        :ok = File.close(io)
      end
      ^expected = actual
      {:error, :closed} = :ssl.recv(socket, 1, remaining(deadline))
      remaining(deadline)
      %{"url" => url, "bytes" => length, "sha512" => actual, "status" => 200, "redirects" => 0, "tls_peer_and_hostname_verified" => true, "content_length_and_eof_exact" => true}
    after
      :ssl.close(socket, min(1000, max(1, deadline - System.monotonic_time(:millisecond))))
    end
  end
  def run do
    {:ok, _} = Application.ensure_all_started(:ssl)
    ca_path = "/etc/ssl/certs/ca-certificates.crt"
    %{type: :regular, size: 224449} = File.stat!(ca_path)
    "714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5" = Base.encode16(:crypto.hash(:sha256, File.read!(ca_path)), case: :lower)
    :ok = :public_key.cacerts_load(ca_path)
    true = length(:public_key.cacerts_get()) > 0
    for path <- ["/workspace/home", "/workspace/tooling/mix", "/workspace/tooling/hex", "/workspace/cache", "/workspace/downloads", "/workspace/evidence"], do: File.mkdir_p!(path)
    [] = File.ls!("/workspace/tooling/mix")
    false = File.exists?("/workspace/tooling/rebar3")
    hex = download("HEX_URL", "/workspace/downloads/hex.ez", "HEX_SHA")
    rebar = download("REBAR_URL", "/workspace/downloads/rebar3", "REBAR_SHA")
    {installed, 0} = System.cmd("/usr/local/bin/mix", ["archive.install", "/workspace/downloads/hex.ez", "--sha512", "HEX_SHA", "--force"], stderr_to_stdout: true)
    true = byte_size(installed) < 1_048_576
    "/workspace/tooling/rebar3" = System.fetch_env!("MIX_REBAR3")
    source = "/workspace/downloads/rebar3"
    target = "/workspace/tooling/rebar3"
    %{type: :regular, size: source_bytes} = File.stat!(source)
    true = source_bytes > 0 and source_bytes <= 16_777_216
    rebar_bytes = File.read!(source)
    ^source_bytes = byte_size(rebar_bytes)
    "REBAR_SHA" = Base.encode16(:crypto.hash(:sha512, rebar_bytes), case: :lower)
    false = File.exists?(target)
    {:ok, target_io} = File.open(target, [:write, :binary, :exclusive])
    try do
      :ok = IO.binwrite(target_io, rebar_bytes)
    after
      :ok = File.close(target_io)
    end
    %{type: :regular, size: ^source_bytes} = File.stat!(target)
    target_sha = Base.encode16(:crypto.hash(:sha512, File.read!(target)), case: :lower)
    "REBAR_SHA" = target_sha
    :ok = File.rm(source)
    false = File.exists?(source)
    transfer = %{"source" => source, "destination" => target, "download_bytes" => source_bytes, "copied_bytes" => byte_size(rebar_bytes), "target_bytes" => File.stat!(target).size, "sha512" => target_sha, "exclusive_create" => true, "closed_before_hash" => true, "owned_download_removed" => true}
    File.chmod!("/workspace/tooling/rebar3", 0o755)
    {hex_version, 0} = System.cmd("/usr/local/bin/elixir", ["-pa", "/workspace/tooling/mix/archives/hex-2.5.1/hex-2.5.1/ebin", "-e", ":ok = Application.load(:hex); IO.puts(Application.spec(:hex, :vsn))"], stderr_to_stdout: true)
    "2.5.1" = String.trim(hex_version)
    {rebar_version, 0} = System.cmd("/workspace/tooling/rebar3", ["--version"], stderr_to_stdout: true)
    true = byte_size(rebar_version) < 65_536 and String.contains?(rebar_version, "rebar 3.28.0")
    IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(%{"hex" => hex, "rebar" => rebar, "hex_version" => String.trim(hex_version), "rebar_version" => rebar_version, "archive_install_output" => installed, "exact_rebar_path" => System.fetch_env!("MIX_REBAR3"), "rebar_transfer" => transfer})))
  end
end
MixerIdentityNetworkCollector.Bootstrap.run()
'''
for _placeholder, _value in {"HEX_URL": BOOTSTRAP["hex"]["url"], "HEX_SHA": BOOTSTRAP["hex"]["sha512"], "REBAR_URL": BOOTSTRAP["rebar"]["url"], "REBAR_SHA": BOOTSTRAP["rebar"]["sha512"]}.items():
    BOOTSTRAP_EXS = BOOTSTRAP_EXS.replace(_placeholder, _value)




def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".writing")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def json_marker(output):
    rows = [line.removeprefix(b"IDENTITY_JSON=") for line in output.splitlines() if line.startswith(b"IDENTITY_JSON=")]
    require(len(rows) == 1, "missing/duplicate structured command observation")
    return json.loads(rows[0])


def source_tar(files):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, body in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size, member.mode, member.mtime = len(body), 0o644, 0
            archive.addfile(member, io.BytesIO(body))
    return output.getvalue()


class Collector:
    """One attempt, no retries; command injection permits offline wiring review."""

    def __init__(self, root, output, sha, *, runner=None):
        self.root, self.output, self.sha = Path(root), Path(output), sha
        self.output.mkdir(exist_ok=False, parents=True)
        (self.output / "logs").mkdir()
        (self.output / ".scratch").mkdir()
        self.registry, self.budget = OwnedRegistry(), Budget()
        self.runner = runner
        self.cancelled, self.log_bytes, self.command_number = False, 0, 0
        self.run_id = os.environ.get("GITHUB_RUN_ID", "")
        self.attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
        require(re.fullmatch("[0-9]+", self.run_id or "") and re.fullmatch("[0-9]+", self.attempt or ""), "remote run identity missing")
        self.label = "mixer-identity-net-" + self.run_id + "-" + self.attempt + "-" + uuid.uuid4().hex
        self.state = {"schema": 1, "run_id": self.run_id, "attempt": self.attempt, "sha": sha, "label": self.label, "started_monotonic": self.budget.start, "status": "in-progress", "execution_scope": "two synthetic production-path network methods only; no GA or held-lane acceptance", "cleanup": {"status": "pending"}}
        self.persist()

    def persist(self):
        self.state.update(containers=[dataclasses.asdict(row) for row in self.registry.records], unresolved_creates=self.registry.unresolved, log_bytes=self.log_bytes, command_number=self.command_number, cancelled=self.cancelled)
        write_json(self.output / "state.json", self.state)

    def command(self, argv, timeout=15, *, input_bytes=None, limit=MAX_COMMAND_BYTES, binary_path=None, cleanup=False, check=True):
        require(cleanup or not self.cancelled, "cancelled; no new work")
        require(isinstance(argv, list) and all(isinstance(v, str) for v in argv), "argv must be literal strings")
        timeout = self.budget.remaining(timeout, cleanup=cleanup)
        raw_remaining = MAX_LOG_BYTES - self.log_bytes - (0 if cleanup else 1048576)
        require(raw_remaining > 0, "raw log cap/cleanup output reserve reached")
        self.command_number += 1
        stem = self.output / "logs" / f"{self.command_number:04d}"
        row = {"argv": argv, "cwd": str(self.root), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "timeout_seconds": timeout, "stdin_bytes": len(input_bytes or b""), "stdin_sha256": hashlib.sha256(input_bytes).hexdigest() if input_bytes is not None else None, "stdout_complete": False, "stderr_complete": False}
        started = time.monotonic()
        out, err, process, overflow, timed_out = bytearray(), bytearray(), None, False, False
        # Deliberately excludes caller Docker config, startup flags and credentials.
        environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(self.output / ".scratch"), "DOCKER_CONFIG": str(self.output / ".scratch" / "docker"), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
        row["host_environment"] = environment
        try:
            if self.runner is not None:
                code, stdout, stderr = self.runner(argv, timeout, input_bytes)
                out.extend(stdout)
                err.extend(stderr)
                overflow = len(out) + len(err) > limit or len(err) > min(MAX_COMMAND_BYTES, raw_remaining) or (binary_path is None and len(out) + len(err) > raw_remaining)
                if overflow:
                    err = err[:min(MAX_COMMAND_BYTES, raw_remaining)]
                    out = out[:max(0, min(limit - len(err), raw_remaining - len(err) if binary_path is None else limit))]
            else:
                process = subprocess.Popen(argv, cwd=self.root, env=environment, stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=False)
                with selectors.DefaultSelector() as selected:
                    for pipe, kind in ((process.stdout, "stdout"), (process.stderr, "stderr")):
                        os.set_blocking(pipe.fileno(), False)
                        selected.register(pipe, selectors.EVENT_READ, kind)
                    pending = memoryview(input_bytes or b"")
                    if process.stdin is not None:
                        os.set_blocking(process.stdin.fileno(), False)
                        selected.register(process.stdin, selectors.EVENT_WRITE, "stdin")
                    while selected.get_map():
                        if time.monotonic() - started >= timeout or (self.cancelled and not cleanup):
                            timed_out = True
                            break
                        for key, _ in selected.select(min(0.1, max(0, timeout - (time.monotonic() - started)))):
                            if key.data == "stdin":
                                if pending:
                                    try:
                                        consumed = os.write(key.fileobj.fileno(), pending[:65536])
                                        pending = pending[consumed:]
                                    except BrokenPipeError:
                                        pending = pending[:0]
                                if not pending:
                                    selected.unregister(key.fileobj)
                                    key.fileobj.close()
                                continue
                            chunk = os.read(key.fileobj.fileno(), 65536)
                            if not chunk:
                                selected.unregister(key.fileobj)
                                key.fileobj.close()
                            else:
                                target = out if key.data == "stdout" else err
                                log_used = len(err) + (len(out) if binary_path is None else 0)
                                is_raw = key.data == "stderr" or binary_path is None
                                if len(out) + len(err) + len(chunk) > limit or (is_raw and log_used + len(chunk) > raw_remaining) or (key.data == "stderr" and len(err) + len(chunk) > MAX_COMMAND_BYTES):
                                    overflow = True
                                    break
                                target.extend(chunk)
                        if overflow:
                            break
                if timed_out or overflow:
                    process.terminate()  # Only this direct CLI child, never a process group.
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=1)
                else:
                    process.wait(timeout=max(0.01, timeout - (time.monotonic() - started)))
                code = process.returncode
            row.update(exit_code=code, stdout_complete=not (overflow or timed_out), stderr_complete=not (overflow or timed_out), overflow=overflow, timed_out=timed_out, elapsed_seconds=time.monotonic() - started, stdout_bytes=len(out), stderr_bytes=len(err))
            if binary_path is not None:
                Path(binary_path).write_bytes(out)
                row["stdout_artifact"] = str(Path(binary_path).relative_to(self.output))
                row["stdout_sha256"] = hashlib.sha256(out).hexdigest()
            else:
                self.log_bytes += len(out)
                stem.with_suffix(".stdout").write_bytes(out)
            self.log_bytes += len(err)
            stem.with_suffix(".stderr").write_bytes(err)
            require(self.log_bytes <= MAX_LOG_BYTES, "aggregate raw log cap reached")
            require(not overflow and not timed_out, "command timeout/output incomplete")
            if check:
                validate_command_result(code, out, err, limit=limit)
            return bytes(out), bytes(err), code
        except BaseException as error:
            row["failure"] = str(error)
            row["stdout_complete"], row["stderr_complete"] = False, False
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)
            raise
        finally:
            if process is not None:
                for pipe in (process.stdin, process.stdout, process.stderr):
                    if pipe is not None and not pipe.closed:
                        pipe.close()
            write_json(stem.with_suffix(".json"), row)
            self.persist()

    def git_blobs(self, paths):
        raw, _, _ = self.command(["git", "--no-replace-objects", "cat-file", "--batch"], input_bytes="".join(self.sha + ":" + path + "\n" for path in paths).encode())
        result, cursor = {}, 0
        for path in paths:
            end = raw.index(b"\n", cursor)
            header = raw[cursor:end].split()
            require(len(header) == 3 and header[1] == b"blob" and header[2].isdigit(), "missing/nonblob delivered input: " + path)
            size = int(header[2])
            cursor = end + 1
            result[path] = raw[cursor:cursor + size]
            cursor += size
            require(raw[cursor:cursor + 1] == b"\n", "git batch framing")
            cursor += 1
        require(cursor == len(raw), "extra git blobs")
        return result

    def inspect(self, owned, cleanup=False):
        require(owned.state == "owned", "sticky owned identity loss; no retry")
        try:
            output, _, _ = self.command(["docker", "container", "inspect", owned.cid], cleanup=cleanup)
            rows = json.loads(output)
            require(len(rows) == 1, "inspect count mismatch")
            validate_owned_identity(rows[0], owned)
        except BaseException as error:
            self.registry.refuse(owned.cid, str(error))
            self.persist()
            raise
        if not cleanup:
            test = next((row.cid for row in self.registry.records if row.role == "test"), None)
            validate_container_inspect(owned.role, rows[0], owned, test)
        return rows[0]

    def docker(self, owned, argv, timeout=15, **options):
        self.inspect(owned, cleanup=options.get("cleanup", False))
        try:
            result = self.command(["docker", *argv, owned.cid], timeout, **options)
            if result[2] != 0:
                self.refuse_if_permission_denied(owned)
            return result
        except CollectorError as error:
            self.refuse_if_permission_denied(owned, str(error))
            raise

    def refuse_if_permission_denied(self, owned, failure=""):
        # Permission uncertainty remains sticky even when a caller collects a
        # nonzero status (readiness/log capture); it cannot authorize cleanup.
        path = self.output / "logs" / f"{self.command_number:04d}.stderr"
        recent = failure.encode().lower() + (path.read_bytes().lower() if path.is_file() else b"")
        if any(word in recent for word in (b"permission denied", b"operation not permitted", b"access denied")):
            if owned.state == "owned":
                self.registry.refuse(owned.cid, "Docker permission refusal")
                self.persist()
            raise CollectorError("Docker permission refused; exact CID state unknown; no retry")

    def execute(self, owned, argv, timeout=15, *, environment=None, check=True, workdir=None, **options):
        require(workdir is None or (workdir == "/workspace" and owned.role in {"prepare", "test"}), "unreviewed exec workdir")
        input_bytes = options.get("input_bytes")
        require(input_bytes is None or (type(input_bytes) is bytes and len(input_bytes) <= MAX_ARCHIVE_BYTES), "exec stdin byte cap/type")
        self.inspect(owned)
        env = environment or BASE_ENV
        args = ["docker", "exec", *(["-i"] if input_bytes is not None else []), "--workdir", workdir or ("/" if owned.role == "pg" else "/workspace/hosted")]
        args += [part for key, value in sorted(env.items()) for part in ("--env", key + "=" + value)]
        args += [owned.cid, "/usr/bin/env", "-i", *[key + "=" + value for key, value in sorted(env.items())], *argv]
        try:
            result = self.command(args, timeout, check=check, **options)
            if result[2] != 0:
                self.refuse_if_permission_denied(owned)
            return result
        except CollectorError as error:
            self.refuse_if_permission_denied(owned, str(error))
            raise

    def create(self, role, test_cid=None):
        image = IMAGES["pg" if role == "pg" else "test"]
        name = self.label + "-" + role
        self.registry.reserve(name, role, image["config"], self.label)
        self.persist()  # Reservation precedes the possibly lost create response.
        memory, cpus, pids = RESOURCES[role]
        argv = ["docker", "create", "--pull", "never", "--platform", "linux/amd64", "--name", name, "--label", "mixer.identity.run=" + self.label, "--label", "mixer.identity.role=" + role, "--network", "container:" + test_cid if role == "pg" else ("none" if role == "test" else "bridge"), "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--memory", str(memory), "--memory-swap", str(memory), "--cpus", str(cpus), "--pids-limit", str(pids), "--ulimit", "nofile=4096:4096"]
        for cap in sorted(CAPS[role]):
            argv += ["--cap-add", cap]
        for path, options in TMPFS[role].items():
            argv += ["--tmpfs", path + ":" + options]
        env = {"POSTGRES_USER": "mixer_fixture", "POSTGRES_DB": "mixer_startup_test", "POSTGRES_HOST_AUTH_METHOD": "trust"} if role == "pg" else BASE_ENV
        for key, value in sorted(env.items()):
            argv += ["--env", key + "=" + value]
        if role != "pg":
            argv += ["--entrypoint", "/usr/local/bin/elixir", image["config"], "-e", "Process.sleep(:infinity)"]
        else:
            argv += [image["config"], "-c", "listen_addresses=127.0.0.1", "-c", "timezone=UTC"]
        try:
            output, _, _ = self.command(argv)
            row = self.registry.add(output.decode().strip(), name, role, image["config"], self.label)
        except BaseException as error:
            self.registry.creation_unknown(name, str(error))
            self.persist()
            raise
        self.persist()
        self.inspect(row)
        return row

    def copy_in(self, owned, data):
        require(owned.role in {"prepare", "test"}, "unreviewed transfer role")
        validate_transfer_archive(data)
        # docker cp's daemon path refuses a read-only root even for this tmpfs.
        # Both generated archives use uid/gid 0. Ignore stored ownership and
        # special permission restoration; no CHOWN/FOWNER capability is needed.
        self.execute(owned, ["/usr/bin/tar", "--extract", "--file", "-", "--directory", "/workspace", "--no-same-owner", "--no-same-permissions"], 30, input_bytes=data, workdir="/workspace")

    def copy_file_out(self, owned, path, maximum=MAX_COMMAND_BYTES):
        require(path in {"/workspace/prepared.tar", "/workspace/downloads/hex.ez", "/workspace/tooling/rebar3"} or path.startswith("/workspace/evidence/"), "unreviewed copy-out path")
        require(0 < maximum <= MAX_ARCHIVE_BYTES, "copy-out cap")
        literal = "path = " + json.dumps(path) + "; true = File.stat!(path).size <= " + str(maximum) + "; :ok = :io.setopts(:standard_io, encoding: :latin1); :ok = IO.binwrite(File.read!(path))"
        public_tool = {"/workspace/downloads/hex.ez": "hex", "/workspace/tooling/rebar3": "rebar"}.get(path)
        if public_tool is not None:
            require(maximum <= 16777216, "public bootstrap export cap")
            destination = self.output / "bootstrap-exports" / (public_tool + "-actual.bin")
            destination.parent.mkdir(exist_ok=True)
            require(not destination.exists(), "public bootstrap export already retained")
        else:
            destination = self.output / ".scratch" / "copy.bin"
        try:
            result, _, _ = self.execute(owned, ["/usr/local/bin/elixir", "-e", literal], 30, limit=maximum, binary_path=destination)
        finally:
            # Only these two fixed public artifacts survive a failed host check.
            # Partial command captures remain partial; they cannot be a tool pass.
            if public_tool is not None and destination.is_file():
                require(destination.stat().st_size <= maximum, "retained public bootstrap capture cap")
                body = destination.read_bytes()
                log = self.output / "logs" / f"{self.command_number:04d}.json"
                command = json.loads(log.read_bytes()) if log.is_file() else {}
                write_json(destination.with_suffix(".json"), {"schema": 1, "tool": public_tool, "container_path": path, "owned_cid": owned.cid, "role": owned.role, "command_number": self.command_number, "maximum_bytes": maximum, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "sha512": hashlib.sha512(body).hexdigest(), "expected_sha512": BOOTSTRAP[public_tool]["sha512"], "stdout_complete": command.get("stdout_complete"), "stderr_complete": command.get("stderr_complete"), "command_exit_code": command.get("exit_code"), "qualification": "bounded-public-command-stdout-only-before-host-size-and-digest-validation"})
        if public_tool is None:
            destination.unlink()
        return result

    def capture_generated_dag(self, owned, expected, timeout=15):
        require(owned.role == "test" and owned.state == "owned", "generated DAG export requires owned test role")
        require(type(timeout) in (int, float) and 0 < timeout <= 15, "generated DAG export time bound")
        validate_generated_dag_row(expected)
        destination = self.output / "compiler-generated" / "telemetry-source.dag"
        destination.parent.mkdir(exist_ok=True)
        require(not destination.exists(), "generated DAG capture already retained")
        try:
            body, _, _ = self.execute(owned, ["/usr/local/bin/elixir", "/workspace/collector-manifest.exs", "export-generated"], timeout, limit=MAX_GENERATED_DAG_BYTES, binary_path=destination)
        finally:
            if destination.is_file():
                require(destination.stat().st_size <= MAX_GENERATED_DAG_BYTES, "retained generated DAG capture cap")
                actual = destination.read_bytes()
                log = self.output / "logs" / f"{self.command_number:04d}.json"
                command = json.loads(log.read_bytes()) if log.is_file() else {}
                write_json(destination.with_suffix(".json"), {"schema": 1, "classification": "opaque-postcompile-rebar-telemetry-metadata", "container_path": "/workspace/" + GENERATED_DAG_PATH, "owned_cid": owned.cid, "role": owned.role, "phase": "after-offline-compile-before-test-authorization", "command_number": self.command_number, "maximum_bytes": MAX_GENERATED_DAG_BYTES, "bytes": len(actual), "sha256": hashlib.sha256(actual).hexdigest(), "expected_manifest_row": expected, "stdout_complete": command.get("stdout_complete"), "stderr_complete": command.get("stderr_complete"), "command_exit_code": command.get("exit_code"), "qualification": "bounded-opaque-command-stdout-only-before-host-input-equality-validation"})
        require({"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} == {key: expected[key] for key in ("bytes", "sha256")}, "generated DAG capture differs from compiled manifest")
        return {"path": GENERATED_DAG_PATH, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "classification": "opaque-postcompile-rebar-telemetry-metadata"}

    def stop_remove(self, owned):
        self.inspect(owned, cleanup=True)
        self.docker(owned, ["stop", "--time", "2"], cleanup=True)
        terminal = self.inspect(owned, cleanup=True)
        require(terminal.get("State", {}).get("Running") is False, "container still running after stop")
        if terminal.get("State", {}).get("OOMKilled") is True:
            self.state.setdefault("qualification_failures", []).append({"cid": owned.cid, "role": owned.role, "failure": "terminal OOMKilled"})
            self.persist()  # Preserve failure, then still remove this exact ID.
        write_json(self.output / (owned.role + "-terminal.json"), terminal)
        self.docker(owned, ["logs"], cleanup=True)
        self.docker(owned, ["rm", "--volumes"], cleanup=True)
        try:
            output, stderr, code = self.command(["docker", "container", "inspect", owned.cid], cleanup=True, check=False)
            require(code != 0 and b"No such container" in stderr and not any(word in stderr.lower() for word in (b"permission", b"operation not permitted", b"access denied")), "exact CID absence not observed")
        except BaseException as error:
            self.registry.refuse(owned.cid, "post-remove absence unknown: " + str(error))
            self.persist()
            raise
        owned.state = "removed"
        self.persist()

    def cleanup(self):
        errors = []
        for role in ("pg", "test", "prepare"):
            for row in self.registry.records:
                if row.role == role and row.state == "owned":
                    try:
                        self.stop_remove(row)
                    except BaseException as error:
                        errors.append({"cid": row.cid, "role": role, "failure": str(error)})
        clean = not errors and not self.registry.unresolved and all(row.state == "removed" for row in self.registry.records)
        self.state["cleanup"] = {"status": "verified-exact-created-IDs-absent" if clean else "FAILED-unknown-or-incomplete", "errors": errors, "unresolved_creates": self.registry.unresolved, "container_teardown_is_product_lifecycle_proof": False}
        self.persist()
        return clean

    def seal(self):
        scratch = self.output / ".scratch"
        if scratch.exists():
            shutil.rmtree(scratch)  # Only the output directory exclusively created above.
        self.state["host_scratch_cleanup"] = "removed owned .scratch; package outputs retained"
        self.persist()
        paths = [p for p in self.output.rglob("*") if p.is_file() and p.name != "artifact-manifest.json"]
        total = sum(p.stat().st_size for p in paths)
        if total > MAX_ARTIFACT_BYTES:
            self.state["status"] = "FAILED-artifact-cap"
            self.state["artifact_cap_exceeded_bytes"] = total
            # Retain failure receipts and hashes; do not upload an unbounded archive.
            for path in paths:
                if path.name.endswith(".tar"):
                    self.state.setdefault("omitted_oversize_archives", []).append({"path": str(path.relative_to(self.output)), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                    path.unlink()
            self.persist()
            paths = [p for p in self.output.rglob("*") if p.is_file() and p.name != "artifact-manifest.json"]
        files = {str(p.relative_to(self.output)): {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths}
        write_json(self.output / "artifact-manifest.json", {"schema": 1, "files": files, "tree_digest_sha256": canonical_digest(files), "scope": self.state["execution_scope"]})

    def run(self):
        """Freeze primary outcome before finally; cleanup can only reduce qualification."""
        try:
            self.collect()
            require(not self.cancelled, "cancelled before primary outcome")
            self.state["status"] = "two-methods-passed-pending-owned-cleanup-and-independent-acceptance"
        except BaseException as error:
            self.state["status"] = "FAILED-or-partial"
            self.state["primary_failure"] = {"type": type(error).__name__, "message": str(error)}
        finally:
            self.state["primary_outcome_frozen"] = True
            self.persist()
            clean = self.cleanup()
            if not clean:
                self.state["status"] = "FAILED-cleanup-unknown-or-incomplete"
            if self.state.get("qualification_failures"):
                self.state["status"] = "FAILED-terminal-runtime-state"
            if self.cancelled:
                self.state["status"] = "FAILED-cancelled"
            self.seal()
        return 0 if not self.cancelled and self.state["status"] == "two-methods-passed-pending-owned-cleanup-and-independent-acceptance" else 1

    def observe_mounts(self, owned):
        require(owned.role in {"prepare", "test"}, "mount observation role refused")
        output, _, _ = self.execute(owned, ["/usr/local/bin/elixir", "/workspace/collector-mounts.exs", owned.role], 15, limit=65536)
        observed = validate_mount_observation(owned.role, json_marker(output))
        write_json(self.output / (owned.role + "-mount-policy.json"), observed)
        return observed

    def collect(self):
        require(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_OS") == "Linux" and os.environ.get("RUNNER_ARCH") == "X64", "only selected GitHub Linux AMD64 runner is supported")
        require(os.uname().sysname == "Linux" and os.uname().machine == "x86_64", "actual host platform mismatch")
        validate_environment(os.environ)
        require(re.fullmatch("[0-9a-f]{40}", self.sha), "delivery SHA must be exact")
        head, _, _ = self.command(["git", "--no-replace-objects", "rev-parse", "HEAD"])
        require(head.decode().strip() == self.sha, "checkout delivery revision mismatch")
        validate_build_clock_source_manifest(BUILD_CLOCK_MANIFEST)
        product = self.git_blobs(sorted(BUILD_CLOCK_MANIFEST))
        observed = {path: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for path, body in product.items()}
        validate_build_clock_source_manifest(observed)  # All static product/lock checks precede create/pull.
        self.state["source"] = {"delivery_revision": self.sha, "frozen_product_commit": PRODUCT_COMMIT, "product_files": len(observed), "product_tree_digest_sha256": canonical_digest(observed), "lock_sha256": FROZEN_LOCK_SHA256}
        write_json(self.output / "product-source-manifest.json", observed)
        control_paths = ["hosted/scripts/test-identity-network.py", "hosted/scripts/test_identity_network_collector.py", "docs/hosted-identity-production-network-ci-contract.md", ".github/workflows/identity-network.yml"]
        controls = self.git_blobs(control_paths)
        for path, body in controls.items():
            require((self.root / path).read_bytes() == body, "dirty delivered collector/control/workflow: " + path)
        write_json(self.output / "collector-source-bindings.json", {path: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for path, body in controls.items()})
        (self.output / "collector-source.tar").write_bytes(source_tar(controls))
        amendment_manifest = self.git_blobs([AMENDMENT_BASE + "packet-manifest.json"])
        amendment_files = validate_amendment_manifest(amendment_manifest[AMENDMENT_BASE + "packet-manifest.json"])
        metadata = {**amendment_manifest, **self.git_blobs(predecessor_metadata_paths() + [AMENDMENT_BASE + path for path in amendment_files])}
        amendment = validate_selected_metadata(metadata)
        execution_manifest = self.git_blobs([EXECUTION_BASE + "packet-manifest.json"])
        execution_files = validate_execution_manifest(execution_manifest[EXECUTION_BASE + "packet-manifest.json"])
        metadata.update(execution_manifest)
        metadata.update(self.git_blobs([EXECUTION_BASE + path for path in execution_files]))
        validate_execution_metadata(metadata)
        fixture_manifest = self.git_blobs([FIXTURE_BASE + "packet-manifest.json"])
        fixture_files = validate_fixture_manifest(fixture_manifest[FIXTURE_BASE + "packet-manifest.json"])
        metadata.update(fixture_manifest)
        metadata.update(self.git_blobs([FIXTURE_BASE + path for path in fixture_files]))
        format_manifest = self.git_blobs([FORMAT_BASE + "packet-manifest.json"])
        format_files = validate_format_manifest(format_manifest[FORMAT_BASE + "packet-manifest.json"])
        metadata.update(format_manifest)
        metadata.update(self.git_blobs([FORMAT_BASE + path for path in format_files]))
        validate_format_metadata(metadata)
        predecessor_metadata = self.git_blobs([CURRENT_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_current_source_metadata(predecessor_metadata)
        metadata.update(predecessor_metadata)
        current_metadata = self.git_blobs([SUCCESSOR_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_successor_source_metadata(current_metadata)
        metadata.update(current_metadata)
        private_metadata = self.git_blobs([PRIVATE_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_private_source_metadata(private_metadata)
        metadata.update(private_metadata)
        browser_metadata = self.git_blobs([BROWSER_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_browser_source_metadata(browser_metadata)
        metadata.update(browser_metadata)
        operation_metadata = self.git_blobs([OPERATION_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_operation_source_metadata(operation_metadata)
        metadata.update(operation_metadata)
        lifetime_metadata = self.git_blobs([LIFETIME_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_lifetime_source_metadata(lifetime_metadata)
        metadata.update(lifetime_metadata)
        commit_metadata = self.git_blobs([COMMIT_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_commit_source_metadata(commit_metadata)
        metadata.update(commit_metadata)
        proxy_metadata = self.git_blobs([PROXY_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_proxy_source_metadata(proxy_metadata)
        metadata.update(proxy_metadata)
        customer_build_metadata = self.git_blobs([BUILD_READ_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_customer_build_source_metadata(customer_build_metadata)
        metadata.update(customer_build_metadata)
        customer_build_metadata = self.git_blobs([BROWSER_BUILD_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_browser_build_source_metadata(customer_build_metadata)
        metadata.update(customer_build_metadata)
        owned_metadata = self.git_blobs([OWNED_EVIDENCE_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_owned_evidence_source_metadata(owned_metadata)
        metadata.update(owned_metadata)
        compiler_metadata = self.git_blobs([HOSTED_COMPILER_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_hosted_compiler_source_metadata(compiler_metadata)
        metadata.update(compiler_metadata)
        catalog_metadata = self.git_blobs([CATALOG_JOIN_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_catalog_join_source_metadata(catalog_metadata)
        metadata.update(catalog_metadata)
        provider_metadata = self.git_blobs([PROVIDER_HTTPS_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_provider_https_source_metadata(provider_metadata)
        metadata.update(provider_metadata)
        ordinary_metadata = self.git_blobs([ORDINARY_BROWSER_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_ordinary_browser_source_metadata(ordinary_metadata)
        metadata.update(ordinary_metadata)
        supervised_metadata = self.git_blobs([SUPERVISED_PROVIDER_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_supervised_provider_source_metadata(supervised_metadata)
        metadata.update(supervised_metadata)
        provider_io_metadata = self.git_blobs([PROVIDER_IO_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_provider_io_source_metadata(provider_io_metadata)
        metadata.update(provider_io_metadata)
        configured_metadata = self.git_blobs([CONFIGURED_STARTUP_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_configured_startup_source_metadata(configured_metadata)
        metadata.update(configured_metadata)
        historical_signin = self.git_blobs([PUBLIC_SIGNIN_SOURCE_BASE + name for name in ('selection.json', 'selected-source-manifest.json')])
        validate_public_signin_source_metadata(historical_signin)
        metadata.update(historical_signin)
        historical_coherence = self.git_blobs([CONSOLE_COHERENCE_SOURCE_BASE + name for name in ('selection.json', 'selected-source-manifest.json')])
        validate_console_coherence_source_metadata(historical_coherence)
        metadata.update(historical_coherence)
        signin_metadata = self.git_blobs([BUILD_CLOCK_SOURCE_BASE + name for name in ("selection.json", "selected-source-manifest.json")])
        validate_build_clock_source_metadata(signin_metadata)
        metadata.update(signin_metadata)
        self.state["source"].update(current_source_selection_sha256=BUILD_CLOCK_SELECTION_SHA256, current_source_digest_sha256=BUILD_CLOCK_SOURCE_DIGEST)
        self.prerequisites = amendment["prerequisites"]
        self.state["source"].update(predecessor_contract_sha256=CONTRACT_SHA256, predecessor_packet_sha256=CONTRACT_PACKET, image_amendment_sha256=AMENDMENT_SHA256, image_amendment_packet_sha256=AMENDMENT_PACKET, image_source_review_packet_sha256=SOURCE_REVIEW_PACKET, execution_amendment_sha256=EXECUTION_SHA256, execution_amendment_packet_sha256=EXECUTION_PACKET)
        self.state["source"].update(predecessor_product_files=177, predecessor_product_tree_digest_sha256=FROZEN_PRODUCT_DIGEST, fixture_amendment_sha256=FIXTURE_SHA256, fixture_amendment_packet_sha256=FIXTURE_PACKET, fixture_review_packet_sha256=FIXTURE_REVIEW_PACKET, fixture_preformat_source_digest_sha256=FIXTURE_SOURCE_DIGEST, format_amendment_sha256=FORMAT_SHA256, format_amendment_packet_sha256=FORMAT_PACKET)
        self.persist()
        (self.output / "selected-contract-metadata.tar").write_bytes(source_tar(metadata))
        write_json(self.output / "host.json", {"uname": list(os.uname()), "python": sys.version, "netns": os.readlink("/proc/self/ns/net"), "runner": "ubuntu-24.04", "github_run_id": self.run_id, "attempt": self.attempt})
        self.command(["git", "--version"])
        self.command(["docker", "version", "--format", "{{json .}}"])
        # Both pulls are completed before any preparation container is created.
        for role in ("test", "pg"):
            image = IMAGES[role]
            self.command(["docker", "pull", "--platform", "linux/amd64", image["ref"]], 120)
            inspected, _, _ = self.command(["docker", "image", "inspect", image["ref"]])
            rows = json.loads(inspected)
            require(len(rows) == 1, "image inspect count")
            validate_image_inspect(role, rows[0])
            write_json(self.output / (role + "-image.json"), rows[0])
        helpers = {"collector-prerequisites.exs": PREREQUISITES_EXS.encode(), "collector-bootstrap.exs": BOOTSTRAP_EXS.encode(), "collector-manifest.exs": MANIFEST_EXS.encode(), "collector-netns.exs": NETNS_EXS.encode(), "collector-observer.exs": OBSERVER_EXS.encode(), "collector-mounts.exs": MOUNTS_EXS.encode(), "frozen-manifest.json": json.dumps(BUILD_CLOCK_MANIFEST, sort_keys=True, separators=(",", ":")).encode()}
        write_json(self.output / "literal-helper-bindings.json", {path: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for path, body in helpers.items()})
        (self.output / "literal-helpers.tar").write_bytes(source_tar(helpers))
        prepare = self.create("prepare")
        validate_container_environment("prepare", self.inspect(prepare))
        self.docker(prepare, ["start"])
        self.copy_in(prepare, source_tar({**product, **helpers}))
        self.observe_mounts(prepare)
        prerequisite_output, _, _ = self.execute(prepare, ["/usr/local/bin/elixir", "/workspace/collector-prerequisites.exs"])
        write_json(self.output / "prepare-prerequisites.json", validate_prerequisites(json_marker(prerequisite_output), self.prerequisites))
        write_json(self.output / "bootstrap-plan.json", {"argv": ["/usr/local/bin/elixir", "/workspace/collector-bootstrap.exs"], "tool_destination": BASE_ENV["MIX_REBAR3"], "helper_sha256": hashlib.sha256(BOOTSTRAP_EXS.encode()).hexdigest(), "download_bytes_each": 16777216, "download_seconds_each": 25, "no_package_install_or_fallback": True})
        bootstrap, _, _ = self.execute(prepare, ["/usr/local/bin/elixir", "/workspace/collector-bootstrap.exs"], 60)
        bootstrap_result = json_marker(bootstrap)
        validate_rebar_transfer(bootstrap_result.get("rebar_transfer"), bootstrap_result.get("rebar"))
        write_json(self.output / "bootstrap-observed.json", bootstrap_result)
        for tool, path, filename in (("hex", "/workspace/downloads/hex.ez", "bootstrap-hex-2.5.1.ez"), ("rebar", "/workspace/tooling/rebar3", "bootstrap-rebar-3.28.0")):
            artifact = self.copy_file_out(prepare, path, 16777216)
            validate_bootstrap_export(tool, artifact, bootstrap_result[tool]["bytes"])
            (self.output / filename).write_bytes(artifact)
        self.execute(prepare, ["/usr/local/bin/mix", "deps.get", "--check-locked"], 120)
        manifest_output, _, _ = self.execute(prepare, ["/usr/local/bin/elixir", "/workspace/collector-manifest.exs", "archive-list"])
        prepared_manifest = json_marker(manifest_output)
        require(prepared_manifest["source"] == BUILD_CLOCK_MANIFEST, "prepare source changed")
        write_json(self.output / "prepared-manifest.json", prepared_manifest)
        self.execute(prepare, ["/usr/bin/tar", "--format=ustar", "--sort=name", f"--mtime=@{PREPARED_MTIME}", "--owner=0", "--group=0", "--numeric-owner", "--no-recursion", "-cf", "/workspace/prepared.tar", "-C", "/workspace", "-T", "/workspace/archive-files.txt"], 30)
        prepared = self.copy_file_out(prepare, "/workspace/prepared.tar", MAX_ARCHIVE_BYTES)
        validate_prepared_archive(prepared, prepared_manifest)
        (self.output / "prepared-source-dependencies-tools.tar").write_bytes(prepared)
        self.stop_remove(prepare)  # No networked namespace remains at test creation.
        require(prepare.state == "removed", "prepare removal missing")
        require(not self.state.get("qualification_failures"), "preparation terminal runtime failure")
        test = self.create("test")
        validate_container_environment("test", self.inspect(test))
        self.docker(test, ["start"])
        self.copy_in(test, prepared)
        self.observe_mounts(test)
        self.execute(test, ["/usr/local/bin/elixir", "-e", 'for path <- ["/workspace/home", "/workspace/tooling/hex", "/workspace/cache", "/workspace/evidence", "/workspace/evidence/identity"], do: File.mkdir!(path)'])
        actual_prerequisites, _, _ = self.execute(test, ["/usr/local/bin/elixir", "/workspace/collector-prerequisites.exs"])
        write_json(self.output / "test-prerequisites.json", validate_prerequisites(json_marker(actual_prerequisites), self.prerequisites))
        restored_output, _, _ = self.execute(test, ["/usr/local/bin/elixir", "/workspace/collector-manifest.exs"])
        restored = json_marker(restored_output)
        validate_source_unchanged(prepared_manifest, restored)
        host_netns = os.readlink("/proc/self/ns/net")
        namespace_output, _, _ = self.execute(test, ["/usr/local/bin/elixir", "/workspace/collector-netns.exs"])
        namespace = validate_namespace(json_marker(namespace_output), host_netns)
        write_json(self.output / "test-namespace.json", namespace)
        pg = self.create("pg", test.cid)
        validate_container_environment("pg", self.inspect(pg))
        self.docker(pg, ["start"])
        pg_netns, _, _ = self.execute(pg, ["/usr/bin/readlink", "/proc/self/ns/net"], environment=PG_ENV)
        require(pg_netns.decode().strip() == namespace["netns"], "PostgreSQL namespace differs from exact test namespace")
        pg_version, _, _ = self.execute(pg, ["/usr/lib/postgresql/16/bin/postgres", "--version"], environment=PG_ENV)
        require(b"PostgreSQL) 16.15" in pg_version, "PostgreSQL executable version mismatch")
        ready_until = time.monotonic() + min(30, self.budget.remaining(30))
        ready = False
        while time.monotonic() < ready_until:
            _, _, result = self.execute(pg, ["/usr/lib/postgresql/16/bin/pg_isready", "-h", "127.0.0.1", "-U", "mixer_fixture", "-d", "mixer_startup_test", "-t", "1"], min(3, max(.01, ready_until - time.monotonic())), environment=PG_ENV, check=False)
            if result == 0:
                ready = True
                break
            require(result in {1, 2}, "PostgreSQL readiness error")
            time.sleep(min(.25, max(0, ready_until - time.monotonic())))
        require(ready and time.monotonic() <= ready_until, "PostgreSQL readiness bound reached")
        sql = "SELECT json_build_object('server_version_num',current_setting('server_version_num'),'timezone',current_setting('TimeZone'),'database',current_database(),'databases',(SELECT json_agg(datname ORDER BY datname) FROM pg_database));"
        database = self.pg_query(pg, sql)
        require(database == {"server_version_num": "160015", "timezone": "UTC", "database": "mixer_startup_test", "databases": ["mixer_startup_test", "postgres", "template0", "template1"]}, "private PostgreSQL scope/version mismatch")
        write_json(self.output / "database-before.json", database)
        status, _, _ = self.execute(pg, ["/usr/bin/cat", "/proc/1/status"], environment=PG_ENV)
        uid = next((line.split()[1:] for line in status.decode().splitlines() if line.startswith("Uid:")), [])
        require(len(uid) == 4 and all(value.isdigit() and int(value) > 0 for value in uid), "PostgreSQL remains root")
        write_json(self.output / "postgres-process.json", {"namespace": pg_netns.decode().strip(), "uid_fields": uid, "version": pg_version.decode()})
        offline_until = time.monotonic() + min(180, self.budget.remaining(180))
        def offline_timeout():
            left = offline_until - time.monotonic()
            require(left > 0, "offline compile/two-test phase aggregate bound reached")
            return left
        self.execute(test, ["/usr/local/bin/mix", "deps.compile"], offline_timeout())
        self.execute(test, ["/usr/local/bin/mix", "compile", "--warnings-as-errors"], offline_timeout())
        before_output, _, _ = self.execute(test, ["/usr/local/bin/elixir", "/workspace/collector-manifest.exs"], min(15, offline_timeout()))
        before_tests = json_marker(before_output)
        write_json(self.output / "before-tests-manifest.json", before_tests)
        generated = self.capture_generated_dag(test, before_tests.get("deps", {}).get(GENERATED_DAG_PATH), min(15, offline_timeout()))
        require(time.monotonic() <= offline_until, "offline phase deadline exceeded during generated DAG capture")
        validate_compiled_source_unchanged(prepared_manifest, before_tests)
        write_json(self.output / "compiled-input-validation.json", {"prepared_manifest_sha256": canonical_digest(prepared_manifest), "compiled_manifest_sha256": canonical_digest(before_tests), "prepared_inputs_unchanged": True, "generated_output": generated, "generated_output_was_absent_before_compile": True, "remaining_dependency_entries_unchanged": True, "artifact_contents_interpreted_or_executed": False})
        compiled_output, _, _ = self.execute(test, ["/usr/local/bin/elixir", "-e", 'rows = Map.new(Path.wildcard("/workspace/hosted/_build/test/lib/*/ebin/*.beam"), fn path -> {path, Base.encode16(:crypto.hash(:sha256, File.read!(path)), case: :lower)} end); true = map_size(rows) > 0; IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(rows)))'], min(15, offline_timeout()))
        write_json(self.output / "compiled-modules-before-tests.json", json_marker(compiled_output))
        validate_container_environment("test", self.inspect(test))
        validate_container_environment("pg", self.inspect(pg))
        fresh_namespace, _, _ = self.execute(test, ["/usr/local/bin/elixir", "/workspace/collector-netns.exs"], min(15, offline_timeout()))
        validate_namespace(json_marker(fresh_namespace), host_netns)
        # The flag is constructed here only, after actual source/tool/isolation checks.
        flag_env = {**TEST_ENV, "MIXER_ISOLATED_NETNS": "1"}
        write_json(self.output / "test-authorization.json", {"allowed_environment": flag_env, "owned_test_cid": test.cid, "owned_pg_cid": pg.cid, "actual_namespace": namespace["netns"], "source_unchanged": True, "generated_output": generated, "prerequisites_observed": True, "mount_policy_observed": True, "assertions_before_flag": True})
        argv = ["/usr/local/bin/elixir", "-r", "/workspace/collector-observer.exs", "-S", "mix", "test", "--warnings-as-errors", "--seed", "0", "--trace", "--no-color", "--formatter", "ExUnit.CLIFormatter", "--formatter", "MixerIdentityNetworkCollector.Observer", *TEST_ROOTS]
        _, _, test_exit = self.execute(test, argv, offline_timeout(), environment=flag_env, check=False)
        require(time.monotonic() <= offline_until, "offline phase deadline exceeded")
        events_bytes = self.copy_file_out(test, "/workspace/evidence/events.jsonl", 2097152)
        (self.output / "observer-events.jsonl").write_bytes(events_bytes)
        semantic = {}
        for name in SEMANTICS:
            body = self.copy_file_out(test, "/workspace/evidence/identity/" + name)
            (self.output / name).write_bytes(body)
            semantic[name] = json.loads(body)
        runtime_body = self.copy_file_out(test, "/workspace/evidence/runtime.json")
        (self.output / "loaded-runtime.json").write_bytes(runtime_body)
        runtime = json.loads(runtime_body)
        require(runtime.get("elixir") == "1.20.4" and runtime.get("otp_patch") == "29.1.1" and "x86_64" in runtime.get("architecture", ""), "observed test VM identity mismatch")
        require(any(row.get("module") == "Elixir.MixerHosted.Identity.KeyOwner" and row.get("sha256") and row.get("path", "").startswith("/workspace/hosted/_build/test/") for row in runtime.get("modules", [])), "loaded product module identity missing")
        events = [json.loads(line) for line in events_bytes.splitlines()]
        result = validate_events(events, test_exit, semantic)
        after_output, _, _ = self.execute(test, ["/usr/local/bin/elixir", "/workspace/collector-manifest.exs"])
        after_tests = json_marker(after_output)
        validate_source_unchanged(before_tests, after_tests)
        write_json(self.output / "after-tests-manifest.json", after_tests)
        keydirs, _, _ = self.execute(test, ["/usr/local/bin/elixir", "-e", 'dirs = Path.wildcard("/tmp/mixer-key-owner-tls-*"); IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(%{"remaining_key_directories" => dirs})))'])
        key_evidence = json_marker(keydirs)
        require(key_evidence == {"remaining_key_directories": []}, "synthetic key directories remain")
        write_json(self.output / "key-directory-cleanup.json", key_evidence)
        applied = self.pg_query(pg, "SELECT json_agg(version ORDER BY version) FROM schema_migrations;")
        expected_migrations = sorted(int(PurePosixPath(path).name.split("_")[0]) for path in BUILD_CLOCK_MANIFEST if path.startswith("hosted/priv/repo/migrations/") and path.endswith(".exs"))
        require(applied == expected_migrations, "actual selected migrations differ")
        write_json(self.output / "applied-migrations.json", {"database": "mixer_startup_test", "versions": applied})
        self.state["test_result"] = result
        self.state["limitations"] = ["Ordinary remote synthetic fixture scope only; no syscall/child-command custody trace", "Existing TLSFixture discards successful OpenSSL child output; executable/parent trace/assertions retained", "No real provider/browser/Neon/Cloudflare/native/physical/GA qualification", "No new production release/exclusion run; root must separately accept exact unchanged-product evidence reuse", "Host loss/hard cancellation can prevent cleanup or upload; missing evidence is unqualified", "Independent root artifact download, digest validation and acceptance remain required"]
        self.persist()

    def pg_query(self, pg, sql):
        output, _, _ = self.execute(pg, ["/usr/lib/postgresql/16/bin/psql", "--no-psqlrc", "--set", "ON_ERROR_STOP=1", "--host", "127.0.0.1", "--username", "mixer_fixture", "--dbname", "mixer_startup_test", "--tuples-only", "--no-align", "--command", sql], environment=PG_ENV)
        return json.loads(output)


# Frozen ordinary product blobs; collector/control source is separately bound.
PREDECESSOR_MANIFEST = {'hosted/.formatter.exs': {'bytes': 74,
                           'sha256': '0d5f1f1bc0a4d678629084c6f15f96e000b4882594bc829f2adf5eacc9ff42b5'},
 'hosted/.gitignore': {'bytes': 40,
                       'sha256': '363721e50c7313c16377d1d426ffbef80e6a0ff5943fb500c4a6f96917f336e5'},
 'hosted/.tool-versions': {'bytes': 35,
                           'sha256': '6286da51456f864e5f1d8f2280e6de86d6fb1ee4517c40819760ec54d203c846'},
 'hosted/README.md': {'bytes': 4195,
                      'sha256': 'b9e4e05d585bc493d40ff5c5843d9a911667656710087705650622fd79d0c663'},
 'hosted/config/config.exs': {'bytes': 431,
                              'sha256': '6510b5e0f5eecb2ced799250d7bdcef91b8f8278e19e2c886c60dd624443005c'},
 'hosted/config/runtime.exs': {'bytes': 549,
                               'sha256': '73cd8edac21bb64c3fba3cd81bb461f2cee651b9f799bd42bfac3e5ffeca6e9f'},
 'hosted/lib/mixer_hosted/application.ex': {'bytes': 1278,
                                            'sha256': 'bbf02752b982e1437564c266772cd4e5dd7190670a575dd6676dda7fc692803f'},
 'hosted/lib/mixer_hosted/audit/customer_artifact_event.ex': {'bytes': 17388,
                                                              'sha256': '6e8450558d71af3d0940e7ca7a5725f7bdbc1ad834f4619f9008d8d196976942'},
 'hosted/lib/mixer_hosted/audit/upload_event.ex': {'bytes': 12893,
                                                   'sha256': 'daff6c6084be7094bc1a2b97ae386d5fcd4390e245c99f6de77f09572c07f6ad'},
 'hosted/lib/mixer_hosted/authorization.ex': {'bytes': 4183,
                                              'sha256': 'ac5b8a0ed8edc40598d8b02036066460fa8ce7d4cb55abbd05229d18a18a10d3'},
 'hosted/lib/mixer_hosted/authorization/artifact_read.ex': {'bytes': 7879,
                                                            'sha256': 'e5b5760c7d81204d9e2ca6a9bf89b1317e8dbbb2353ae39c9171b17e9bd44ef0'},
 'hosted/lib/mixer_hosted/authorization/policy.ex': {'bytes': 14476,
                                                     'sha256': '53a60ab1055d82d3bfc3e89bf67925b190fb3f6feb5a9e326a58b935b78f94d1'},
 'hosted/lib/mixer_hosted/authorization/postgres/evidence.ex': {'bytes': 6737,
                                                                'sha256': 'fe5e34d6e66b84aa6f4786c7922eeb75faf5d2b142de82d17f184b5b08fff1f7'},
 'hosted/lib/mixer_hosted/authorization/postgres/session.ex': {'bytes': 6489,
                                                               'sha256': '8ae27291a2e0777dfde6f995cf8c1a64c6ac8e2e7b0e7660afdb7cac76382727'},
 'hosted/lib/mixer_hosted/authorization/postgres_repository.ex': {'bytes': 3112,
                                                                  'sha256': '78b77db112d0fb45e0bd645e91049daf016867f5086a4c07d373b7e88fab384b'},
 'hosted/lib/mixer_hosted/authorization/repository.ex': {'bytes': 3591,
                                                         'sha256': '76a24ec22292193f5d1ba26ad17711645662939db2b8fe988ea84b3614d1de00'},
 'hosted/lib/mixer_hosted/authorization/scope.ex': {'bytes': 2264,
                                                    'sha256': 'b98c7c6f2f3592bf2fcfd0890d86bb503e3c9cdd6558fa1c7b0766ddb61c7b7a'},
 'hosted/lib/mixer_hosted/authorization/transaction/context.ex': {'bytes': 6912,
                                                                  'sha256': '36c10584932aca726e855891f8c7ef54e35a19625a922cc779fe0eb6238b0bfc'},
 'hosted/lib/mixer_hosted/authorization/transaction/snapshot.ex': {'bytes': 12313,
                                                                   'sha256': '39bae74a8022ea9884874f8e457568a073fd798fa87ebf901e9b896062528599'},
 'hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex': {'bytes': 7827,
                                                            'sha256': 'a420d5a54868d61c3d6e9c7cb41807698eb729df3e6babda12135a727ac657ea'},
 'hosted/lib/mixer_hosted/billing/webhook_signature.ex': {'bytes': 4549,
                                                          'sha256': '3fa0a2d8bee3e4eb9a4204857aaec0d16565df7c0d3f0aa8062158d51f2e3cb6'},
 'hosted/lib/mixer_hosted/billing/webhook_transport.ex': {'bytes': 22396,
                                                          'sha256': '56a26cf3a56f3e5a5b2d8f5104fc7c3371b0e44918b007197be5871cf94ef1a5'},
 'hosted/lib/mixer_hosted/browser_auth/activation_preparation.ex': {'bytes': 2543,
                                                                    'sha256': 'e208e159719dd29ff75186667404cb6018391a2ecc3b8a3534db131d1bc281f5'},
 'hosted/lib/mixer_hosted/browser_auth/activation_preparation_schema.ex': {'bytes': 19706,
                                                                           'sha256': 'd58bc6009d6118ba9469f087af99e893df6a99038cdccec11ba5048d48bf4ae8'},
 'hosted/lib/mixer_hosted/browser_auth/catalog.ex': {'bytes': 23235,
                                                     'sha256': '6d568887deabc3d573462b7ecd038444bc07e985ee4a9e1f32e6fb4a3ef268af'},
 'hosted/lib/mixer_hosted/browser_auth/catalog_manifest.ex': {'bytes': 3589,
                                                              'sha256': '3508c85922a1a716d39eb61ecb5daa699d6141b1aeb88a9565512c78465d1269'},
 'hosted/lib/mixer_hosted/browser_auth/catalog_manifest_v2.ex': {'bytes': 4450,
                                                                 'sha256': '0c4e4c0186a57979182b90eb4b6e852b8b2b40d9e894bede0e95e382dfc7a8ea'},
 'hosted/lib/mixer_hosted/browser_auth/config.ex': {'bytes': 8033,
                                                    'sha256': 'f9e9f1cac7083fbcb282c4a150e65a646228f005522a0b212e602b6495ab588d'},
 'hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex': {'bytes': 2813,
                                                                  'sha256': 'a2166f04006293598fcb073a2f8e90170a839c2b5d0cc3ecb754bfd8c4d41532'},
 'hosted/lib/mixer_hosted/browser_auth/custody.ex': {'bytes': 1515,
                                                     'sha256': '675429fa3daf5c84cf8ee8223aeeea6842889af859a6468c763ffc0ea6033803'},
 'hosted/lib/mixer_hosted/browser_auth/lifecycle_repo.ex': {'bytes': 1683,
                                                            'sha256': '66c27f0cac41d04b754532df397ace17370436af7b68707d0d8216dddc4918f9'},
 'hosted/lib/mixer_hosted/browser_auth/preauth_draft.ex': {'bytes': 1569,
                                                           'sha256': '143f34f3c0810e290b4ccfa4460b86fee0482b33573a6fc604aeeac27498cbbd'},
 'hosted/lib/mixer_hosted/browser_auth/protocol.ex': {'bytes': 10422,
                                                      'sha256': 'a569cabebfd905f1f717137b9180ff5ae47fffb747a9b5e45f049f03b3da3428'},
 'hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex': {'bytes': 47573,
                                                              'sha256': 'f71d79b92065d2137363f10de89c137b95ce5758b0e4c21b88faaeb8a779fcfc'},
 'hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex': {'bytes': 1463,
                                                               'sha256': '6e6fd520d4b3e37af2d4c3c5cd4c40caf7a1cadc473baed6246db05a49df35da'},
 'hosted/lib/mixer_hosted/browser_auth/runtime_config.ex': {'bytes': 7874,
                                                            'sha256': '0ce7e28450b7f5652313fc22cb909ea6e65cc8b4a8edcc960669d5a950da0962'},
 'hosted/lib/mixer_hosted/browser_auth/runtime_owner.ex': {'bytes': 20613,
                                                           'sha256': '007ab3e8445820318ed503337b0c2693d0e703227eb8b0202d21cd1330666580'},
 'hosted/lib/mixer_hosted/browser_auth/storage_schema.ex': {'bytes': 63975,
                                                            'sha256': '676bb977bbe4c322caf63c1a5f40d86e7861847636029948b55cb01f6dedb6dd'},
 'hosted/lib/mixer_hosted/browser_auth/store.ex': {'bytes': 20860,
                                                   'sha256': '6c02fff8454790449b3ebe70695fc3adfd537d899b24411ee6585171578c8e43'},
 'hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex': {'bytes': 9927,
                                                             'sha256': 'ce92f99c3990bf9ddd0fbf5d8c7d329ea63bb5dc31ec3df4922907b19986cd3e'},
 'hosted/lib/mixer_hosted/browser_auth/vault.ex': {'bytes': 10754,
                                                   'sha256': 'e376cdd7305a520c61e716e3f4fcd3f5493e280ff5424ba822516f9a6f4281b2'},
 'hosted/lib/mixer_hosted/builds/admission.ex': {'bytes': 26456,
                                                 'sha256': '87bd56955fa99c2978a407c74cfcc87819ac6059a0bc4a86a36df763424ab0eb'},
 'hosted/lib/mixer_hosted/builds/coordinator.ex': {'bytes': 12726,
                                                   'sha256': '1bf162cb617c8a62262c82d8a7038214bd7d229762ced511c2c33d082493e0b3'},
 'hosted/lib/mixer_hosted/builds/dispatch.ex': {'bytes': 3130,
                                                'sha256': 'a535e02f8d4a9ebf8a6c9be5a5ba89b09de0192f8987e2e9ac520af206fcb753'},
 'hosted/lib/mixer_hosted/builds/journal.ex': {'bytes': 18098,
                                               'sha256': '3386d7338d189ffc9bdd97ea9669d9c66569ec300e94154b69e14dafd41053ea'},
 'hosted/lib/mixer_hosted/builds/lifecycle.ex': {'bytes': 19409,
                                                 'sha256': '514eac8d0fd2300e6e9506a8b0f4c6c5d77d20e930982e723ce0ee8227c9bc32'},
 'hosted/lib/mixer_hosted/builds/record.ex': {'bytes': 463,
                                              'sha256': '4394feecd6e04eba55e6aec6d3cde832a14616d0ff10a9682700477ad11930c2'},
 'hosted/lib/mixer_hosted/builds/storage.ex': {'bytes': 9880,
                                               'sha256': 'f078d7f113f50e2705c6e4083b16a7b382a509fe0225977f43f339e4cc7b1685'},
 'hosted/lib/mixer_hosted/customer_artifacts.ex': {'bytes': 7971,
                                                   'sha256': 'f9143a77e6357720fcca3731d5fcd5dd63458a0fe48807ba992698d6b43f03be'},
 'hosted/lib/mixer_hosted/customer_artifacts/postgres_storage.ex': {'bytes': 18055,
                                                                    'sha256': 'b6e9fcd0c3df4f28b6da90589eb2d3c465780c4f8ec484ace74f893aeb216340'},
 'hosted/lib/mixer_hosted/customer_artifacts/schema.ex': {'bytes': 36518,
                                                          'sha256': '5bd58744af4823374cc9a981b0699dc16c7d88f37bc8077a40b509cdf5426a19'},
 'hosted/lib/mixer_hosted/customer_artifacts/topology.ex': {'bytes': 8906,
                                                            'sha256': '35b4cc8f6a91b9b5049dae2ae50d2c056f4066b5c4e88d2e4115d252c137f4cc'},
 'hosted/lib/mixer_hosted/customer_workspace.ex': {'bytes': 1108,
                                                   'sha256': 'ea897c99ee520bc57d9dfd086ff7e102b042d2750d91f404561bdc048ebcf8e6'},
 'hosted/lib/mixer_hosted/customer_workspace/input.ex': {'bytes': 3780,
                                                         'sha256': '0ede3d8032b9703375f4d4bddd35567979ab8b454278eaaf4adfb8ca91c45fbc'},
 'hosted/lib/mixer_hosted/customer_workspace/storage.ex': {'bytes': 16295,
                                                           'sha256': '3ca97ed522b3d088dd098829d27dbd9c81bfb52c399dcf4efd3e377d121c5e34'},
 'hosted/lib/mixer_hosted/identity/access_token_verifier.ex': {'bytes': 5090,
                                                               'sha256': '1c17efc4b1a7c9befed39e312fdd3d06f89f4c64a0befbfb7c1cc9a9049d5dcb'},
 'hosted/lib/mixer_hosted/identity/admission.ex': {'bytes': 2723,
                                                   'sha256': 'f1a0ea0420a644b06f93910cbf807171e1978b2b0adf6c4186b203bf377a6d85'},
 'hosted/lib/mixer_hosted/identity/bounded_json.ex': {'bytes': 1662,
                                                      'sha256': '6f2dfd7ec4c6b85e25e61feb53cc26591129ca484b308ee1d49497fe695eb2e6'},
 'hosted/lib/mixer_hosted/identity/bounded_tcp.ex': {'bytes': 4128,
                                                     'sha256': '26e3f47841c99c0b5558317c84b21ab5b1ab77d049518a2df935cab221940529'},
 'hosted/lib/mixer_hosted/identity/configured_verifier.ex': {'bytes': 2377,
                                                             'sha256': 'd138c83981d0e0a01c27164fbe74c54635a0947254726a122253f8b2b752f35c'},
 'hosted/lib/mixer_hosted/identity/dns_resolver.ex': {'bytes': 3061,
                                                      'sha256': 'aec030a7fc368764230f078155dc2ff29137ec5a19590bc2a2a3a785d0a39567'},
 'hosted/lib/mixer_hosted/identity/encoding.ex': {'bytes': 745,
                                                  'sha256': '565338c3669fb9578e086510d6f7d06135958049c918a7df3f3558474e8e01f4'},
 'hosted/lib/mixer_hosted/identity/fetch_flight.ex': {'bytes': 6097,
                                                      'sha256': 'ca91467ac1d9011f26ff59382c996ee6186ea8daa789e64ead926a2392a60cf4'},
 'hosted/lib/mixer_hosted/identity/global_address.ex': {'bytes': 1807,
                                                        'sha256': 'd28fca0c87120f56e5e40d6ea5bb716a0f765f9e50fb500788233194c0aa74f6'},
 'hosted/lib/mixer_hosted/identity/http_freshness.ex': {'bytes': 3551,
                                                        'sha256': '43d49b9704c9f6698bf585f9495c877c37f5645a41a8133e31d5fbde50d77863'},
 'hosted/lib/mixer_hosted/identity/http_wire_guard.ex': {'bytes': 5575,
                                                         'sha256': 'cab3b7048e3572420c907acae4ec3445717dee0e62e554dec39fa9d4c0b0fa2e'},
 'hosted/lib/mixer_hosted/identity/jwks_transport.ex': {'bytes': 6140,
                                                        'sha256': 'f4e3a77d02c7a85a34223b60bc457821100769bef86e6f8102f0ba91279f02a4'},
 'hosted/lib/mixer_hosted/identity/key_owner.ex': {'bytes': 15903,
                                                   'sha256': 'd5d98bec506ad418c37fc36097d2cf714261c3f644875bf2bf93b4360adefe5d'},
 'hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex': {'bytes': 1072,
                                                              'sha256': 'cdb7b901a8e521361e1578bf0b47ea521a31c61c681c27d1f164925081238ba2'},
 'hosted/lib/mixer_hosted/identity/manifest.ex': {'bytes': 3157,
                                                  'sha256': '4b12b89c3b39177c295f68050aba84dcb2e5ae62421b3ebd4810526d125a30b4'},
 'hosted/lib/mixer_hosted/identity/startup_config.ex': {'bytes': 5214,
                                                        'sha256': '0c9b11693d34880ca9e9c05fba95e1f3994a0eadd7189a5fde2f65b036ff4d50'},
 'hosted/lib/mixer_hosted/identity/trust_snapshot.ex': {'bytes': 5390,
                                                        'sha256': '5bce1be5dc33155669f30e615bb5ef8c61c41488072608df14b963dfc3edb1f9'},
 'hosted/lib/mixer_hosted/identity/verified_identity.ex': {'bytes': 1098,
                                                           'sha256': '02ea302abedbf10555792ae5284f8eb41113edd11bc83c3e869bdbee7b68ae4d'},
 'hosted/lib/mixer_hosted/identity/verifier.ex': {'bytes': 559,
                                                  'sha256': '713a64a0bba94b6a1d4e5c8e55dada8807ca1256000b5c62b36fc3b493574a9e'},
 'hosted/lib/mixer_hosted/protocol/artifact_admission.ex': {'bytes': 6176,
                                                            'sha256': '8a4712fbfe92f70d4c27466d5f2cd4ff9d720e60208029563ca94aa3590d0cbb'},
 'hosted/lib/mixer_hosted/protocol/artifact_cbor.ex': {'bytes': 5343,
                                                       'sha256': '518f5a23b7c6a266c2b0837355446ad6d326cfcd0f5cfd9b0120ea4e851caaa6'},
 'hosted/lib/mixer_hosted/protocol/artifact_json.ex': {'bytes': 5805,
                                                       'sha256': 'c17a68db3eac6f2c018612df536b100de7378c74f5dd2f9dd6d6c1e9d42d2957'},
 'hosted/lib/mixer_hosted/protocol/artifact_v3_policy.ex': {'bytes': 8214,
                                                            'sha256': '13ddbe90a6942bf05311d58270786bcfb4def75107b6d6377fd451b1e2121a3a'},
 'hosted/lib/mixer_hosted/repo.ex': {'bytes': 107,
                                     'sha256': '034e56f300c8677adc71cee8b63d86825588cbc26a9ec155d9670cbd0a5329ec'},
 'hosted/lib/mixer_hosted/runtime_config.ex': {'bytes': 4199,
                                               'sha256': 'e3b8ab88ae4c12788b09d470a71d051bd817ee919db5fe6281054231d38f0286'},
 'hosted/lib/mixer_hosted_web/browser_workspace_dispatcher.ex': {'bytes': 4531,
                                                                 'sha256': '49f87b855412261a0bf705d7c9ba5f37048ee3918fe092e754380fa974faff17'},
 'hosted/lib/mixer_hosted_web/browser_workspace_dispatcher/capture_adapter.ex': {'bytes': 1514,
                                                                                 'sha256': 'a8ebc637dc3ac4ffad016b31c5e093dd953de86ae5042788ef82bcb0b973b921'},
 'hosted/lib/mixer_hosted_web/browser_workspace_dispatcher/request.ex': {'bytes': 1377,
                                                                         'sha256': 'abdeae66e37e3ca015244433c5947dcb9b91f6e0ee847090ff5de80ebfc0cf2a'},
 'hosted/lib/mixer_hosted_web/customer_artifact_controller.ex': {'bytes': 3649,
                                                                 'sha256': '1597d793de5b78f6f02094535989b240210747e74ac9b86c5ecd82134cefabdf'},
 'hosted/lib/mixer_hosted_web/customer_workspace_controller.ex': {'bytes': 4455,
                                                                  'sha256': '3035b60c297c1da6665d013f668d48a1ed09433936eab5d22938c06885d63b64'},
 'hosted/lib/mixer_hosted_web/endpoint.ex': {'bytes': 160,
                                             'sha256': '7702c86f462af84fb6ac157d700d1a22352f2eaf117e31565f672dd533313d08'},
 'hosted/lib/mixer_hosted_web/error_json.ex': {'bytes': 187,
                                               'sha256': 'c850deb7ae7656cc8d895cc7dbfb1753b7f13e563f16987677cebc5169bd9915'},
 'hosted/lib/mixer_hosted_web/health_controller.ex': {'bytes': 221,
                                                      'sha256': 'f3bb0776dd5015aae029b76c73784254daf831c53d06d20f0ec10103e3fc72cb'},
 'hosted/lib/mixer_hosted_web/plugs/bearer_identity.ex': {'bytes': 10884,
                                                          'sha256': '4bb4964827578fe373b64705bce74807191551cc8f870041f11da907a7ef249a'},
 'hosted/lib/mixer_hosted_web/plugs/customer_artifact_request.ex': {'bytes': 13467,
                                                                    'sha256': '40b39e38f8c3ecdcb36ba006ee0517303a690246c029d1cc6d42b00a5fbf9a1b'},
 'hosted/lib/mixer_hosted_web/plugs/customer_workspace_request.ex': {'bytes': 11149,
                                                                     'sha256': 'bc1cd4244d436dbf8bd769ed03fc5baf28939661604648434d157c47ed504d3c'},
 'hosted/lib/mixer_hosted_web/router.ex': {'bytes': 938,
                                           'sha256': '71ae9d8a07c2559a76773b2228d740e006315899536866d9ea79ebbbaade256c'},
 'hosted/mix.exs': {'bytes': 1270,
                    'sha256': 'bf32132975d04d66315974a6a5ef0bc9d9718b6392824d92bbc8e9d764062f0d'},
 'hosted/mix.lock': {'bytes': 7964,
                     'sha256': '1eada39dcaf4863d02d39f51e218d2bad8908b36a0cba47ff2d16037b7bcf837'},
 'hosted/priv/browser_auth/relation_surface_v1_pg16.json': {'bytes': 132435,
                                                            'sha256': '079b8cdeb3c039284b3ae402664230f6abc01782ab5e7f08219a06067e22cadf'},
 'hosted/priv/browser_auth/relation_surface_v1_pg17.json': {'bytes': 132435,
                                                            'sha256': '100df9346930b778611b46e821484db025671819b3bb966cfcb496014ce42785'},
 'hosted/priv/repo/migrations/20261024000000_add_oban.exs': {'bytes': 168,
                                                             'sha256': 'c4cd9451f54eb37da9d357f8cc451dc0188134799fa5c359d754c07208bb6b3e'},
 'hosted/priv/repo/migrations/20261025000000_add_build_journals.exs': {'bytes': 1562,
                                                                       'sha256': '9d848ba6c781cd018aca43989313e78320b5e970da7fc4c863a1da644a16d7f2'},
 'hosted/priv/repo/migrations/20261025000001_add_build_admission.exs': {'bytes': 2880,
                                                                        'sha256': '67da842fb971ace6081c8287792acc1cc5bcb2be630dcad1fcf54b4eae2a87bb'},
 'hosted/priv/repo/migrations/20261025000002_add_build_aggregate_limits.exs': {'bytes': 2572,
                                                                               'sha256': '443ede59186c0fca9454bcec319965217007c328719dbb152bdf6552901e009b'},
 'hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs': {'bytes': 12665,
                                                                               'sha256': '110997b341449a04135296b000c6434f84526305c2f70c16b1e51f38dffc3f6c'},
 'hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs': {'bytes': 805,
                                                                                      'sha256': '5248990524d1c2504847fdff2f107a952d850acf8ff5fcdb8e7b0ef77e38bcd7'},
 'hosted/priv/repo/migrations/20261025000005_add_customer_artifact_storage.exs': {'bytes': 1967,
                                                                                  'sha256': '35e00750436666e22ee4a483848b9fca4fa33fa39b529dd39d27b940f0d0f681'},
 'hosted/priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs': {'bytes': 7652,
                                                                                     'sha256': '43140162ceaf87b58bcdcdf820a9b95b7ae465a873193ac61c7a725a18bde875'},
 'hosted/priv/repo/migrations/20261025000007_add_browser_sessions.exs': {'bytes': 435,
                                                                         'sha256': '577b38e600c55e9844bc393ccfe4dfdfb7241db7eaed449956e6a3335442710f'},
 'hosted/priv/repo/migrations/20261025000008_add_browser_activation_preparation.exs': {'bytes': 460,
                                                                                       'sha256': 'efcd051a07ea3cdb4e294bd3d205a2e87d6354cd9b8b6f4adbb4b11bf44007d0'},
 'hosted/scripts/dependency-inventory.exs': {'bytes': 501,
                                             'sha256': 'ed9cb6ec066742d09ae14c82968b4da0600a0ada7728227f255864e7e01619ab'},
 'hosted/scripts/test-local.py': {'bytes': 21455,
                                  'sha256': '78292dbf027bff4fae67d638fec9504c042cbeac39b6bca40e38321178bb5951'},
 'hosted/test/fixtures/audit/coherent-vectors.json': {'bytes': 464560,
                                                      'sha256': '7932faecca13772c933048ac3cd39da1dcfc07ee215463243ed551cc0beaf72b'},
 'hosted/test/fixtures/audit/retained-chains.json': {'bytes': 1258404,
                                                     'sha256': 'd25955b2e6e8242e2af3e71b718a7c627998df8c9dbf18aa1b94846abc1a16a9'},
 'hosted/test/fixtures/billing/webhook-signature.json': {'bytes': 3328,
                                                         'sha256': '064080c913395ec5105e135070b9af055f529247b1893c76f1482171df9ad9c9'},
 'hosted/test/foundation_integration_test.exs': {'bytes': 5619,
                                                 'sha256': 'a3c6fcbc09170a23b7b45b93cf3805c176b4728a3bb7eef12278ee8f8c046039'},
 'hosted/test/mixer_hosted/audit/customer_artifact_event_test.exs': {'bytes': 25338,
                                                                     'sha256': '1e5729064e747fc57c64dd7b28030ef89b0d9e72bbaaef733bdab93dca2aee93'},
 'hosted/test/mixer_hosted/audit/upload_event_test.exs': {'bytes': 12254,
                                                          'sha256': '626c11b6fe3785cdcde83966f3871c64240ca07dcb2dc03927f5e37033e3d220'},
 'hosted/test/mixer_hosted/authorization/artifact_read_test.exs': {'bytes': 27053,
                                                                   'sha256': 'df0599b4b874566901f5c6ef2faaea370f2639d872167a8fb7697a7c795547f0'},
 'hosted/test/mixer_hosted/authorization/jit_policy_spec.exs': {'bytes': 9268,
                                                                'sha256': 'e39497fb5dd03edc1ddc00a06a56af26b279bcace2ca9c6810c26a004690656b'},
 'hosted/test/mixer_hosted/authorization/policy_test.exs': {'bytes': 21932,
                                                            'sha256': '3b1595799b3cbe5cc080546d07efabb258dd4891bae9702259d95031b9416ae7'},
 'hosted/test/mixer_hosted/authorization/postgres_repository_test.exs': {'bytes': 31469,
                                                                         'sha256': '63e7c72e351ad0aced90145e4cf3a861d68739c0c06d512f0d17b869704edae4'},
 'hosted/test/mixer_hosted/authorization/transaction_test.exs': {'bytes': 31291,
                                                                 'sha256': '414cc74e70ca8572919ae82d4f17b10b9deb2095d4310aa6856dd8179dbae6ad'},
 'hosted/test/mixer_hosted/billing/raw_webhook_capture_http2_test.exs': {'bytes': 4874,
                                                                         'sha256': '4656e1f05e20ddfe8767be837a38d8323313efd7ef77efa7176a748c518c8ce8'},
 'hosted/test/mixer_hosted/billing/raw_webhook_capture_test.exs': {'bytes': 10728,
                                                                   'sha256': 'd90910cfa91d579be9ab748d6019a7048ed37f6abb4b73ac9686510589878fe7'},
 'hosted/test/mixer_hosted/billing/webhook_signature_test.exs': {'bytes': 8329,
                                                                 'sha256': 'dce0985cc2e42af41164a7724769b26768f4c85cc0d87f03d6ad0e61b4f84244'},
 'hosted/test/mixer_hosted/billing/webhook_transport_test.exs': {'bytes': 4105,
                                                                 'sha256': 'f427b0b601e27f5b34d4d4cfe5e6d60eed452ab1d34e2a8474c6bbeb3162c27a'},
 'hosted/test/mixer_hosted/browser_auth/activation_preparation_test.exs': {'bytes': 17926,
                                                                           'sha256': '0245ef23e333bfd16615644613634dc69e31ef468afe6d1ce825b76d07c9f043'},
 'hosted/test/mixer_hosted/browser_auth/config_test.exs': {'bytes': 15194,
                                                           'sha256': '48ef4fed37e5ed94c513fd16fbb6ef7104c1759046e2e6ffc3eeef14cd283c6d'},
 'hosted/test/mixer_hosted/browser_auth/configuration_digest_test.exs': {'bytes': 5649,
                                                                         'sha256': '42bcf1ea1d1c9d7db3b4756b7d5a070ccb1f163164031d7641268f7e71f37290'},
 'hosted/test/mixer_hosted/browser_auth/custody_test.exs': {'bytes': 5458,
                                                            'sha256': 'e907da6a75dc3b5a53d974522ffcabc64f87be78947b914b4ae2f088e5f5f53b'},
 'hosted/test/mixer_hosted/browser_auth/migration_spec.exs': {'bytes': 8211,
                                                              'sha256': '47309d3db40cd5ed3569a9dd4493c8e4df563a8f6e175c11fe282b54955bbadc'},
 'hosted/test/mixer_hosted/browser_auth/protocol_test.exs': {'bytes': 17357,
                                                             'sha256': 'c60ebced5ae850d4d7e2fe3e4d4c60b8cdb490f2ad40ac8e333faeb49d60bda3'},
 'hosted/test/mixer_hosted/browser_auth/run_migration_fixture.py': {'bytes': 9714,
                                                                    'sha256': '4497a64dce49287877f58b1cc76171bc7489da352ee91d5f480cc184f8a8ca55'},
 'hosted/test/mixer_hosted/browser_auth/run_storage_fixture.py': {'bytes': 8627,
                                                                  'sha256': 'bfd5edfa4f4e362e76686fb7de89def23ca79eefe1b1c58f74749f550c9bf92c'},
 'hosted/test/mixer_hosted/browser_auth/runtime_config_test.exs': {'bytes': 20142,
                                                                   'sha256': 'fcd79eb95485dbe8e20b2fe4ec104daad59fc7eb78b607571132f89c0f0b2e82'},
 'hosted/test/mixer_hosted/browser_auth/storage_fixture.exs': {'bytes': 7108,
                                                               'sha256': '9417342d3d5708d21b216383da8cb4bef381e3572036853e6f099ccf08235a06'},
 'hosted/test/mixer_hosted/browser_auth/storage_spec.exs': {'bytes': 45957,
                                                            'sha256': 'bbb6f93902f743299e6c4189806757f3366ff20bcfed8fa56b0f9162d38e041c'},
 'hosted/test/mixer_hosted/browser_auth/stored_snapshot_test.exs': {'bytes': 15352,
                                                                    'sha256': 'bf814937391e70305f853ed5710920b3d7f54587a2497646cb025e03d8c68f2e'},
 'hosted/test/mixer_hosted/browser_auth/vault_test.exs': {'bytes': 20940,
                                                          'sha256': '133dc8e8aeeec19a4a6020baa83e3badc021832360ca3a9048c88a3318a8ab38'},
 'hosted/test/mixer_hosted/builds/admission_test.exs': {'bytes': 21354,
                                                        'sha256': '9aa895580f54af5f67dc610b7e899963712f12a6becd64f8e63170cd02f4a37a'},
 'hosted/test/mixer_hosted/builds/aggregate_admission_test.exs': {'bytes': 30252,
                                                                  'sha256': '3c7ba454e32c085e862ac929a49765cf56166e6057e6ba436cda7dfff90bb646'},
 'hosted/test/mixer_hosted/builds/coordinator_test.exs': {'bytes': 21500,
                                                          'sha256': 'af70ef055e97ff1ba16b546297f802a7b7dc339fcf7e9c5bc45c5af2b70bfdb6'},
 'hosted/test/mixer_hosted/builds/journal_test.exs': {'bytes': 25263,
                                                      'sha256': '8793125673b1a1ded44f47bce833a41bf65cf3eac51fbbd7ebede2ecd478d97e'},
 'hosted/test/mixer_hosted/builds/lifecycle_test.exs': {'bytes': 27848,
                                                        'sha256': '79e1628427b75b5280df2d30219cdd286ad11f0916dcc6e39786b1dbecd4f3f7'},
 'hosted/test/mixer_hosted/builds/storage_test.exs': {'bytes': 13131,
                                                      'sha256': 'dc31fb40ed3cd586450db63fd20747523ac4594349dcf73b2e4b9fb0ec275ca4'},
 'hosted/test/mixer_hosted/customer_artifacts/postgres_storage_test.exs': {'bytes': 39864,
                                                                           'sha256': 'b7c9fc606a6ec1bc5916381b1e970a22f5d5251a98e84c57207cd4763b3fe8ec'},
 'hosted/test/mixer_hosted/customer_artifacts_test.exs': {'bytes': 22095,
                                                          'sha256': 'b9b6aa3c431d918ef1c70fd62abb3286f128fd148f31f813c41e22ae046e8775'},
 'hosted/test/mixer_hosted/customer_workspace_test.exs': {'bytes': 39431,
                                                          'sha256': '1d5b68cb6e3dbace2fe0770764d6e75014cf22e49ebf6b31dfff50d9aafc8a85'},
 'hosted/test/mixer_hosted/identity/access_token_verifier_test.exs': {'bytes': 22379,
                                                                      'sha256': 'e851fa0315c52e02dd24a9b6c81a8d84c409a352b55acba8c26a4d861cd3d7af'},
 'hosted/test/mixer_hosted/identity/key_owner_inflight_lifecycle_test.exs': {'bytes': 24827,
                                                                             'sha256': '712dac61a33dbe7805a1e5f41c1f648c5b9ba482ac23952e9bc1ef0136a6cea6'},
 'hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs': {'bytes': 14688,
                                                                    'sha256': 'b87a38126edc9a96c3721677684007f1870d99736b88e63e15e8ed329d0e215d'},
 'hosted/test/mixer_hosted/identity/key_owner_linux_network_test.exs': {'bytes': 3183,
                                                                        'sha256': '0ce4ba31eebfaea270e891deabdceba936bb79ee2b3b61e48c957e230844ef9f'},
 'hosted/test/mixer_hosted/identity/key_owner_test.exs': {'bytes': 46346,
                                                          'sha256': '0378933f07f780fd4f2616df409b39bbff3a58e0849ca7ff202060d49a9ee483'},
 'hosted/test/mixer_hosted/identity/manifest_endpoint_test.exs': {'bytes': 5208,
                                                                  'sha256': '5c41caab26b19f204d386e9051906cabae490044b209e21b2557dfd1244f9be3'},
 'hosted/test/mixer_hosted/identity/startup_config_test.exs': {'bytes': 8279,
                                                               'sha256': 'bb9fc59f47c2c4bb15c42608ff52cd3dbe88ed71e73957bda3c4775b96214c3a'},
 'hosted/test/mixer_hosted/identity/startup_lifecycle_test.exs': {'bytes': 6531,
                                                                  'sha256': 'e88301c119b04528879b0b52e896c73075cd2a390bc17ef9b20a2ddf68430ba2'},
 'hosted/test/mixer_hosted/identity/startup_linux_network_test.exs': {'bytes': 4995,
                                                                      'sha256': '7d28b594476d349b3ca6e35c2dbadb21f6e831f53ace235e3a1e8b85cb712480'},
 'hosted/test/mixer_hosted/protocol/artifact_admission_test.exs': {'bytes': 16835,
                                                                   'sha256': '8d79277ad933204be02bc540412968842b903cfe444f252a9c4642e1da3dd31f'},
 'hosted/test/mixer_hosted/protocol/artifact_cbor_test.exs': {'bytes': 7872,
                                                              'sha256': '083d0479d56a3c77fffc32988fc42746d1968219807debbb687078a812a933a5'},
 'hosted/test/mixer_hosted_web/bearer_identity_compile_test.exs': {'bytes': 3555,
                                                                   'sha256': '664fec5c8c3ae9001df1836f74e1f76f3fb70696a4b7d7bd03c7074d825be710'},
 'hosted/test/mixer_hosted_web/bearer_identity_test.exs': {'bytes': 25213,
                                                           'sha256': '3a2445a9380a6679529d245fa092a5f0c0eab4dc658b41e0f44f563f1a6fda17'},
 'hosted/test/mixer_hosted_web/browser_workspace_dispatcher_capture_adapter_test.exs': {'bytes': 7201,
                                                                                        'sha256': '7fc8cc584d3f1b882386f62903c2c69b1cd7c4a1a75361175556e2bc25f00c61'},
 'hosted/test/mixer_hosted_web/browser_workspace_dispatcher_request_test.exs': {'bytes': 5465,
                                                                                'sha256': '83649a3f972e13482abe893ab8817f85fec47910722bfa7fafbd246403f53d73'},
 'hosted/test/mixer_hosted_web/browser_workspace_dispatcher_test.exs': {'bytes': 6885,
                                                                        'sha256': 'e03227fde20ef946e538c17ed41b4d7d50d7fba88ef737c50e9caceb7c47e3ea'},
 'hosted/test/mixer_hosted_web/customer_artifact_http_integration_test.exs': {'bytes': 33067,
                                                                              'sha256': '81de356fc55106181471b72de93f4664600075f079135a5881f7b6985a810272'},
 'hosted/test/mixer_hosted_web/customer_artifact_transport_test.exs': {'bytes': 28640,
                                                                       'sha256': '2aa497b77292e380c88b564ee504165f5773e3347da422e97ece664ce152d9bb'},
 'hosted/test/mixer_hosted_web/customer_workspace_http_integration_test.exs': {'bytes': 30280,
                                                                               'sha256': 'ec04043170f7300293b6a42c3daf47f2f26c1868b77a1b30a03a9259b524a870'},
 'hosted/test/mixer_hosted_web/customer_workspace_transport_test.exs': {'bytes': 22996,
                                                                        'sha256': '2f5c93b3a2ee6c99fac018b10e66e266b44c4c36d3ec01e5fc91303960a3aabf'},
 'hosted/test/runtime_config_test.exs': {'bytes': 3661,
                                         'sha256': 'bf12eaec3ac8da5b7aec297c16bd3d3e89f62182c3fd00980b60a7c04e3a6daf'},
 'hosted/test/support/build_dispatch_fixture.ex': {'bytes': 4675,
                                                   'sha256': 'a2c601c4cdab3a2bb2683fb8564da0fa61a4bf543123b81f5ee1d63418af4c62'},
 'hosted/test/support/build_intent_worker.ex': {'bytes': 468,
                                                'sha256': '48f36bbc27956ce380bf2684826bcb22180636d9e81a3a3a569658f4cfb9ff48'},
 'hosted/test/support/http2_wire_fixture.ex': {'bytes': 21444,
                                               'sha256': 'c0ba4561576060c525e586414fcfeacc88cfa19b14607d4f13dffaca32da7f4e'},
 'hosted/test/support/identity_component_fixture.ex': {'bytes': 525,
                                                       'sha256': '1713d06d203ff6ca765e25b2dacc0cb5b8f3c7597308412e7d61ff5f8507953c'},
 'hosted/test/support/identity_dns_fixture.ex': {'bytes': 2874,
                                                 'sha256': '67f1dfc30387f48644bfe1d4de3ac43a77f873fe82cac4a02eb881f9d56b9283'},
 'hosted/test/support/identity_raw_fixture.ex': {'bytes': 2664,
                                                 'sha256': 'ccfc9105b317d0708d3af2a98f6854c38aed30ed12ba28a1fe49a6cc3ffd6862'},
 'hosted/test/support/identity_socket_probe.ex': {'bytes': 2893,
                                                  'sha256': '8135af832ad0f1877e7370ff491c882597c1510d82f15c011a35897e936f9416'},
 'hosted/test/support/identity_startup_fixture.ex': {'bytes': 4539,
                                                     'sha256': '075f77531b83d43567c214777ee458cb630f15e62fbd1f009c46100ccacdd761'},
 'hosted/test/support/identity_tls_fixture.ex': {'bytes': 8003,
                                                 'sha256': '1ebb466459c4cf07e23bad66dcabc080b3f3348c5c12d974b28ef88ded1de1e2'},
 'hosted/test/support/probe_worker.ex': {'bytes': 365,
                                         'sha256': '1caebaa5ea30e06a114650b67d577c4e31125d2b76e59c1de6900ff2989dfb33'},
 'hosted/test/test_helper.exs': {'bytes': 251,
                                 'sha256': '71a75fc76dcf3c252b4d41c1f3a30adccfae5873028f7d40f174c8a25fd7c646'}}


FIXTURE_MANIFEST = {
    **PREDECESSOR_MANIFEST,
    "hosted/test/support/identity_tls_fixture.ex": {"bytes": 9533, "sha256": "d3b55796a8baac4f9ebd37cc9ee5e44bde01ca346ce2dd00a0a5dd884711ba55"},
    "hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs": {"bytes": 4387, "sha256": "417704f8e805196f9546a508a770d23a55d40ce9d6214be5225f131c4bd2c7c6"},
}


FROZEN_MANIFEST = {
    **FIXTURE_MANIFEST,
    "hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs": {'bytes': 4401, 'sha256': 'a76b33c4cefac67797fed2909fe7b0c2eb7f7bb99a40b7924adc68901a514fff'},
}


CURRENT_MANIFEST = {
    **FROZEN_MANIFEST,
    'hosted/lib/mixer_hosted/billing/webhook_event.ex': {'bytes': 505, 'sha256': 'e353ab039a9b5d6a919888baf7e424bd126a208571019651764cf801d4d7955f'},
    'hosted/lib/mixer_hosted/billing/webhook_inbox.ex': {'bytes': 6483, 'sha256': 'd498fa87642389a4351f195a94632e2b890881bcb803e5aeb7659080a2147f87'},
    'hosted/lib/mixer_hosted_web/billing_webhook_controller.ex': {'bytes': 1547, 'sha256': 'e054af6025aacb4fa826129681fd958c2127d95bfd0ba4b6c71a979c401792a3'},
    'hosted/lib/mixer_hosted_web/billing_webhook_endpoint.ex': {'bytes': 1903, 'sha256': '469f02425b201e9cf81c45f7da0a83fc8d92eae3e66b17d7f5b165eed8be9ff6'},
    'hosted/priv/repo/migrations/20261110000000_add_billing_webhook_inbox.exs': {'bytes': 711, 'sha256': 'ac4cf0df76b0e7963b48d3a97a727d0a31f108a9267c32999ed7b852a393a2ff'},
    'hosted/test/foundation_integration_test.exs': {'bytes': 6296, 'sha256': '852de2acd4dbf623925d5fb7eddc14856e4cd0dc0ed09ca87703e6b1f2294a1b'},
    'hosted/test/mixer_hosted/billing/product_route_test.exs': {'bytes': 7937, 'sha256': '7eed8000a1c8d56950986e1ef67b56ee9511be9d4aff293891dc0cfdd547ca64'},
    'hosted/test/mixer_hosted/billing/webhook_inbox_test.exs': {'bytes': 11307, 'sha256': '91f7f81881da4120cb940b565ae019c2a4a97376c1bdf98b652058420eb874bd'},
    'hosted/test/mixer_hosted/builds/admission_test.exs': {'bytes': 21331, 'sha256': 'df5a64018692a9ddaefffb032d8ebec05824bd60035f5f08741d40e76c2bf1c7'},
    'hosted/test/mixer_hosted/builds/aggregate_admission_test.exs': {'bytes': 30295, 'sha256': 'ea55f5d285ea1804238a577237fef1f0166e257ca3fa2d31d621f0324dbcc6df'},
    'hosted/test/mixer_hosted/builds/coordinator_test.exs': {'bytes': 24996, 'sha256': '8750fcbdcc6b280b20bb68a44ef2df0f0617d77a47d32d8a5cbfd3adb6458ad3'},
    'hosted/test/mixer_hosted/builds/storage_test.exs': {'bytes': 12763, 'sha256': '32ffb3afddbb34126ef63328c44f458c2310d9e107d7413c8bb95cb6c55735cd'},
    'hosted/test/test_helper.exs': {'bytes': 1362, 'sha256': 'cbabda9a0df61675908367f4b7e74580070d9ae491d9aa1a29a30e88a06f0f0f'},
}


def finalize(root, output):
    """Always-step continuation, within the original budget and retained exact IDs."""
    output = Path(output)
    state_path = output / 'state.json'
    if not state_path.is_file():
        output.mkdir(parents=True, exist_ok=True)
        receipt = {'schema': 1, 'status': 'unqualified-collector-not-run-or-state-missing', 'cleanup': 'no retained created CID; no Docker operation attempted', 'run_id': os.environ.get('GITHUB_RUN_ID'), 'attempt': os.environ.get('GITHUB_RUN_ATTEMPT'), 'sha': os.environ.get('GITHUB_SHA'), 'independent_acceptance': 'pending'}
        write_json(output / 'finalizer.json', receipt)
        files = {'finalizer.json': {'bytes': (output / 'finalizer.json').stat().st_size, 'sha256': hashlib.sha256((output / 'finalizer.json').read_bytes()).hexdigest()}}
        write_json(output / 'artifact-manifest.json', {'schema': 1, 'files': files, 'tree_digest_sha256': canonical_digest(files), 'scope': 'collector not run; no test/cleanup qualification'})
        return 1
    state = json.loads(state_path.read_bytes())
    require(state.get('run_id') == os.environ.get('GITHUB_RUN_ID') and state.get('attempt') == os.environ.get('GITHUB_RUN_ATTEMPT') and state.get('sha') == os.environ.get('GITHUB_SHA'), 'finalizer run identity mismatch')
    require(re.fullmatch(r'mixer-identity-net-[0-9]+-[0-9]+-[0-9a-f]{32}', state.get('label', '')), 'finalizer label mismatch')
    subject = object.__new__(Collector)
    subject.root, subject.output, subject.sha = Path(root), output, state['sha']
    subject.state, subject.registry = state, OwnedRegistry()
    subject.registry.records = [OwnedContainer(**row) for row in state['containers']]
    subject.registry.unresolved = state['unresolved_creates']
    subject.budget = Budget(start=state['started_monotonic'])
    subject.cancelled, subject.log_bytes, subject.command_number = state['cancelled'], state['log_bytes'], state['command_number']
    subject.run_id, subject.attempt, subject.label, subject.runner = state['run_id'], state['attempt'], state['label'], None
    require(len(subject.registry.records) + len(subject.registry.unresolved) <= 3, 'finalizer registry count')
    require(len({row.cid for row in subject.registry.records}) == len(subject.registry.records), 'finalizer duplicate CID')
    for row in subject.registry.records:
        require(row.role in CAPS and re.fullmatch('[0-9a-f]{64}', row.cid) and row.name == subject.label + '-' + row.role and row.label == subject.label and row.image_id == IMAGES['pg' if row.role == 'pg' else 'test']['config'] and row.state in {'owned', 'removed', 'identity_lost'}, 'finalizer registry identity mismatch')
    (output / '.scratch').mkdir(exist_ok=True)
    clean = subject.cleanup()
    if not clean:
        subject.state['status'] = 'FAILED-cleanup-unknown-or-incomplete'
    if subject.state.get('qualification_failures'):
        subject.state['status'] = 'FAILED-terminal-runtime-state'
    if subject.cancelled:
        subject.state['status'] = 'FAILED-cancelled'
    if not subject.state.get('primary_outcome_frozen'):
        subject.state['status'] = 'FAILED-interrupted-before-outcome'
    write_json(output / 'finalizer.json', {'schema': 1, 'same_original_aggregate_deadline': True, 'cleanup_verified': clean, 'no_retry_of_identity_lost_or_unknown_create': True, 'primary_status': subject.state['status']})
    subject.seal()
    return 0 if clean else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sha')
    parser.add_argument('--output')
    parser.add_argument('--finalize')
    parser.add_argument('--check-source', action='store_true')
    options = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    if options.check_source:
        require(not options.sha and not options.output and not options.finalize, 'source preflight takes only --check-source')
        print(json.dumps(check_build_clock_source(root), sort_keys=True))
        return 0
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'execution is selected only on the fresh GitHub runner; import controls are host-only')
    selected_output = Path(options.finalize or options.output or '').resolve()
    require(selected_output.parent == root and selected_output.name == 'identity-network-evidence', 'output must be the one owned identity-network-evidence directory')
    if options.finalize:
        require(not options.sha and not options.output, 'finalizer takes only --finalize')
        return finalize(root, selected_output)
    require(options.sha == os.environ.get('GITHUB_SHA') and options.output, 'exact GITHUB_SHA and explicit output required')
    subject = Collector(root, selected_output, options.sha)
    def cancelled(signum, _frame):
        subject.cancelled = True
        subject.state['cancellation_signal'] = signum
    signal.signal(signal.SIGINT, cancelled)
    signal.signal(signal.SIGTERM, cancelled)
    return subject.run()


SUCCESSOR_MANIFEST = {
    **CURRENT_MANIFEST,
    'hosted/lib/mixer_hosted/billing/usage_entry.ex': {'bytes': 559, 'sha256': '6b6a5b2acdcf8a2118d34ccc15345e63ac08e3d2e2676489366bf8ebbce1322f'},
    'hosted/lib/mixer_hosted/billing/usage_ledger.ex': {'bytes': 7837, 'sha256': '4655ef30ec1efa001bf38194701c0f7e5785df55a7efb1889f27741cb5f6c266'},
    'hosted/priv/repo/migrations/20261110000001_add_billing_usage_ledger.exs': {'bytes': 3732, 'sha256': '33d341c493b5ba7a0f170a5d4994972ba7666cc91c0cdcf64b943822b08af7c5'},
    'hosted/scripts/test-local.py': {'bytes': 21806, 'sha256': '5c8d878c895866411bc34b42b6e38e7a5f8a73d1cd3a213773bc09a424420dd8'},
    'hosted/test/mixer_hosted/billing/usage_ledger_test.exs': {'bytes': 15583, 'sha256': '71d5d292dbe025a45f4fc0b67121ac5354d55cb639c71b53de4ed6666e66ed1e'},
    'hosted/test/mixer_hosted/browser_auth/migration_spec.exs': {'bytes': 8509, 'sha256': '17525dde0c58c997a7f1ba4e6d5f33106dae972a805d2611f84a24480d2151d1'},
    'hosted/test/mixer_hosted/browser_auth/run_migration_fixture.py': {'bytes': 9339, 'sha256': '2e095ea7202cd7d7f72df6c30e961dafdcf848d63807a089da26abd5ae831e84'},
    'hosted/test/mixer_hosted/builds/aggregate_admission_test.exs': {'bytes': 30144, 'sha256': '4dde515c2cb3805ac979b382a867eac56335c7bfda44ed6b8bfac235de6de3b6'},
    'hosted/test/support/reviewed_migrations.json': {'bytes': 597, 'sha256': '588f54f76747be82713188547f41a3f04cdb18250faaa375b1ee65523e36d103'},
    'hosted/test/test_helper.exs': {'bytes': 903, 'sha256': 'c8781a28fdc95e2556794163fa24036546be1959b04371f577a63418efbc503b'},
}


PRIVATE_MANIFEST = {
    **SUCCESSOR_MANIFEST,
    'hosted/lib/mixer_hosted/billing/observed_subscription.ex': {'bytes': 2846, 'sha256': '49bf9da5d873d0299b9cf99bc70a27711cad9b1145ea17e56ba294f103a08e0e'},
    'hosted/lib/mixer_hosted/billing/subscription_read_transport.ex': {'bytes': 9245, 'sha256': 'd9a1440060a6166eb49eac42d89bcf2c613bd60a0609d1002eeea3cf7bcaec95'},
    'hosted/lib/mixer_hosted/builds/operation_admission.ex': {'bytes': 6985, 'sha256': 'e8d8e29f3fbba9b5fe8f2f6ae8fb82413105eb4599334f86efb3843aad0e735c'},
    'hosted/priv/unselected_operation_admission/01_table.sql': {'bytes': 774, 'sha256': '7b016fb16a77b2f32a4034d108fb8450ec8acb8285a5f892ab383a1576dc1b45'},
    'hosted/priv/unselected_operation_admission/02_immutable_function.sql': {'bytes': 988, 'sha256': 'c2df2cfbabb2b5ee09d878067f58caf2df8483560cac5cc84c719db8ea707cb5'},
    'hosted/priv/unselected_operation_admission/03_immutable_trigger.sql': {'bytes': 195, 'sha256': '23ff6521503065ec7dd15c871c8c056b15c464f5873bfb4dafd938641d495c26'},
    'hosted/priv/unselected_operation_admission/04_admission_function.sql': {'bytes': 3779, 'sha256': '32267de6bbe60ce2999b2e628b71c19499206ef4fad7385f9de3960e1a01b700'},
    'hosted/priv/unselected_operation_admission/20261110000498_add_private_build_operation_admission.exs': {'bytes': 525, 'sha256': '7833259133321b699559052bf836900a80f0257a437e3762a1dbb98af99b8ea3'},
    'hosted/scripts/test-local.py': {'bytes': 21972, 'sha256': '1514be29aed481e4e433bbcf9c6c7778c7b3acbf8db16b3bb3a06e5b753c9507'},
    'hosted/test/mixer_hosted/billing/subscription_read_transport_test.exs': {'bytes': 14451, 'sha256': '10cc7e5ee10e933865ed7c62afafb818053c427fdd4ff0334c4d3c6f1b9601f1'},
    'hosted/test/mixer_hosted/builds/operation_admission_test.exs': {'bytes': 17945, 'sha256': '71597fc651ee7e265d6da7bcaf1daf5a3343fa0e1bdc77375b74b818f5d00eaa'},
    'hosted/test/support/subscription_tls_fixture.ex': {'bytes': 9626, 'sha256': '6ba9183453d9137585d8155cee02ab559fbd1cc776fe93ca722ffed612680ab8'},
    'hosted/test/mixer_hosted_web/customer_artifact_http_integration_test.exs': {'bytes': 33080, 'sha256': '79cbcf1a529723f55e5bf49c18aa667b13cec1403c87c86a1a2975d57e81f23e'},
}


BROWSER_SOURCE_COUNT, BROWSER_MANIFEST = _load_browser_source_authority()
OPERATION_AUTHORITY = _load_operation_source_authority()
OPERATION_SOURCE_COUNT, OPERATION_MANIFEST = OPERATION_AUTHORITY.count, OPERATION_AUTHORITY.manifest
LIFETIME_AUTHORITY = _load_lifetime_source_authority()
LIFETIME_SOURCE_COUNT, LIFETIME_MANIFEST = LIFETIME_AUTHORITY.count, LIFETIME_AUTHORITY.manifest
COMMIT_AUTHORITY = _load_commit_source_authority()
COMMIT_SOURCE_COUNT, COMMIT_MANIFEST = COMMIT_AUTHORITY.count, COMMIT_AUTHORITY.manifest

PROXY_AUTHORITY = _load_proxy_source_authority()
PROXY_SOURCE_COUNT, PROXY_MANIFEST = PROXY_AUTHORITY.count, PROXY_AUTHORITY.manifest

BUILD_READ_AUTHORITY = _load_customer_build_source_authority()
BUILD_READ_SOURCE_COUNT, BUILD_READ_MANIFEST = BUILD_READ_AUTHORITY.count, BUILD_READ_AUTHORITY.manifest

BROWSER_BUILD_AUTHORITY = _load_browser_build_source_authority()
BROWSER_BUILD_SOURCE_COUNT, BROWSER_BUILD_MANIFEST = BROWSER_BUILD_AUTHORITY.count, BROWSER_BUILD_AUTHORITY.manifest

OWNED_EVIDENCE_AUTHORITY = _load_owned_evidence_source_authority()
OWNED_EVIDENCE_SOURCE_COUNT, OWNED_EVIDENCE_MANIFEST = OWNED_EVIDENCE_AUTHORITY.count, OWNED_EVIDENCE_AUTHORITY.manifest

HOSTED_COMPILER_AUTHORITY = _load_hosted_compiler_source_authority()
HOSTED_COMPILER_SOURCE_COUNT, HOSTED_COMPILER_MANIFEST = HOSTED_COMPILER_AUTHORITY.count, HOSTED_COMPILER_AUTHORITY.manifest

CATALOG_JOIN_AUTHORITY = _load_catalog_join_source_authority()
CATALOG_JOIN_SOURCE_COUNT, CATALOG_JOIN_MANIFEST = CATALOG_JOIN_AUTHORITY.count, CATALOG_JOIN_AUTHORITY.manifest

PROVIDER_HTTPS_AUTHORITY = _load_provider_https_source_authority()
PROVIDER_HTTPS_SOURCE_COUNT, PROVIDER_HTTPS_MANIFEST = PROVIDER_HTTPS_AUTHORITY.count, PROVIDER_HTTPS_AUTHORITY.manifest

ORDINARY_BROWSER_AUTHORITY = _load_ordinary_browser_source_authority()
ORDINARY_BROWSER_SOURCE_COUNT, ORDINARY_BROWSER_MANIFEST = ORDINARY_BROWSER_AUTHORITY.count, ORDINARY_BROWSER_AUTHORITY.manifest

SUPERVISED_PROVIDER_AUTHORITY = _load_supervised_provider_source_authority()
SUPERVISED_PROVIDER_SOURCE_COUNT, SUPERVISED_PROVIDER_MANIFEST = SUPERVISED_PROVIDER_AUTHORITY.count, SUPERVISED_PROVIDER_AUTHORITY.manifest

PROVIDER_IO_AUTHORITY = _load_provider_io_source_authority()
PROVIDER_IO_SOURCE_COUNT, PROVIDER_IO_MANIFEST = PROVIDER_IO_AUTHORITY.count, PROVIDER_IO_AUTHORITY.manifest

CONFIGURED_STARTUP_AUTHORITY = _load_configured_startup_source_authority()
CONFIGURED_STARTUP_SOURCE_COUNT, CONFIGURED_STARTUP_MANIFEST = CONFIGURED_STARTUP_AUTHORITY.count, CONFIGURED_STARTUP_AUTHORITY.manifest

PUBLIC_SIGNIN_AUTHORITY = _load_public_signin_source_authority()
PUBLIC_SIGNIN_SOURCE_COUNT, PUBLIC_SIGNIN_MANIFEST = PUBLIC_SIGNIN_AUTHORITY.count, PUBLIC_SIGNIN_AUTHORITY.manifest

CONSOLE_COHERENCE_AUTHORITY = _load_console_coherence_source_authority()
CONSOLE_COHERENCE_SOURCE_COUNT, CONSOLE_COHERENCE_MANIFEST = CONSOLE_COHERENCE_AUTHORITY.count, CONSOLE_COHERENCE_AUTHORITY.manifest

BUILD_CLOCK_AUTHORITY = _load_build_clock_source_authority()
BUILD_CLOCK_SOURCE_COUNT, BUILD_CLOCK_MANIFEST = BUILD_CLOCK_AUTHORITY.count, BUILD_CLOCK_AUTHORITY.manifest

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except CollectorError as error:
        print('identity network collector refused: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
