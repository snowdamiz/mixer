import { template as _$template } from "solid-js/web";
import { setAttribute as _$setAttribute } from "solid-js/web";
import { memo as _$memo } from "solid-js/web";
import { createComponent as _$createComponent } from "solid-js/web";
import { className as _$className } from "solid-js/web";
import { effect as _$effect } from "solid-js/web";
import { getNextElement as _$getNextElement } from "solid-js/web";
import { getNextMarker as _$getNextMarker } from "solid-js/web";
import { insert as _$insert } from "solid-js/web";
var _tmpl$ = /*#__PURE__*/_$template(`<span><span class=status-dot aria-hidden=true></span><!$><!/>`),
  _tmpl$2 = /*#__PURE__*/_$template(`<div class=empty-state role=status><h2>Loading release checks</h2><p>Waiting for the selected release and its required checks.`),
  _tmpl$3 = /*#__PURE__*/_$template(`<div class=empty-state role=status><h2>Release data unavailable</h2><p>No release data source is connected to this console yet.</p><p>Checks will appear here when a release is available.`),
  _tmpl$4 = /*#__PURE__*/_$template(`<div class="empty-state invalid-state"role=alert><h2>Check results could not be displayed</h2><p>The release data is incomplete or inconsistent. No check summary is available.`),
  _tmpl$5 = /*#__PURE__*/_$template(`<section aria-labelledby=release-checks-heading class=release-checks><header class=page-heading><p class=eyebrow>Release review</p><h1 id=release-checks-heading>Release checks</h1><p>Compatibility, policy, and test results for every target binary.</p></header><!$><!/>`),
  _tmpl$6 = /*#__PURE__*/_$template(`<div role=status aria-live=polite aria-atomic=true><div><p class=eyebrow>Required checks</p><h2></h2><p></p></div><!$><!/>`),
  _tmpl$7 = /*#__PURE__*/_$template(`<dl class=release-context><div><dt>Selected source revision</dt><dd><code></code></dd></div><div><dt>Target binaries</dt><dd></dd></div><div><dt>Required results</dt><dd>`),
  _tmpl$8 = /*#__PURE__*/_$template(`<div class=target-list>`),
  _tmpl$9 = /*#__PURE__*/_$template(`<p class=page-note>Results apply to the source revision shown. Missing and previous-revision results do not count as a pass.`),
  _tmpl$0 = /*#__PURE__*/_$template(`<section class=target-card><header class=target-heading><div class=target-identity><span class=platform-symbol aria-hidden=true><svg viewBox="0 0 24 24"><rect x=6 y=2 width=12 height=20></rect><path d="M10 5h4m-3 14h2"></path></svg></span><div><h2></h2><p class=target-id></p></div></div><!$><!/></header><table><caption class=sr-only>Required checks for <!$><!/></caption><thead><tr><th scope=col>Check</th><th scope=col>Result</th><th scope=col>Reported evidence</th></tr></thead><tbody>`),
  _tmpl$1 = /*#__PURE__*/_$template(`<p>Previously <!$><!/>. Does not cover the selected revision.`),
  _tmpl$10 = /*#__PURE__*/_$template(`<p>Waiting for completion.`),
  _tmpl$11 = /*#__PURE__*/_$template(`<p>Reported as not run.`),
  _tmpl$12 = /*#__PURE__*/_$template(`<code>`),
  _tmpl$13 = /*#__PURE__*/_$template(`<tr><th scope=row></th><td></td><td class=evidence-cell>`),
  _tmpl$14 = /*#__PURE__*/_$template(`<span>No result received`);
