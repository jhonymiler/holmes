# Optional module — cases with ciphers

Use only when the case involves ciphertext, encoding or hidden data.

## Encoding or cipher?

Encoding hides nothing: base64, hex, binary, base58, URL-encoding, decimal ASCII, Morse. Peel every layer
before suspecting cryptography. Identify the file type by its header, not its extension.

## Diagnosing a classical cipher

- **Class (100 letters, English):** vowels AEIOUY 33–47; DNRST 28–42; BCFGHLMPVW 17–31; JKQXZ 0–3. All in range
  → transposition; out of range → substitution.
- **IC** = Σ nᵢ(nᵢ−1)/(N(N−1)). English ≈ 0.067; random ≈ 0.0385. It does not change under simple substitution:
  it finds transposition while ignoring substitution.
- **Mono × poly:** a peaked distribution → one alphabet; a flat one → several. Kasiski gives the period.
- **Probable word:** only if motivated by an external circumstance. Every word tried counts as an attempt.
- **Frequency does not see everything:** acrostics, indexing and grids with nulls leave no statistical signal.
- **Block cipher** (size a multiple of 16, high entropy): without the key there is no cryptanalysis. Look for
  the key in the material.
- **Steganography:** least significant bits, colour channels, metadata, data after the end of the file,
  trailing spaces, different versions of the same image.
- **Kerckhoffs:** in a puzzle, the author wants the method to be found. Look for the hint to the method.

## Unicity

U = H(K) / D. English D ≈ 3.2 bits/letter; simple substitution U ≈ 28 letters. Below U, false keys give
plausible text and no scorer decides. Use the D of the criterion the scorer measures, not the language's.
H(K) includes the analyst's choices.

## Scorers

- Monograms and IC: robust, not very selective, false scores on short text.
- Larger n-grams and dictionaries: selective, not very robust.
- Measure before trusting: synthetics with a known key, injected error, score × error curve at the target's
  length, false rate with random keys.
- Never train the scorer on the case's material.

## Typical acceptance criteria

| Criterion | False positive per candidate | Role |
|---|---|---|
| Hash or identifier equal to the target | negligible | Confirmation; the dominant error is technical |
| Short checksum (4 bits) | 1/16 | Filter |
| 8-bit checksum | 1/256 | Filter |
| PKCS#7 padding after AES-CBC | ≈ 1/255 | Filter; in 10⁹ attempts, millions of false ones |
| "Plausible" text | measure at the target's length | Filter, never confirmation |

The final criterion needs FPR × N far below 1. Otherwise, chain an independent second stage.

## Human errors

A hand-assembled password may contain an error. Enumerable repairs: an illegible symbol, a missing character,
an extra character. Tolerating 1 error multiplies the space by roughly length × alphabet. Accept the error only
if a single mechanism explains all of them.

## Running a search

- A control with measured power in every run (`validation.md`).
- The criterion must see everything the hypothesis can produce (readable text and binary).
- Declared space = executed code.
- A local copy of a shared function is a defect. Record the instrument with `instrument`.
- Checkpoint in a long search; unbuffered log.
- Reprocessing old output with a more selective criterion is allowed; repeating the same search is not.
- Software error is systematic: rerunning does not find bugs; a second method does.
