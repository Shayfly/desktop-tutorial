"""Evidence lines a reviewer can read WITHOUT log access: GitHub turns `::notice` lines into check-run annotations
(GET /repos/{repo}/check-runs/{job_id}/annotations). pytest captures stdout, so tests append the lines to the file
named by OMNI_EVIDENCE_NOTICES and a workflow step prints it. Outside CI this is a no-op."""
import os
import re


def notice(title: str, message: str) -> None:
    path = os.getenv('OMNI_EVIDENCE_NOTICES', '').strip()
    if not path:
        return
    clean = lambda s: re.sub(r'[\r\n%:,]+', ' ', str(s)).strip()[:900]
    with open(path, 'a', encoding='utf-8') as f:
        f.write(f'::notice title={clean(title)}::{clean(message)}\n')
