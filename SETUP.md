# One-time setup

## 1. Generate the age keypair (already done in this repo)

```bash
age-keygen -o .keys/age.key
```

- The file `.keys/age.key` holds **both** keys but is git-ignored (`.keys/`).
- The **public** key is embedded in `.sops.yaml` — safe to commit; it only lets
  people *encrypt*.
- The **private** key (the whole `.keys/age.key` file contents) is the secret.

> This repo already has a keypair. **Rotate it before going to production** —
> the private key was generated on a dev machine. To rotate: generate a new
> key, update the `age:` recipient in `.sops.yaml`, and re-encrypt every file
> with `sops updatekeys data/*.yaml`.

## 2. Add the private key to GitHub Secrets

1. Print the private key:
   ```bash
   cat .keys/age.key
   ```
2. In GitHub: **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `SOPS_AGE_KEY`
   - Value: the **full contents** of `.keys/age.key` (including the
     `AGE-SECRET-KEY-...` line).

The workflow reads it via `env: SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}`, and
SOPS picks it up automatically — the key never lands on the runner's disk.

## 3. Enable GitHub Pages

**Settings → Pages → Build and deployment → Source: GitHub Actions.**

## 4. Push

```bash
git add -A
git commit -m "Set up encrypted CFP pipeline"
git push
```

The `Build & Deploy CFP site` workflow runs on every push to `main` and
publishes to your Pages URL.

## Backup the private key

If you lose `SOPS_AGE_KEY`, you can never decrypt the data again. Store a copy
in a password manager. Losing it means re-entering all private fields from
scratch.
