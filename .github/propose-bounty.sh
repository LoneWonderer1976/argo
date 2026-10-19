#!/usr/bin/env bash
# Draw a week's bounty if it has none, commit it, close any open bounty issue as lapsed, and open
# the new one for Ben. Two callers, so every Monday gets its bounty (19/10/2026, when one did not):
# statement.yml after Monday's statement, and every hourly sync for the week it is in -- GitHub's
# own schedule is best-effort, the sync is started by cron-job.org, so a Monday the statement run
# missed is made up within the hour. A week that has one -- proposed, live or vetoed -- is left
# alone, so the two never draw twice. Needs GH_TOKEN with issues: write.
#
#   bash .github/propose-bounty.sh [MONDAY]     (blank: argo.weeks.next_monday)
set -euo pipefail
TITLE=$(python -m argo.bounty --propose ${1:+--week "$1"} --issue-file bounty.md --apply)
if [ -z "$TITLE" ]; then exit 0; fi
git config user.name "argo"
git config user.email "argo@users.noreply.github.com"
git add data
git commit -qm "bounty proposed: $TITLE"
git push
for n in $(gh issue list --state open --search 'in:title "Argo bounty"' --json number --jq '.[].number'); do
  gh issue close "$n" --comment "Lapsed: a new week's bounty has just been proposed." || true
done
gh issue create --title "$TITLE" --body-file bounty.md
