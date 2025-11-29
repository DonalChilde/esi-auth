# Dev workflow notes

## Feature dev steps

 - Ensure dev branch is current!
 - make a feature branch from the dev branch
 - `scriv create` to make a scriv fragment. Update fragment with expected feature details.
 - code the feature.
 - ensure tests are written and pass.
 - update docs.
 - update scriv fragment with ACTUAL changes.
 - merge feature branch to dev


 # Release steps

 - Ensure dev branch is current!
 - Make a release branch from the dev branch
 - Make a PR for the release branch if using GitHub PRs. ENSURE USING THE DEV AND FEATURE BRANCHES!
 - Update the version in pyproject.toml, and in the `__init__.py` file
 - Use `scriv collect` to update changelog. Check and edit as necessary.
   - NOTES ABOUT EDITING CHANGELOG FILE
 - ensure tests pass
 - check docs are up to date.
 - tag the release using `0.0.0` format `git tag -a <tag_name> -m "Tag message"`
 - push tag to origin with `git push origin <tagname>`
 - Ensure local branch pushed to origin
 - Accept PR, and merge to dev. ENSURE MERGING TO THE CORRECT BRANCH!
 - If not using a PR through Github, merge feature branch into dev.
 - Merge dev into main
 - make Github Release