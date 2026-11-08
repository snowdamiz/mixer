# Store reviewer information

Prepare one copy for each actual submitted build. Replace every bracketed field
with verified facts about that build. Keep the completed copy and review-account
details in the release's restricted records, outside this repository. This blank
template is not a submission or evidence that Mixer or FieldLog passed review.

Describe the behavior reviewers and ordinary users actually receive. If an update,
fallback, permission boundary or demonstration is unavailable, say so explicitly;
do not copy a capability claim from the product plan as an implemented feature.

## Notes to adapt for App Review or Play review

```text
App: [name], [bundle/package ID], version [version], build [build number/version code].
Contact: [review contact and provider contact-field reference].
Purpose: [specific advertised purpose and the user workflows in this build].

This build contains Mixer [engine version]. [Identify the interpreter included in
the submitted binary, whether interpreted updates are enabled, and the precise
screens/features that use it.] Native controls and platform integrations are
[identify the implementations actually compiled into this binary].

Downloaded material: [exact code/data formats, source, purpose and activation
conditions, or "none"]. [Describe signature verification, installed trust roots,
application/build compatibility checks and the limits actually enforced.] The
downloaded material can access only [enumerate the installed capabilities and
relevant permissions]. [Describe which changes require a new store binary.]

Example change: [the exact before/after behavior of an available example, its
existing user workflow, and why it remains within the stated app purpose].
[Disclose every other feature or functionality change in this submission.]

Review steps:
1. [Sign-in method; use the provider's protected review-account fields.]
2. [Navigation to each affected feature and the expected visible result.]
3. [How to identify the installed binary and active interpreted release.]
4. [How to observe the stated update using the submitted build and normal behavior.]
5. [How to exercise native fallback/offline behavior and its expected visible result.]

Fallback: [what runs without a downloaded release, after rejection or activation
failure, and offline; describe retained data and any limitations].
Review access: [test data, regional/backend requirements, hardware needs and
necessary setup; disclose any review configuration differences].
Evidence: [accessible attachment/reference with build identity, example update,
capability list, reproduction steps and recordings from that exact build].
```

Apple's Notes field allows 4,000 bytes. Measure the completed UTF-8 text, shorten
it if necessary, and place supplementary evidence in the permitted review
attachment fields. Supply required demo-account details through the protected
provider fields; never include signing keys, provider bearer tokens or customer
accounts in these notes. [App Store Connect review information](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information)

## Evidence retained with the release

| Record | Required content |
| --- | --- |
| Build identity | Provider app/build IDs, binary digest, source revision, engine/SDK versions and actual supported OS versions |
| Installed boundary | Capabilities, permissions/entitlements, host ABI and trust-root identifiers, with their installed-binary evidence |
| Example update | Artifact digest, signer identifier, compatible build identity, before/after behavior and reviewer reproduction |
| Recovery | Exact native-fallback, rejected-update and offline outcomes; device/OS and evidence locations |
| Policy review | Date, accountable owner, applicable official-policy URLs, interpretation and unresolved questions |
| Provider progress | Observed provider state and timestamp, submission/build IDs, review messages and required account actions |

Example candidates include correcting a calculation in an existing workflow or
fixing existing text and layout. These examples are not preapproved update
categories: evaluate each actual change and describe it specifically. A new
native library, permission, entitlement, capability or engine implementation
requires the native/store release path under Mixer’s product contract.

Retain upload, processing, testing readiness, review, rejection and availability
as distinct observations. Record an agreement or identity-verification request
as awaiting an account action, preserving the existing build and progress.
Submitting this document or successfully uploading a binary proves neither
testing readiness nor availability. [App and submission statuses](https://developer.apple.com/help/app-store-connect/reference/app-information/app-and-submission-statuses)

## Policy references to recheck for each release train

References were checked on November 7, 2026. Record a fresh check for the actual
release; this date does not certify a future submission or its SDK requirements.

- Apple's agreement §3.3.1(B) places conditions on downloaded interpreted code,
  including consistency with the app's purpose and respect for OS security.
  §3.3.1(C) also addresses enabling additional functionality outside Apple's
  distribution channels. [Apple Developer Program License Agreement](https://developer.apple.com/support/terms/apple-developer-program-license-agreement/)
- App Review Guideline 2.5.2 separately restricts downloaded code that changes
  features or functionality. Guideline 2.3.1 requires specific disclosure of
  changes. Read these requirements together; an interpreter or a technical
  compatibility result does not establish approval. [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- Google Play's Device and Network Abuse policy restricts self-updating apps and
  downloading executable formats such as DEX or native libraries outside Play.
  Its interpreter/VM provision has conditions, and runtime-loaded interpreted
  code must still comply with Play policies. [Google Play Developer Program Policy](https://support.google.com/googleplay/android-developer/answer/18265346?hl=en)

Keep marketing, screenshots, privacy declarations and reviewer instructions
consistent with the submitted build. Preserve the provider's actual decision
and any conditions attached to it; an accepted example is not blanket approval
for later updates or another app.
