import assert from "node:assert/strict";
import test from "node:test";
import { runnerImport } from "vite";

const { module: codec } = await runnerImport("/src/character/appearanceCode.ts", {
  environments: { inline: { resolve: { noExternal: ["@xiuxian/character-assets"] } } },
});
const { decodeAppearance, encodeAppearance, savedAppearanceKey } = codec;

const dyed = "XX1-F-13-16-01-04-08-05-11-13-06-a483b3";
const underclothes = "XX1-M-02-05-13-12-01-00-00-00-00-0";

test("reads legacy XX1 saves and preserves the field order and storage key", () => {
  assert.equal(savedAppearanceKey, "xiuxian.appearance.v1");
  const appearance = decodeAppearance(`  ${dyed.toUpperCase()} \n`);
  assert.deepEqual(appearance, {
    body: "female",
    parts: {
      shape: "13",
      brows: "16",
      eyes: "01",
      nose: "04",
      mouth: "08",
      frontHair: "05",
      backHair: "11",
      topHair: "13",
      outfit: "06",
    },
    dye: "#a483b3",
  });
  assert.equal(encodeAppearance(appearance), dyed);
});

test("retains the legacy IDs for no hair and underclothes", () => {
  const appearance = decodeAppearance(underclothes);
  assert.deepEqual(appearance, {
    body: "male",
    parts: {
      shape: "02",
      brows: "05",
      eyes: "13",
      nose: "12",
      mouth: "01",
      frontHair: "none",
      backHair: "none",
      topHair: "none",
      outfit: "none",
    },
    dye: null,
  });
  assert.equal(encodeAppearance(appearance), underclothes);
});

test("rejects unknown parts and dye on underclothes", () => {
  assert.equal(decodeAppearance(dyed.replace("-F-13-", "-F-17-")), null);
  assert.equal(decodeAppearance(underclothes.replace(/-0$/, "-a483b3")), null);
});
