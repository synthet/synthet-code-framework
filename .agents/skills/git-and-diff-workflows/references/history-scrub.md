# Scrubbing a leaked path from published history

Use this only after the user approves a history rewrite in so many words. It ends in a force-push, and
every other clone has to realign afterwards.

1. **Inventory.** List every remote branch and tag with `git ls-remote <url>`. Check which of them contain
   the leaking commit: `git merge-base --is-ancestor <commit> <ref>`. Note the full SHA of each ref.
2. **Back up.** Make a fresh `git clone --mirror <url>` in a temporary folder. Then run
   `git bundle create <backup>.bundle --all` and `git bundle verify`. The bundle still holds the leak, so
   keep it local and tell the user where it is.
3. **Drop read-only refs.** GitHub rejects pushes to `refs/pull/*`. Delete them in the mirror first:
   `git for-each-ref --format='delete %(refname)' refs/pull | git update-ref --stdin`.
4. **Rewrite.** `git filter-repo --path <path> --invert-paths --force`, or
   `python -m git_filter_repo …` when the git subcommand isn't on PATH.
5. **Verify before pushing:**
   - No commit on any ref still contains the path: `git log --oneline <ref> -- <path>` is empty for every ref.
   - The leaked string is gone: `git grep -l <string> $(git rev-list --all)` returns nothing.
   - Each rewritten head equals the original minus the path. Compare `git ls-tree -r <old>` with the path's
     lines filtered out against `git ls-tree -r <new>`, for example by sha256 of both listings.
6. **Push with leases.** Name every expected old value as a full SHA, so the push fails if anyone pushed in
   the meantime:
   `git push <url> --force-with-lease=refs/heads/<b>:<full-old-sha> … refs/heads/<b>:refs/heads/<b>`.
   Delete branches that existed only to hold the path (`:refs/heads/<b>`). Leave refs that didn't contain
   the commit alone.
7. **Realign other clones.** Tell every other checkout, including other PCs and agents, not to push until
   it has run `git fetch --prune` and `git reset --keep origin/<default>`. `--keep` refuses to clobber
   local edits, so stop and report if it fails. Pushing an old clone puts the leak back.
8. **What a force-push can't remove.** `refs/pull/<n>/head`, cached commit pages and forks still reach the
   old commit. Only GitHub Support can purge them, so give the user the repo and commit SHA to quote.

Afterwards, update open PRs (their head branches were rewritten too) and remove the temporary mirror.
