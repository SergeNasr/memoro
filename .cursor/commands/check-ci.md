# Check CI Status

Check the status of GitHub Actions CI workflows and fetch failure details. If failures are detected, analyze and fix them.

## Steps

1. **Fetch latest workflow run**:
   ```bash
   gh run list --workflow=ci.yml --limit=1 --json databaseId,conclusion,status,name,headBranch,createdAt,displayTitle
   ```

2. **Check status**:
   - If the latest run is successful: inform user and exit (nothing to do)
   - If the latest run failed or is in progress:
     - Get detailed job information: `gh run view <run-id> --json jobs`
     - For each failed job, fetch logs: `gh run view <run-id> --log --job <job-id>`
     - Extract and display:
       - Test failure messages
       - Error stack traces
       - Compilation/build errors
       - Linting errors
       - Any other relevant error output
     - Provide the GitHub Actions run URL for reference

3. **Analyze failures and fix**:
   - Read the error logs carefully
   - Identify the root cause(s) of failures
   - Fix all issues found in the logs
   - Run the same verification commands locally that the CI runs to ensure fixes work
   - If fixes are successful, inform the user

## Output Format

- Use clear formatting with status indicators (✓ for success, ✗ for failure)
- Group related information together
- Highlight error messages prominently
- Provide actionable next steps

## Notes

- The workflow file is `ci.yml` in `.github/workflows/`
- Run the same verification commands locally that the CI workflow runs to confirm fixes work
