#!/usr/bin/env bash
# ci-alert.sh -- make a failing digest run impossible to miss, and say which
# kind of failure it was.
#
# Usage:
#   .github/scripts/ci-alert.sh open <run-id> [quota|defect]   # on failure
#   .github/scripts/ci-alert.sh close                          # on success
#
# This workflow runs several times a day and a red run has no reader: the
# curator's notifications only fire after a successful push, so a run that
# died before that (2026-09-02 05:32, "Spending cap reached", 481 ms) was
# silent. The tripwire is a tracking issue: opened on the first failure,
# commented on for each subsequent one, closed by the next green run.
#
# Two channels, because there are two problems. Every failure this tripwire
# has caught so far was the shared Claude OAuth token at its cap, which is a
# capacity problem Eric owns at the account level and no commit here can fix.
# A broken script is a defect this repo owns. Filing both under one title
# means the twentieth quota notice buries the first real bug -- red stops
# meaning anything, the same way green did before the verify step landed.
# So: `quota` and `ci-failure` are separate rolling issues, one open at most
# each, and a green run closes both.
#
# The quota issue counts its comments rather than staying quiet, because the
# useful question is not "are we out?" but "how often?" -- that is the number
# that decides whether the bots need a seat of their own.
#
# Dedup never uses the search API: its index lags writes by minutes, which is
# how a sibling repo once filed byte-identical duplicates 13 seconds apart.
# The REST list lags a write too, by a few seconds and unevenly (measured
# 2026-09-02: a second `open` one second after the first made a duplicate
# with or without the label filter, and once even after a 3 s recheck; a
# third `open` seconds later deduplicated fine). So: match on title OR
# label over the plain open-issues list, and before creating, poll for up
# to 15 s. Runs are hours apart, so the wait costs nothing on the path
# that matters and the window is closed on the path that does not.
#
# Same script as claude-code-envs, claude-code-http-spec and deepseek-docs;
# only the words differ. Uses the built-in GITHUB_TOKEN via GH_TOKEN.
set -euo pipefail

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY not set}"

DEFECT_LABEL="ci-failure"
DEFECT_TITLE="hn digest is failing"
QUOTA_LABEL="quota"
QUOTA_TITLE="hn digest is running out of Claude quota"

action="${1:-}"

# Open issue number for one channel, matched on title OR label so a
# hand-retitled or hand-relabelled issue is still found.
existing() {
  local title="$1" label="$2"
  gh api "repos/$REPO/issues?state=open&per_page=100" \
    -q "[.[] | select(.pull_request == null) | select(.title == \"$title\" or any(.labels[]?; .name == \"$label\"))] | .[0].number // empty"
}

case "$action" in
  open)
    run_id="${2:?usage: $0 open <run-id> [quota|defect]}"
    reason="${3:-defect}"
    run_url="https://github.com/$REPO/actions/runs/$run_id"

    if [[ "$reason" == "quota" ]]; then
      title="$QUOTA_TITLE"; label="$QUOTA_LABEL"; colour="fbca04"
      label_desc="A run died because the Claude account hit its cap"
      body="A scheduled \`hn digest\` run stopped because the Claude OAuth token
hit its spending/session cap, so no edition was written.

Failing run: $run_url

This is capacity, not a defect: nothing in this repo can fix it. The token
is shared with every other bot in the org and with interactive use, so a
heavy session starves the digests. Each recurrence is one comment below --
if they are piling up, the automation needs its own seat or API billing.

Closes automatically on the next green run."
    else
      title="$DEFECT_TITLE"; label="$DEFECT_LABEL"; colour="b60205"
      label_desc="A scheduled digest run is red"
      body="A scheduled \`hn digest\` run failed before an edition reached main,
for a reason that was not the Claude account's quota.

Failing run: $run_url

This issue closes automatically on the next green run. If it stays open,
readers are not getting editions. The usual causes: a GitHub Actions
outage, the curate step timing out, or a broken script."
    fi

    num="$(existing "$title" "$label")"
    for _ in 1 2 3 4 5; do
      [[ -n "$num" ]] && break
      sleep 3
      num="$(existing "$title" "$label")"
    done

    if [[ -n "$num" ]]; then
      # Comment count is the running tally; the (N) makes the rate legible
      # without opening the thread.
      n=$(gh api "repos/$REPO/issues/$num/comments?per_page=100" -q 'length')
      gh api "repos/$REPO/issues/$num/comments" \
        -f body="Again ($((n + 2)) so far): $run_url" >/dev/null
      echo "ci-alert: commented on existing #$num ($reason)" >&2
    else
      gh api "repos/$REPO/labels" -f name="$label" -f color="$colour" \
        -f description="$label_desc" >/dev/null 2>&1 || true
      num="$(gh api "repos/$REPO/issues" -f title="$title" -f "labels[]=$label" \
        -f body="$body" -q .number)"
      echo "ci-alert: opened #$num ($reason)" >&2
    fi
    ;;
  close)
    # A green run means neither condition holds, so clear both channels.
    #
    # Two traps here, both found by running this against a live repo:
    #
    # 1. `[[ $closed == 0 ]] && echo ...` as the last line exits 1 whenever
    #    something WAS closed. This step runs under `if: success()`, so a
    #    nonzero exit turns a green digest red, which fires the failure step,
    #    which opens the very issue that was just closed. A tripwire that
    #    manufactures the fault it watches for is worse than none.
    # 2. The open-issues list lags a close by a second or two, so a second
    #    `close` can still see the issue and report closing it again. Read
    #    the issue's real state before claiming anything.
    closed=0
    for pair in "$DEFECT_TITLE|$DEFECT_LABEL" "$QUOTA_TITLE|$QUOTA_LABEL"; do
      title="${pair%%|*}"; label="${pair##*|}"
      num="$(existing "$title" "$label")"
      [[ -n "$num" ]] || continue
      state="$(gh api "repos/$REPO/issues/$num" -q .state)"
      if [[ "$state" != "open" ]]; then
        echo "ci-alert: #$num already closed (stale list)" >&2
        continue
      fi
      gh api -X PATCH "repos/$REPO/issues/$num" -f state=closed \
        -f state_reason=completed >/dev/null
      echo "ci-alert: closed #$num (run is green again)" >&2
      closed=1
    done
    if [[ "$closed" == 0 ]]; then
      echo "ci-alert: nothing to close" >&2
    fi
    ;;
  *)
    echo "usage: $0 open <run-id> [quota|defect] | close" >&2
    exit 2
    ;;
esac

exit 0
