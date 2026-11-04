export const meta = {
  name: 'web-lib-tests',
  description: 'Write or update Vitest tests for web/lib, one agent per source file, then run the whole web suite',
  whenToUse: 'After files in web/lib are added or changed. Pass an array of paths as args to cover only those files.',
  phases: [
    { title: 'Discover', detail: 'list the source files in web/lib' },
    { title: 'Write tests', detail: 'one agent per source file, each owning one test file' },
    { title: 'Check', detail: 'full test run, typecheck and a look at what changed' },
  ],
}

const FILES_SCHEMA = {
  type: 'object',
  properties: { files: { type: 'array', items: { type: 'string' } } },
  required: ['files'],
}

const RESULT_SCHEMA = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    test_file: { type: 'string' },
    tests_passed: { type: 'number' },
    tests_failed: { type: 'number' },
    not_covered: {
      type: 'array',
      items: { type: 'string' },
      description: 'Exports or branches left untested, each with the reason',
    },
    suspected_bugs: {
      type: 'array',
      description: 'Source behaviour that looks wrong. Not fixed and not pinned by a test.',
      items: {
        type: 'object',
        properties: {
          location: { type: 'string' },
          input: { type: 'string' },
          actual: { type: 'string' },
          expected: { type: 'string' },
          why: { type: 'string' },
        },
        required: ['location', 'input', 'actual', 'expected', 'why'],
      },
    },
  },
  required: ['file', 'test_file', 'tests_passed', 'tests_failed', 'not_covered', 'suspected_bugs'],
}

const CHECK_SCHEMA = {
  type: 'object',
  properties: {
    test_files: { type: 'number' },
    tests_passed: { type: 'number' },
    tests_failed: { type: 'number' },
    typecheck_passed: { type: 'boolean' },
    changed_paths: { type: 'array', items: { type: 'string' } },
    unexpected_changes: {
      type: 'array',
      items: { type: 'string' },
      description: 'Changed paths under web/ other than *.test.ts files in web/lib',
    },
    failures: { type: 'array', items: { type: 'string' } },
  },
  required: ['test_files', 'tests_passed', 'tests_failed', 'typecheck_passed', 'changed_paths', 'unexpected_changes', 'failures'],
}

const isSource = f => /^web\/lib\/.+\.tsx?$/.test(f) && !/\.(test|d)\.tsx?$/.test(f)

const testPrompt = file => {
  const testFile = file.replace(/\.tsx?$/, '.test.ts')
  const fromWeb = testFile.replace(/^web\//, '')
  return `Write Vitest tests for ${file}, from the root of this repository. Your only output file is ${testFile}.

If ${testFile} already exists, read it first: keep the tests that still hold, update the ones the source has outgrown, and add what is missing. Do not start over.

Setup, already done in web/vitest.config.mts: node environment, the "@/" alias, and server-only resolved to its empty file. Import describe, it, expect and vi from "vitest"; globals are off.

What to test:
- Every exported function and every branch that changes the result. Read the comments in the source and how its callers in web/app and web/components use it. Those define the intended behaviour, including null and missing values, boundaries such as "on the target counts as met", and rounding.
- Assert exact values. No snapshots.
- Do not test types, and do not test private helpers directly. Reach them through the exports.

Rules:
- Change nothing except ${testFile}. Do not edit source, config, package files or other tests. Do not run git commands that change anything.
- If the source looks wrong, do not fix it and do not write a test that pins the wrong output. Leave that case out and report it in suspected_bugs, with the input, the actual and expected results, and why you think it is wrong. Run the input first, in a throwaway test you delete afterwards, and report the output you saw, not what you worked out by reading. If the output turns out to be correct, it is not a bug: write the test.
- Tests must be deterministic and offline: no network, no database, no real clock.
- Never read the repository's .env or any real token. If the file reads the environment or the disk, mock node:fs, use vi.stubEnv with made-up values such as "test-token", and stub fetch with vi.stubGlobal. Restore all of it after each test.

Before you finish, from web/:
- npm test -- ${fromWeb} must pass.
- npx tsc --noEmit --incremental false must report nothing in ${fromWeb}. Other agents are writing other test files at the same time, so ignore errors in those.

Return file as ${file} and test_file as ${testFile}, with the counts from your last run.`
}

phase('Discover')
let files
if (Array.isArray(args) && args.length) {
  files = args
} else {
  const found = await agent(
    `From the repository root, run: find web/lib -type f \\( -name '*.ts' -o -name '*.tsx' \\) | sort
Return every path exactly as printed.`,
    { label: 'list web/lib', schema: FILES_SCHEMA, effort: 'low' },
  )
  files = found ? found.files : []
}
const sources = files.filter(isSource)
const dropped = files.filter(f => !isSource(f))
if (dropped.length) log(`Skipped ${dropped.length} path(s) that are not web/lib source files: ${dropped.join(', ')}`)
if (!sources.length) throw new Error('No source files found in web/lib')
log(`Covering ${sources.length} file(s): ${sources.join(', ')}`)

phase('Write tests')
const results = await parallel(
  sources.map(file => () => agent(testPrompt(file), { label: `tests:${file}`, phase: 'Write tests', schema: RESULT_SCHEMA })),
)
const missing = sources.filter((_, i) => !results[i])
if (missing.length) log(`No result from: ${missing.join(', ')}`)

phase('Check')
const check = await agent(
  `Check the web test suite. Change nothing.
From web/, run npm test, then npm run typecheck. From the repository root, run git status --short.
Report the counts, and in failures the name and error of each failing test or type error.
In changed_paths list every path git reports. In unexpected_changes list those under web/ that are not *.test.ts files in web/lib.`,
  { label: 'full run', phase: 'Check', schema: CHECK_SCHEMA, effort: 'low' },
)

return { results: results.filter(Boolean), missing, check }
