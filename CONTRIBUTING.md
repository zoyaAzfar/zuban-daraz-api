# Contributing

Thanks for helping! There are three ways to contribute.

## 1. Correct a proverb (data)

Please use the submit/edit forms on the site: **zubandaraz.org**. Every submission is reviewed before going live, and approved changes appear in the API and in the next data export.

Please don't open pull requests that edit `data/proverbs.*`. Those files are regenerated from the database.

## 2. Report a problem

Open a GitHub issue for a wrong translation or theme, an API bug, or a missing language. Include the proverb's `id` where possible.

## 3. Improve the code

Pull requests are welcome for the Python client (`src/zubandaraz`), the Worker (`worker/worker.js`), and the docs. Please keep the client dependency-light, and describe what you changed and why in the PR.

## Themes

Themes are assigned automatically from English translations and then reviewed. If you think a proverb has the wrong theme, open an issue with its `id` and the theme you'd suggest.