import { createMemo, For, Match, Show, Switch } from "solid-js";
import { summarizeReleaseChecks } from "../domain/release-check-summary.js";
import type { DisplayState, ReleaseTarget, ReportedCheck, SummaryState } from "../domain/release-check-summary.js";
export interface ReleaseCheckInput {
  readonly revision: string;
  readonly expectedTargets: readonly ReleaseTarget[];
  readonly requiredChecks: readonly string[];
  readonly reports: readonly ReportedCheck[];
}
export type ReleaseCheckState = {
  readonly kind: "loading";
} | {
  readonly kind: "unavailable";
} | {
  readonly kind: "ready";
  readonly input: ReleaseCheckInput;
};
const stateLabels: Record<DisplayState | "incomplete", string> = {
  passed: "Passed",
  failed: "Failed",
  pending: "Pending",
  not_run: "Not run",
  stale: "Previous revision",
  incomplete: "Incomplete"
};
const summaryCopy: Record<SummaryState, {
  title: string;
  detail: string;
}> = {
  failed: {
    title: "Checks failed",
    detail: "A required check failed for this revision. Review the affected target below."
  },
  incomplete: {
    title: "Checks incomplete",
    detail: "Some required results are pending, missing, or from a previous revision."
  },
  passed: {
    title: "Checks passed",
    detail: "Every required check reports a pass for this revision. Release approval is evaluated separately."
  }
};
function Status(props: {
  state: DisplayState | "incomplete";
}) {
  return (() => {
    var _el$ = _$getNextElement(_tmpl$),
      _el$2 = _el$.firstChild,
      _el$3 = _el$2.nextSibling,
      [_el$4, _co$] = _$getNextMarker(_el$3.nextSibling);
    _$insert(_el$, () => stateLabels[props.state], _el$4, _co$);
    _$effect(() => _$className(_el$, `status status-${props.state}`));
    return _el$;
  })();
}

