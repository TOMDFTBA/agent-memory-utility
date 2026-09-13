// Execute upstream's checked-in pure JS normalizer, not the Agent platform.
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
const source = resolve(process.argv[2], 'src/context/memory/edgeclaw-memory-core/lib/message-utils.js');
const { normalizeMessages } = await import(pathToFileURL(source).href);
const history = [
  { id: 'u1', role: 'user', content: 'The first three digits of the access code are 123.' },
  { id: 'a1', role: 'assistant', content: 'Recorded the first part.' },
  { id: 'u2', role: 'user', content: 'The last three digits of the access code are 456.' },
  { id: 'a2', role: 'assistant', content: 'Recorded the second part.' },
];
const cases = [
  ['last_turn', { captureStrategy: 'last_turn', includeAssistant: true, maxMessageChars: 6000 }, ['u2', 'a2']],
  ['full_session', { captureStrategy: 'full_session', includeAssistant: true, maxMessageChars: 6000 }, ['u1', 'a1', 'u2', 'a2']],
  ['user_only', { captureStrategy: 'full_session', includeAssistant: false, maxMessageChars: 6000 }, ['u1', 'u2']],
];
const probes = cases.map(([probe_id, options, expected]) => {
  const output = normalizeMessages(history, options);
  if (JSON.stringify(output.map(x => x.msgId)) !== JSON.stringify(expected)) throw Error('Capture selection mismatch');
  return { probe_id, options, output, passed: true };
});
const output = normalizeMessages([{ role: 'user', content: 'abcdefghij' }],
  { captureStrategy: 'full_session', includeAssistant: false, maxMessageChars: 5 });
if (output[0]?.content !== 'abcde...') throw Error('Character truncation mismatch');
probes.push({ probe_id: 'character_truncation', output, passed: true });
console.log(JSON.stringify({ probes, runtime: process.version, model_calls: 0,
  execution: 'Pinned upstream lib/message-utils.js normalizeMessages',
  interpretation: 'Single capture input only; not accumulated storage, extraction, Dream, or downstream QA. Compare the recorded runtime with package Node >=22.13 <23 requirement; no full-platform compatibility claim.' }));
