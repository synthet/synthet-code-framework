# Shared checkouts and other people's edits

Several agent sessions often work on the same machine, sometimes in the same checkout. Two habits keep commits
clean.

## 1. Check before you write

Before changing files in a repo you are not already working in:

```bash
git -C <repo> fetch -q origin
git -C <repo> status -sb                                      # your branch, ahead/behind
git -C <repo> log --oneline HEAD..origin/<default-branch>     # work that landed since you looked
```

Also list peer sessions (`ListAgents`) and note any working in that repo. If `origin` already has the change you
were about to make (another session's PR), build on it instead of duplicating it.

**Why:** another session can merge a PR, empty a folder or switch the branch between two of your commands.

## 2. Commit on a branch without moving the shared checkout

Other sessions may commit in the same checkout; if you leave it on your feature branch, their commits land in your
PR. Commit on the branch, then put the checkout back on its default branch with your changes still in place:

```bash
git switch -c <branch>
git add <your paths> && git commit -m "..."
git switch <default-branch>
git checkout <branch> -- <your paths>   # same working-tree content as before
git reset -q                            # unstage; the commit lives on <branch>
```

For a repo with unrelated commits on the local default branch (for example an unpushed release), branch from
`origin/<default>` in a temporary worktree instead (`git worktree add -b <branch> <tmp> origin/<default>`), and
remove the worktree afterwards.

## 3. Stage only your hunks

When a file holds someone else's uncommitted edits next to yours, stage a filtered patch:

```bash
git diff -- <file> | python -c "
import re, sys
text = sys.stdin.buffer.read().decode('utf-8')
head, *hunks = re.split(r'(?m)^(?=@@ )', text)
mine = [h for h in hunks if '<a string only your hunks contain>' in h]
sys.stdout.buffer.write((head + ''.join(mine)).encode('utf-8'))" > mine.patch
git apply --cached --check mine.patch && git apply --cached mine.patch
git diff --cached -- <file>   # only your hunks
git diff -- <file>            # only theirs, still unstaged
```

**Why `sys.stdout.buffer`:** on Windows, text-mode stdout writes CRLF, and `git apply` then fails with
"patch does not apply".
