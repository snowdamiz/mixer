"""Finite pre-cutoff acceptance snapshot and observation-before-receipt publication."""
import time


def publish(out, launch, parsed, failures, make_receipt, writer, deadline, clock=time.monotonic):
    """Caller has finished compiler cleanup, required hashes and parsing.

    No source/compiler/parse work occurs below. A post-cutoff handler can only
    record an outside-observation classification; it cannot change this frozen
    decision. Writer failures remain publication failures and cannot create an
    accepted receipt for an observation that was never published.
    """
    cutoff = launch.begin_publication()
    launch.record_interruption_failure(failures)
    if clock() >= deadline:
        failures.append({'classification': 'publication-deadline-before-evidence', 'detail': None})
    observation_published = False
    if not failures and parsed is not None:
        try:
            writer(out / 'diagnostic-observation.json', parsed, deadline=deadline)
            observation_published = True
            if clock() >= deadline:
                failures.append({'classification': 'publication-deadline-after-observation', 'detail': None})
        except BaseException as error:
            failures.append({'classification': 'observation-publication-failure',
                             'detail': type(error).__name__ + ': ' + str(error)})
    receipt = make_receipt(cutoff, observation_published)
    if receipt['accepted_diagnostic_observation'] and (failures or not observation_published or parsed is None):
        raise RuntimeError('accepted receipt without completed observation publication')
    # This is the final commit evidence. Atomic writer stages bytes first and
    # publishes the accepted receipt only after observation publication succeeds.
    writer(out / 'receipt.json', receipt, deadline=deadline)
    return receipt
