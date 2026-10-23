# FieldLog store preparation

Requirements checked October 23, 2026, against the official sources linked below. Recheck in the actual store consoles before submission. This guide and `app-store.json` are editable English (US) launch collateral for FieldLog. They do not assert that a store listing, reviewed binary, or qualified feature exists. Mixer itself is developer tooling.

## Metadata

Apple permits a name and subtitle of up to 30 characters each. The promotional text limit is 170 characters; the plain-text description limit is 4,000. Keywords have a stricter **100 UTF-8 byte** limit; the draft uses ASCII and avoids repeating the app name. These are distinct fields; promotional text is not a keyword-ranking field. Sources: [App information](https://developer.apple.com/help/app-store-connect/reference/app-information/app-information/), [Platform version information](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information/), and [Creating your product page](https://developer.apple.com/app-store/product-page/).

Google Play permits a 30-character app title, an 80-character short description, and a 4,000-character full description. Use relevant user language, localize thoughtfully, and avoid repetitive keyword stuffing. Source: [Create and set up your app](https://support.google.com/googleplay/android-developer/answer/9859152?hl=en).

The current name emphasizes the actual task: site notes and tasks. The first two screenshots establish the purpose before deeper workflow features. The JSON lists search-intent hypotheses, not measured keyword volumes or a ranking promise. Verify name availability and product fit with the owner before committing store identities. Category choices are candidates.

## Images and capture

Apple accepts 1–10 screenshots in JPEG/JPG/PNG without transparency. Its current iPhone 6.9-inch portrait options include 1260 × 2736, 1290 × 2796, and 1320 × 2868. Capture a supported size and check the required display classes for the submitted device support, including iPad when applicable; do not stretch a phone capture into a tablet. Apple's table governs required fallbacks. Sources: [Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/) and [Upload previews and screenshots](https://developer.apple.com/help/app-store-connect/manage-app-information/upload-app-previews-and-screenshots/).

Apple's store icon comes from the icon configured in Xcode and uploaded with the build. Prepare 1024 × 1024 artwork for iPhone/iPad, using Icon Composer layers or the appropriate asset catalog, and validate through the selected toolchain. Changing the published icon requires a new app version. Sources: [Creating an icon with Icon Composer](https://developer.apple.com/documentation/xcode/creating-your-app-icon-using-icon-composer) and [Add an app icon](https://developer.apple.com/help/app-store-connect/manage-app-information/add-an-app-icon/). Website icons are separate assets and do not qualify the FieldLog app icon.

Google Play requires a 512 × 512, 32-bit PNG store icon (up to 1024 KB); the feature graphic is 1024 × 500 JPEG or 24-bit PNG without alpha. Screenshots: at least two across supported device types, up to eight per type, JPEG/24-bit PNG without alpha, dimensions 320–3840 px, longest side no more than twice the shortest. Prepare actual portrait phone captures, with 1080 × 1920 as a useful working canvas when accurate for the UI. Additional large-screen requirements apply when supported. Source: [Preview assets](https://support.google.com/googleplay/android-developer/answer/9866151?hl=en).

Use the six-screen story in `app-store.json` as a capture brief. Each entry includes a claim to verify, a caption, and alt text. Capture the released UI separately on iOS and Android. Retain the exact app build, device/OS, scenario, and sanitized dataset identity with the original captures. Review cropping and text at phone display size. Use fictional or consenting project data; remove personal names, location coordinates, tokens, customer addresses, and other identifying content. Do not publish concept renders as evidence of app behavior.

## Publication prerequisites

Work through `publicationChecklist` in the JSON with an accountable product/release owner. The text describes the planned complete FieldLog scope; remove any feature that is absent from the submitted build. Physical-device and store evidence remain separate from website tests. Phones are currently disconnected, so device checks remain pending.

Supply app-specific public support, privacy, and deletion destinations; the Mixer's website privacy page is not a substitute for FieldLog's policy. Reconcile declarations with the actual app, backend, and SDKs. Store review information must make the app's behavior and any downloaded updates understandable and testable. Update technology alone is not a claim of store compliance. Review [Apple's software requirements](https://developer.apple.com/app-store/review/guidelines/#software-requirements) and [Google Play's device/network policy](https://support.google.com/googleplay/android-developer/answer/16559646?hl=en) against the actual build before submission.

Keep listing URLs null until store processing/review and availability are confirmed. Add genuine install badges only once there is an approved destination. Do not invent a published package, price, review count, adoption number, certification, or store approval. FieldLog must consume immutable published Mixer packages from its own repository for release qualification.
