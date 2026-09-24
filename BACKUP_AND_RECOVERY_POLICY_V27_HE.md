# V27 Backup & Recovery Policy

- V27 is the current source of truth after final clean-extract validation.
- Keep the final V27 release ZIP in `/Ai maker/releases/`.
- Keep a separate V27 Recovery Package in `/Ai maker/backups/`.
- Recovery package must contain the exact V27 release, immediate parent V26, validation evidence, checksums, current truth and reviewer checklist.
- Never overwrite the only known-good parent release.
- Every release must have SHA-256 and clean extraction test before it becomes source of truth.
- Rights evidence itself must move to encrypted production persistence/vault before public launch; V27 reviewer implementation currently keeps creator/control-plane state in process memory.
