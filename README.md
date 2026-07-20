# cfp — Call for Papers

Curated **Call for Papers** from reputed global AI conferences, with full
metadata. Data lives in the repo as **SOPS-encrypted YAML**; a GitHub Actions
pipeline decrypts it at build time (using a key held in GitHub Secrets) and
publishes a static site to GitHub Pages. The decryption key is never public and
the plaintext is scrubbed from the runner after each build.

## How it works

```
data/*.yaml            you edit these; SOPS encrypts the private fields
   │  (git — encrypted, public-safe)
   ▼
GitHub Actions         pulls SOPS_AGE_KEY from Secrets, decrypts in the runner
   │
   ▼
scripts/build.py       reads decrypted YAML → site/index.html + site/cfps.json
   │                   (private curation fields are dropped from the output)
   ▼
GitHub Pages           public static site
```

### What is encrypted

Only your **private curation layer** is encrypted (see `.sops.yaml`):

| Field      | Encrypted | Why |
|------------|-----------|-----|
| `notes`    | ✅ | private analysis / opinions |
| `priority` | ✅ | internal ranking |
| `contacts` | ✅ | private contact info |
| everything else (name, deadlines, links, location…) | ❌ | public CFP facts — kept plaintext so git diffs are reviewable |

Even after decryption, `scripts/build.py` **drops** the private fields from the
published site. They only help you rank/annotate entries privately.

## Adding or editing a CFP

1. Create/edit a file in `data/`, e.g. `data/cvpr-2027.yaml` (copy an existing one for the schema).
2. Encrypt it:
   ```bash
   export SOPS_AGE_KEY_FILE=$PWD/.keys/age.key
   sops --encrypt --in-place data/cvpr-2027.yaml
   ```
   To edit an already-encrypted file, use `sops data/cvpr-2027.yaml` — it
   decrypts into your editor and re-encrypts on save.
3. Commit the encrypted file and push. CI builds and deploys automatically.

## Local build

```bash
python3 -m pip install -r requirements.txt
export SOPS_AGE_KEY_FILE=$PWD/.keys/age.key
# decrypt a throwaway copy, build, inspect site/
for f in data/*.yaml; do sops -d "$f" > "$f.plain" && mv "$f.plain" "$f"; done  # ⚠ mutates in place
python3 scripts/build.py
# ...then `git checkout data/` to restore the encrypted versions.
```

See **[SETUP.md](SETUP.md)** for first-time key generation and configuring the
GitHub Secret.
