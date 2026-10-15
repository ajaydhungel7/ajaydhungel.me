Pull latest from dev, stage and commit any uncommitted changes, push to origin/dev, then open a PR to main if one doesn't already exist.

Steps:
1. Run `git status` to check for uncommitted changes. If there are any, ask the user for a commit message before proceeding.
2. Pull latest from dev with `git pull origin dev --no-rebase`. Resolve any conflicts by preferring incoming for generated files (`public/`), and ask the user for guidance on source file conflicts.
3. Push to origin with `git push origin dev`.
4. Check for an existing open PR with `gh pr list --head dev --state open`. If one exists, show the URL and stop.
5. Create a PR to main with `gh pr create --base main --head dev`. Use recent commit messages to write a concise title (under 70 chars) and a short summary body with 2-4 bullet points. No lengthy checklists.
6. Return the PR URL.
