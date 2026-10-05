# Setup (5 minutes)

Your username (akshat-aetroiddestroyer) and your dot portrait are already built in.

1. Create a PUBLIC repo named exactly `akshat-aetroiddestroyer` (same as your username) and tick "Add a README".
2. Upload everything in this folder to that repo, keeping the folder structure
   (README.md, assets/, scripts/, .github/workflows/).
3. Your LinkedIn, Instagram and X links are already filled in.
4. Stats workflow:
   - GitHub > Settings > Developer settings > Personal access tokens (classic)
     Scopes: `repo`, `read:user`. Copy the token.
   - Your profile repo > Settings > Secrets and variables > Actions > New secret
     Name: `METRICS_TOKEN`, value: the token.
   - Actions tab > Metrics > Run workflow. It replaces assets/metrics.languages.svg.
5. Profile page > Customize your pins > pick your 4-6 best repos.
