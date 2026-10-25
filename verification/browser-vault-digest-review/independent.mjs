// Review-only, independently ordered bytes. No product source is imported.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';

const fields = ['mode', 'public_origin', 'profile_id', 'profile_version', 'issuer',
  'client_id', 'api_audience', 'authorization_endpoint', 'token_endpoint',
  'id_token_jwks_endpoint', 'redirect_uri', 'client_auth_method',
  'client_credential_ref', 'session_vault_ref', 'scope', 'response_mode',
  'response_iss_required', 'transaction_seconds', 'session_idle_seconds',
  'return_path', 'failure_path'];
const b = value => Buffer.from(value, 'base64');
const lp = value => { const size = Buffer.alloc(4); size.writeUInt32BE(value.length); return Buffer.concat([size, value]); };
const u64 = value => { const out = Buffer.alloc(8); out.writeBigUInt64BE(BigInt(value)); return out; };
const aad = (key, c) => {
  let domain, parts;
  if (c.purpose === 'attempt') {
    domain = 'mixer.browser.attempt.v1\0';
    parts = [Buffer.from([3]), b(c.state_digest), b(c.browser_id), b(c.cookie_digest),
      u64(c.epoch), u64(c.revision), Buffer.from(c.generation), b(c.config_digest),
      Buffer.from(c.profile_id), u64(c.profile_version), Buffer.from(c.issuer),
      Buffer.from(c.client_id), Buffer.from(c.redirect_uri), u64(c.expires_at)];
  } else {
    domain = 'mixer.browser.vault.v1\0';
    parts = [Buffer.from([c.purpose === 'preauth' ? 1 : 2]), b(c.browser_id),
      b(c.cookie_digest), b(c.csrf_digest), u64(c.epoch), u64(c.revision),
      Buffer.from(c.generation), u64(c.vault_generation), b(c.config_digest),
      Buffer.from(c.profile_id), u64(c.profile_version)];
    if (c.purpose === 'preauth') parts.push(Buffer.from([0]));
    else parts.push(Buffer.from([1]), Buffer.from(c.principal_id), Buffer.from(c.family_id),
      Buffer.from(c.credential_ref), u64(c.credential_revision));
  }
  return Buffer.concat([Buffer.from(domain), ...[Buffer.from([1]), Buffer.from(key.id), ...parts].map(lp)]);
};
const envelope = (purpose, csrf, verifier, token) => purpose === 'preauth'
  ? Buffer.concat([Buffer.from([1]), lp(Buffer.from(csrf))])
  : purpose === 'active' ? Buffer.concat([Buffer.from([2]), lp(Buffer.from(csrf)), lp(Buffer.from(token))])
    : Buffer.concat([Buffer.from([3]), lp(Buffer.from(verifier))]);
