# Console CI sparse checkout

The Console job at `b231f3d405c06bfb348f193d46a348af0529bd84` exhausted its five-minute job budget in checkout. Run `40556161476` lasted 5m03s; `actions/checkout@v4` was cancelled after 4m59s. Node setup, BEAM setup, revision/runtime recording, installation, typecheck, tests and build were skipped. The observed remote record is `../github-delivery-console-pagination-owner-contracts/ci-jobs-4.stdout`.

The only workflow change is the checkout `with` block in `workflow.patch`. It selects six anchored non-cone patterns:

```text
/console/
/website/src/styles.css
/website/public/assets/flick-128.webp
/website/public/assets/favicon-32.png
/hosted/lib/mixer_hosted/authorization/scope.ex
/hosted/.tool-versions
```

The Ubuntu runner, five-minute timeout, Node `22.23.3`, pinned `erlef/setup-beam` revision, strict `hosted/.tool-versions` selection, npm installation flags, typecheck, tests, production build and trigger paths are byte-for-byte unchanged from the baseline. `validate.py` enforces equality to the baseline workflow plus this exact block.

## Input review

| Input | Actual consumer and closure |
| --- | --- |
| `console/` | Contains the npm package and lockfile, TypeScript/Vite configuration, HTML entry, all application/domain/state/API code, CSS, SSR preview/test entries, public brand assets/notices, and every test matched by `node --test tests/*.test.mjs`. TypeScript includes `src/**/*.ts` and `src/**/*.tsx`; the tests' explicit compiler and Vite SSR inputs are also under `console/`. The AST audit resolves all relative source imports within this retained directory and checks bare package imports against the package manifest. |
| `website/src/styles.css` | `console/tests/brand-parity.test.mjs:7` reads the full stylesheet to compare the ordered root declaration blocks with `console/src/brand.css`. It does not execute the website toolchain or load CSS dependencies. |
| `website/public/assets/flick-128.webp` | The same test's literal two-name asset loop compares its bytes with the retained console copy. `console/src/App.tsx` displays the console public copy. |
| `website/public/assets/favicon-32.png` | The same byte comparison loop retains this input. `console/index.html` refers to the console public copy. |
| `hosted/lib/mixer_hosted/authorization/scope.ex` | `console/tests/workspace-directory-scope-parity.test.mjs:21-23` loads this one standalone helper with `elixir -r` and calls `identifier?/1` using synthetic vectors. Manual review of the helper found only Elixir standard-library dependencies; no Mix project, Phoenix application, store, database, credentials or other hosted source is loaded. |
| `hosted/.tool-versions` | Exact workflow input to pinned `erlef/setup-beam`, with strict version selection. The retained file specifies Erlang `29.1.1` and Elixir `1.20.4-otp-29`. |

Manual review covered the computed inputs that import resolution alone cannot establish: the brand test's two literal asset names; the scope helper invocation; each test's local TypeScript entry; Vite SSR entries and generated output imports; and the binding runner's two environment-selected modules, which its parent test generates from retained console sources. Test outputs are created under the console dependency cache or an owned temporary directory. There is no checked-in generated output required for those imports.

`console/THIRD_PARTY.yml` mentions a verification dependency inventory as documentation. No workflow command, package script, configuration, source import or test reads that inventory. Its documentation link does not add a checkout input. Documentation hyperlinks and API URL handling also do not load repository source. The lockfile contains registry packages and no local/link packages. Targeted committed-tree checks found no root npm, Babel, browserslist or PostCSS configuration that could add an ancestor input. The complete console directory retains any console-local configuration.

## Verification and cleanup

Run `python3 verification/ci-console-sparse-checkout/validate.py` from the repository. This uses a dedicated child PID/PGID with a 55-second outer deadline and a 52-second inner command budget. It parses source with the already installed `@babel/parser`; it does not invoke a compiler, typechecker, test, Elixir runtime or Vite build.

`input-manifest.json` records all 55 selected files, Git blob identities and SHA-256 hashes, source revision/tree, total 380,569 input bytes and the selected-tree digest. Current input bytes must match the baseline commit. `source-audit.json` records AST imports and original source fragments for file/process/build calls and dynamic imports, for inspection alongside the manual closure review above.

The validator initializes an isolated temporary Git repository, refers read-only to the existing object store, and materializes the selected baseline revision with these exact non-cone patterns. It checks that the materialized file list equals the 55-file manifest, every SHA-256 matches, and `git rev-parse HEAD` still works from the console directory. It never fetches, mutates the main index, commits or pushes. `commands.json` retains the full command arguments, working directories, outputs and exit codes; `validation.json` records source/tool identities and scoped results. `runner-receipt.json` records the exact child PID/PGID, deadline, exit and removal of the owned temporary repository.

The local result proves the selected baseline bytes can be materialized by the installed Git version. CI checkout timing, network behavior, action setup and Ubuntu runtime success remain unverified until the changed workflow runs remotely. No new console runtime test result is claimed by this packet. Native runtime, browser/UI automation, capture and physical devices remain paused; none was started. No GA gate is changed by this workflow repair.
