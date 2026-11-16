// Vercel "Ignored Build Step" (vercel.json ignoreCommand). Michael 2026-11-15: the $10.53 is Vercel build minutes;
// stop building previews for docs-only changes and stop previews of ci/v24-report.
//
// Exit 0 = Vercel skips the build. Exit 1 = Vercel builds. Every run prints one line saying which and why.
// Rules:
//   * production builds ONLY on a release (warehouse 111, owner 2026-11-16: there is no test environment, so an automatic
//     production deploy of every push to main put every merge in front of customers). A release is a commit whose
//     FIRST LINE (the merge commit's title) ENDS with RELEASE_MARK ("[release]"), or a deployment with
//     OMNI_RELEASE=1 set on it (a manual production deploy). Everything else on production is skipped and says why;
//     production then stays on the last released SHA until the next release;
//   * a preview of a branch in NO_PREVIEW is skipped;
//   * a preview whose whole diff against main is docs-only is skipped. The diff is read from GitHub's compare API
//     against main -- a global source, not the branch's own history (Michael's rule, 2026-11-15) -- so the first
//     push of a branch is judged on everything the branch adds, not on its last commit;
//   * anything unknown builds: no compare answer, a truncated file list (GitHub stops at 300), an empty diff, or a
//     missing variable. Building costs minutes; skipping a code change would hide it from its preview.
import { pathToFileURL } from 'node:url';

export const NO_PREVIEW = ['ci/v24-report'];
// docs/** is excluded from the deployed function by vercel.json (functions.app.py.excludeFiles), so a change there
// cannot reach the running app. CLAUDE.md is read by agents only (no code reads it).
export const DOCS_ONLY = [/^docs\//, /^CLAUDE\.md$/];
export const COMPARE_FILE_LIMIT = 300;

export const RELEASE_MARK = '[release]';
// 2026-11-16: #413's merge released by accident -- its body quoted a PR title that mentioned "[release]" in prose. The
// mark counts only as a deliberate suffix of the title line; anywhere else it is text (same rule: scripts/release_gate.py).
export function isRelease(message) {
  return String(message || '').split('\n')[0].trimEnd().endsWith(RELEASE_MARK);
}

export function decide({ env, ref, files, message = '', release = '' }) {
  if (env === 'production') {
    if (release === '1') return { build: true, reason: 'production: manual release (OMNI_RELEASE=1)' };
    if (isRelease(message)) return { build: true, reason: `production: release commit (title ends with ${RELEASE_MARK})` };
    return { build: false, reason: `production: not a release -- end the merge commit's title with ${RELEASE_MARK}, or deploy manually with OMNI_RELEASE=1` };
  }
  if (env !== 'preview') return { build: true, reason: `unknown VERCEL_ENV ${JSON.stringify(env)}: building` };
  if (NO_PREVIEW.includes(ref)) return { build: false, reason: `no previews for ${ref}` };
  if (!Array.isArray(files)) return { build: true, reason: 'diff against main unknown: building' };
  if (files.length === 0) return { build: true, reason: 'empty diff against main: building' };
  if (files.length >= COMPARE_FILE_LIMIT) return { build: true, reason: `diff has ${files.length}+ files (list may be truncated): building` };
  const paths = files.flatMap(f => [f.filename, f.previous_filename].filter(Boolean));
  const code = paths.filter(p => !DOCS_ONLY.some(rx => rx.test(p)));
  if (code.length) return { build: true, reason: `${code.length} non-docs file(s), e.g. ${code[0]}` };
  return { build: false, reason: `docs-only diff against main (${files.length} file(s))` };
}

async function changedFiles(owner, repo, sha) {
  if (!owner || !repo || !sha) return { files: null, why: 'missing VERCEL_GIT_REPO_OWNER/SLUG/COMMIT_SHA' };
  const url = `https://api.github.com/repos/${owner}/${repo}/compare/main...${sha}?per_page=${COMPARE_FILE_LIMIT}`;
  try {
    const res = await fetch(url, { headers: { Accept: 'application/vnd.github+json' }, signal: AbortSignal.timeout(10000) });
    if (!res.ok) return { files: null, why: `compare HTTP ${res.status}` };
    const body = await res.json();
    return { files: Array.isArray(body.files) ? body.files : null, why: 'compare without a file list' };
  } catch (err) {
    return { files: null, why: `compare failed: ${err.message}` };
  }
}

async function main() {
  const env = process.env.VERCEL_ENV;
  const ref = process.env.VERCEL_GIT_COMMIT_REF;
  let files = null, why = '';
  if (env === 'preview' && !NO_PREVIEW.includes(ref)) {
    ({ files, why } = await changedFiles(process.env.VERCEL_GIT_REPO_OWNER, process.env.VERCEL_GIT_REPO_SLUG,
                                         process.env.VERCEL_GIT_COMMIT_SHA));
  }
  const d = decide({ env, ref, files, message: process.env.VERCEL_GIT_COMMIT_MESSAGE || '', release: process.env.OMNI_RELEASE || '' });
  console.log(`vercel-ignore: ${d.build ? 'BUILD' : 'SKIP'} ${ref || '?'} -- ${d.reason}${files === null && why ? ` (${why})` : ''}`);
  process.exit(d.build ? 1 : 0);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