const encrypt = (key, iv, associated, plain) => {
  const cipher = crypto.createCipheriv('aes-256-gcm', b(key.bytes), iv, {authTagLength: 16});
  cipher.setAAD(associated);
  const ciphertext = Buffer.concat([cipher.update(plain), cipher.final()]);
  return {version: 1, key_id: key.id, iv: iv.toString('base64'),
    tag: cipher.getAuthTag().toString('base64'), ciphertext: ciphertext.toString('base64')};
};
const fixture = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
if (process.argv[2] === 'generate') {
  for (const item of fixture.configs) {
    const canonical = Buffer.concat([Buffer.from('mixer.browser.configuration.v1\0'),
      Buffer.from(JSON.stringify([1, fields.map(name => [name, item.values[name]])]))]);
    item.canonical = canonical.toString('base64');
    item.sha256 = crypto.createHash('sha256').update(canonical).digest('hex');
  }
  let ordinal = 0;
  fixture.vectors = fixture.contexts.map(context => {
    const associated = aad(fixture.key, context);
    const plaintext = envelope(context.purpose, fixture.csrf, fixture.verifier, fixture.access_token);
    const iv = Buffer.alloc(12); iv.writeUInt32BE(++ordinal, 8);
    return {purpose: context.purpose, aad: associated.toString('base64'),
      plaintext: plaintext.toString('base64'), sealed: encrypt(fixture.key, iv, associated, plaintext)};
  });
  fixture.malformed = [];
  for (const context of fixture.contexts) {
    const raw = envelope(context.purpose, fixture.csrf, fixture.verifier, fixture.access_token);
    const alias = fixture.csrf.slice(0, 42) + 'B';
    const bad = [Buffer.alloc(0), Buffer.from([0]), Buffer.from([4]), raw.subarray(0, raw.length - 1),
      Buffer.concat([raw, Buffer.from([0])]), Buffer.concat([Buffer.from([raw[0], 255, 255, 255, 255]), raw.subarray(5)]),
      Buffer.concat([Buffer.from([raw[0], 0, 0, 0, 0]), raw.subarray(5)]),
      envelope(context.purpose === 'attempt' ? 'preauth' : 'attempt', fixture.csrf, fixture.verifier, fixture.access_token),
      Buffer.concat([Buffer.from([raw[0], 43, 0, 0, 0]), raw.subarray(5)]),
      envelope(context.purpose, alias, alias, 'a=b'),
      envelope(context.purpose, fixture.verifier, fixture.verifier, 'a')];
    if (context.purpose === 'attempt') bad.pop(); // valid verifier under the correct attempt would be accepted.
    if (context.purpose === 'active') {
      for (const token of ['', '=', 'a=b', 'a b', 'a\nb', 'é', 'x'.repeat(4090)])
        bad.push(envelope('active', fixture.csrf, fixture.verifier, token));
      bad.push(Buffer.concat([raw.subarray(0, 48), Buffer.from([255, 255, 255, 255])]));
    }
    for (const plain of bad) {
      const iv = Buffer.alloc(12); iv.writeUInt32BE(++ordinal, 8);
      fixture.malformed.push({purpose: context.purpose, plaintext: plain.toString('base64'),
        sealed: encrypt(fixture.key, iv, aad(fixture.key, context), plain)});
    }
  }
  fs.writeFileSync(process.argv[4], JSON.stringify(fixture, null, 2) + '\n');
  console.log(JSON.stringify({configuration_byte_vectors: fixture.configs.length,
    independent_aad_envelope_vectors: fixture.vectors.length,
    authenticated_malformed_vectors: fixture.malformed.length}));
} else if (process.argv[2] === 'verify') {
  const result = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
  assert.equal(result.length, 3);
  for (const item of result) {
    const c = fixture.contexts.find(c => c.purpose === item.purpose);
    const associated = aad(fixture.key, c);
    const expected = envelope(c.purpose, fixture.csrf, fixture.verifier, fixture.access_token);
    assert.equal(item.aad, associated.toString('base64'));
    const decipher = crypto.createDecipheriv('aes-256-gcm', b(fixture.key.bytes), b(item.sealed.iv), {authTagLength: 16});
    decipher.setAAD(associated); decipher.setAuthTag(b(item.sealed.tag));
    assert.deepEqual(Buffer.concat([decipher.update(b(item.sealed.ciphertext)), decipher.final()]), expected);
    assert.deepEqual(encrypt(fixture.key, b(item.sealed.iv), associated, expected), item.sealed);
  }
  const zero = {id: 'kat', bytes: Buffer.alloc(32).toString('base64')};
  const kat = encrypt(zero, Buffer.alloc(12), Buffer.alloc(0), Buffer.alloc(16));
  assert.equal(b(kat.ciphertext).toString('hex'), 'cea7403d4d606b6e074ec5d3baf39d18');
  assert.equal(b(kat.tag).toString('hex'), 'd0d1c8a799996bf0265b98b5d48ab919');
  console.log(JSON.stringify({product_to_node_open_and_exact_reseal: result.length, aes256gcm_known_answer: 1}));
} else throw new Error('unknown review operation');
