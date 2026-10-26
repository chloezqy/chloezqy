# Contribution Piggy

A hand-drawn pixel pig, a contribution-aware route planner, and a native SVG animation renderer. Python 3.12+; **no runtime packages**. Visitors receive an ordinary animated image, with no JavaScript, fonts, tracking, or interactive embed.

## Regenerate locally

```sh
python3 scripts/piggy.py --username chloezqy
python3 -m unittest discover -s tests -v
```

With `GH_TOKEN` or `GITHUB_TOKEN`, the fetcher uses GitHub GraphQL and records actual contribution counts and quartiles. Without a token, it reads GitHub's own public contribution calendar and records the actual quartile levels (not invented counts). HTTP/API errors or malformed calendars fail the build, leaving the previous published image intact. Private activity follows GitHub's visibility and token permissions.

For an offline rebuild from the checked-in real data snapshot:

```sh
python3 scripts/piggy.py --data dist/contributions.json
```

Open `dist/piggy-light.svg` and `dist/piggy-dark.svg` in a browser. The four standalone sprites are in `assets/`; their source of truth is `sprite()` in `scripts/piggy.py`. Colors, grid spacing, walking speed and eating beats are defined in that script.

## GitHub setup

Commit these files to the default `main` branch of `chloezqy/chloezqy`. The initial push triggers **Feed the contribution piggy**. It also runs daily at 07:23 UTC, and can be run from **Actions → Feed the contribution piggy → Run workflow**. No personal access token or repository secrets are needed: the workflow uses `github.token` with `contents: write`.

The workflow creates/replaces the dedicated `output` branch with the two SVGs and data snapshot; do not store hand-edited files there. `main` contains all source and an initial preview in `dist/`. The README uses raw URLs on `output` and a `<picture>` for theme selection. Repository rules must allow Actions to write `output`; the repository must be public for anonymous profile visitors. If Actions is disabled, enable it in repository settings. GitHub can disable scheduled runs after 60 days without repository activity; a manual run or qualifying repository activity can restore the schedule. Cron times can be delayed by GitHub.

## Animation design

The route greedily seeks the nearest uneaten contribution, with contribution intensity breaking ties. It walks in adjacent horizontal/vertical steps and eats snacks encountered on the way. Unlike a snake, a pig has no trailing body or self-collision constraint, so snake tunnel solving would add complexity without improving this route. It returns to its starting square before the calendar regrows. A shared timeline controls movement, direction, lifted steps, happy eyes and the eating squash/stretch, so the loop has no position jump. Empty calendars still show an idle pig and a valid looping timeline.

Each output is a self-contained SVG using native SMIL `<animate>` and `<animateTransform>`. There are no CSS keyframes or scripts. Static SVG viewers show the initial calendar and pig. A GIF is unnecessary while native image animation works; if a future GitHub proxy/browser regression strips SMIL, render this same timeline to GIF and change the README image URLs rather than introducing a scripted embed.

## Research and validation

Reference: [Platane/snk](https://github.com/Platane/snk), its [GraphQL contribution fetcher](https://github.com/Platane/snk/blob/main/packages/github-user-contribution/index.ts), and [solver explanation](https://github.com/Platane/snk/blob/main/packages/solver/README.md). These informed the calendar coordinates, fetch shape, nearest-target routing and return-to-start loop. This implementation uses original renderer, artwork and routing code; no snk code or package is copied or required.

Automated tests cover empty/dense/sparse calendars, complete snack coverage, adjacent walking, exact loop closure, invalid input, SVG XML parsing, strictly increasing animation times, and consistent native animation keyframes. The optional browser check below verifies actual image animation and samples the eating and loop-reset states in Chromium. It is a development tool only:

```sh
python3 -m pip install playwright
python3 -m playwright install chromium
python3 scripts/check_browser.py
```

Local image playback is not a substitute for checking GitHub's image proxy. After publishing, verify the profile README in light and dark mode, confirm the pig moves without clicking, and inspect a successful Actions run. Safari/Firefox playback and GitHub mobile layout require their own visual checks.