/** Read-only display. Expected requirements come from the caller, never reports. */
export function ReleaseChecks(props: {
  state: ReleaseCheckState;
}) {
  const result = createMemo(() => {
    try {
      const state = props.state;
      if (state?.kind === "loading" || state?.kind === "unavailable") return {
        kind: state.kind
      } as const;
      if (state?.kind !== "ready") return {
        kind: "invalid"
      } as const;
      const input = state.input;
      return {
        kind: "ready",
        summary: summarizeReleaseChecks(input.revision, input.expectedTargets, input.requiredChecks, input.reports)
      } as const;
    } catch {
      return {
        kind: "invalid"
      } as const;
    }
  });
  const summary = () => {
    const value = result();
    return value.kind === "ready" ? value.summary : undefined;
  };
  return (() => {
    var _el$5 = _$getNextElement(_tmpl$5),
      _el$6 = _el$5.firstChild,
      _el$0 = _el$6.nextSibling,
      [_el$1, _co$2] = _$getNextMarker(_el$0.nextSibling);
    _$insert(_el$5, _$createComponent(Switch, {
      get children() {
        return [_$createComponent(Match, {
          get when() {
            return result().kind === "loading";
          },
          get children() {
            return _$getNextElement(_tmpl$2);
          }
        }), _$createComponent(Match, {
          get when() {
            return result().kind === "unavailable";
          },
          get children() {
            return _$getNextElement(_tmpl$3);
          }
        }), _$createComponent(Match, {
          get when() {
            return result().kind === "invalid";
          },
          get children() {
            return _$getNextElement(_tmpl$4);
          }
        }), _$createComponent(Match, {
          get when() {
            return summary();
          },
          get children() {
            return _$createComponent(Show, {
              get when() {
                return summary();
              },
              children: value => [(() => {
                var _el$10 = _$getNextElement(_tmpl$6),
                  _el$11 = _el$10.firstChild,
                  _el$12 = _el$11.firstChild,
                  _el$13 = _el$12.nextSibling,
                  _el$14 = _el$13.nextSibling,
                  _el$15 = _el$11.nextSibling,
                  [_el$16, _co$3] = _$getNextMarker(_el$15.nextSibling);
                _$insert(_el$13, () => summaryCopy[value().state].title);
                _$insert(_el$14, () => summaryCopy[value().state].detail);
                _$insert(_el$10, _$createComponent(Status, {
                  get state() {
                    return value().state;
                  }
                }), _el$16, _co$3);
                _$effect(() => _$className(_el$10, `summary-banner summary-${value().state}`));
                return _el$10;
              })(), (() => {
                var _el$17 = _$getNextElement(_tmpl$7),
                  _el$18 = _el$17.firstChild,
                  _el$19 = _el$18.firstChild,
                  _el$20 = _el$19.nextSibling,
                  _el$21 = _el$20.firstChild,
                  _el$22 = _el$18.nextSibling,
                  _el$23 = _el$22.firstChild,
                  _el$24 = _el$23.nextSibling,
                  _el$25 = _el$22.nextSibling,
                  _el$26 = _el$25.firstChild,
                  _el$27 = _el$26.nextSibling;
                _$insert(_el$21, () => value().revision);
                _$insert(_el$24, () => value().targets.length);
                _$insert(_el$27, () => value().targets.reduce((total, target) => total + target.checks.length, 0));
                return _el$17;
              })(), (() => {
                var _el$28 = _$getNextElement(_tmpl$8);
                _$insert(_el$28, _$createComponent(For, {
                  get each() {
                    return value().targets;
                  },
                  children: target => (() => {
                    var _el$30 = _$getNextElement(_tmpl$0),
                      _el$31 = _el$30.firstChild,
                      _el$32 = _el$31.firstChild,
                      _el$33 = _el$32.firstChild,
                      _el$34 = _el$33.firstChild,
                      _el$35 = _el$34.firstChild,
                      _el$36 = _el$33.nextSibling,
                      _el$37 = _el$36.firstChild,
                      _el$38 = _el$37.nextSibling,
                      _el$39 = _el$32.nextSibling,
                      [_el$40, _co$4] = _$getNextMarker(_el$39.nextSibling),
                      _el$41 = _el$31.nextSibling,
                      _el$42 = _el$41.firstChild,
                      _el$43 = _el$42.firstChild,
                      _el$44 = _el$43.nextSibling,
                      [_el$45, _co$5] = _$getNextMarker(_el$44.nextSibling),
                      _el$46 = _el$42.nextSibling,
                      _el$47 = _el$46.nextSibling;
                    _$insert(_el$37, () => target.platform === "ios" ? "iOS" : "Android");
                    _$insert(_el$38, () => target.id);
                    _$insert(_el$31, _$createComponent(Status, {
                      get state() {
                        return target.state;
                      }
                    }), _el$40, _co$4);
                    _$insert(_el$42, () => target.id, _el$45, _co$5);
                    _$insert(_el$47, _$createComponent(For, {
                      get each() {
                        return target.checks;
                      },
                      children: check => (() => {
                        var _el$48 = _$getNextElement(_tmpl$13),
                          _el$49 = _el$48.firstChild,
                          _el$50 = _el$49.nextSibling,
                          _el$51 = _el$50.nextSibling;
                        _$insert(_el$49, () => check.checkId);
                        _$insert(_el$50, _$createComponent(Status, {
                          get state() {
                            return check.state;
                          }
                        }));
                        _$insert(_el$51, _$createComponent(Show, {
                          get when() {
                            return check.reportedRevision !== null;
                          },
                          get fallback() {
                            return _$getNextElement(_tmpl$14);
                          },
                          get children() {
                            return [_$createComponent(Switch, {
                              get children() {
                                return [_$createComponent(Match, {
                                  get when() {
                                    return check.state === "stale";
                                  },
                                  get children() {
                                    var _el$52 = _$getNextElement(_tmpl$1),
                                      _el$53 = _el$52.firstChild,
                                      _el$55 = _el$53.nextSibling,
                                      [_el$56, _co$6] = _$getNextMarker(_el$55.nextSibling),
                                      _el$54 = _el$56.nextSibling;
                                    _$insert(_el$52, (() => {
                                      var _c$ = _$memo(() => check.reportedState === null);
                                      return () => _c$() ? "unreported" : stateLabels[check.reportedState].toLowerCase();
                                    })(), _el$56, _co$6);
                                    return _el$52;
                                  }
                                }), _$createComponent(Match, {
                                  get when() {
                                    return check.state === "pending";
                                  },
                                  get children() {
                                    return _$getNextElement(_tmpl$10);
                                  }
                                }), _$createComponent(Match, {
                                  get when() {
                                    return check.state === "not_run";
                                  },
                                  get children() {
                                    return _$getNextElement(_tmpl$11);
                                  }
                                })];
                              }
                            }), (() => {
                              var _el$59 = _$getNextElement(_tmpl$12);
                              _$insert(_el$59, () => check.reportedRevision);
                              return _el$59;
                            })()];
                          }
                        }));
                        _$effect(() => _$className(_el$48, `check-${check.state}`));
                        return _el$48;
                      })()
                    }));
                    _$effect(_p$ => {
                      var _v$ = `${target.platform === "ios" ? "iOS" : "Android"} target ${target.id}`,
                        _v$2 = target.platform === "ios" ? "3" : "1.5";
                      _v$ !== _p$.e && _$setAttribute(_el$30, "aria-label", _p$.e = _v$);
                      _v$2 !== _p$.t && _$setAttribute(_el$35, "rx", _p$.t = _v$2);
                      return _p$;
                    }, {
                      e: undefined,
                      t: undefined
                    });
                    return _el$30;
                  })()
                }));
                return _el$28;
              })(), _$getNextElement(_tmpl$9)]
            });
          }
        })];
      }
    }), _el$1, _co$2);
    return _el$5;
  })();
}
