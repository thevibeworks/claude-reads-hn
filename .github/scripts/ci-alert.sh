#!/usr/bin/env bash
# ci-alert.sh -- make a failing digest run impossible to miss.
#
# Usage:
#   .github/scripts/ci-alert.sh open <run-id>   # called on failure
#   .github/scripts/ci-alert.sh close           # called on success
#
# This workflow runs several times a day and a red run has no reader: the
# curator's notifications only fire after a successful push, so a run that
# died before that (2026-09-02 05:32, "Spending cap reached", 481 ms) was
# silent. The tripwire is one tracking issue labelled `ci-failure`: opened
# on the first failure, commented on for each subsequent one, closed by the
# next green run. Bounded at one open issue.
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
# Same script as claude-code-envs and claude-code-http-spec; only the words
# differ. Uses the built-in GITHUB_TOKEN via GH_TOKEN.
set -euo pipefail

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY not set}"
LABEL="ci-failure"
TITLE="hn digest is failing"

action="${1:-}"

existing() {
  gh api "repos/$REPO/issues?state=open&per_page=100" \
    -q "[.[] | select(.pull_request == null) | select(.title == \"$TITLE\" or any(.labels[]?; .name == \"$LABEL\"))] | .[0].number // empty"
}

case "$action" in
  open)
    run_id="${2:?usage: $0 open <run-id>}"
    run_url="https://github.com/$REPO/actions/runs/$run_id"
    num="$(existing)"
    for _ in 1 2 3 4 5; do
      [[ -n "$num" ]] && break
      sleep 3
      num="$(existing)"
    done
    if [[ -n "$num" ]]; then
      gh api "repos/$REPO/issues/$num/comments" -f body="Still failing: $run_url" >/dev/null
      echo "ci-alert: commented on existing #$num" >&2
    else
      gh api "repos/$REPO/labels" -f name="$LABEL" -f color=b60205 \
        -f description="A scheduled digest run is red" >/dev/null 2>&1 || true
      num="$(gh api "repos/$REPO/issues" -f title="$TITLE" -f "labels[]=$LABEL" \
        -f body="A scheduled \`hn digest\` run failed before an edition reached main.

Failing run: $run_url

This issue closes automatically on the next green run. If it stays open,
readers are not getting editions. The usual causes: the Claude OAuth
token at its spending cap, a GitHub Actions outage, or the curate step
timing out." -q .number)"
      echo "ci-alert: opened #$num" >&2
    fi
    ;;
  close)
    num="$(existing)"
    if [[ -n "$num" ]]; then
      gh api -X PATCH "repos/$REPO/issues/$num" -f state=closed -f state_reason=completed >/dev/null
      echo "ci-alert: closed #$num (run is green again)" >&2
    else
      echo "ci-alert: nothing to close" >&2
    fi
    ;;
  *)
    echo "usage: $0 open <run-id> | close" >&2
    exit 2
    ;;
esac
