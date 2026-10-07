# Setup (5 minutes)

Your username, links and dot portrait are already built in.

1. Create a PUBLIC repo named exactly `akshat-aetroiddestroyer` and tick "Add a README".
2. Upload everything in this folder (keep the structure: README.md, assets/, scripts/, .github/workflows/).
3. Stats workflow:
   - GitHub > Settings > Developer settings > Personal access tokens (classic); scopes `repo`, `read:user`.
   - Repo > Settings > Secrets and variables > Actions > New secret: `METRICS_TOKEN` = the token.
   - Actions tab > Metrics > Run workflow (replaces assets/metrics.languages.svg).
4. Pin your best 4-6 repos on your profile page.

## Rebuilding the hero (only if you change something)
    pip install -r scripts/requirements.txt
    python scripts/prepare_portrait.py my_photo.jpg 0 285 335 800   # new photo: x0 y0 x1 y1 crop around head+shoulders
    python scripts/generate_assets.py                                # rebuilds assets/*.svg
Edit your details at the top of scripts/generate_assets.py. If you change the SVG, GitHub caches images:
hard-refresh (Ctrl+Shift+R) or rename the file (e.g. hero.v2.svg) and update README.md.

Tip for a sharper face: a front-facing, evenly lit photo with a plain background works best.
