import assert from "node:assert/strict";
import test from "node:test";

import {
  LETICIA_DEMO_SCENARIO,
  validateLeticiaDemoScenario,
} from "../client/src/lib/leticiaDemoScenario";
import {
  LETICIA_DEMO_STORAGE_PREFIX,
  resetLeticiaDemoState,
} from "../client/src/lib/leticiaDemoState";

test("Leticia scenario is internally coherent and auditable", () => {
  assert.deepEqual(validateLeticiaDemoScenario(), []);
  assert.ok(LETICIA_DEMO_SCENARIO.mentions.some((item) => item.language === "darija_arabizi"));
  assert.ok(LETICIA_DEMO_SCENARIO.mentions.some((item) => item.language === "darija_arabe"));
  assert.ok(LETICIA_DEMO_SCENARIO.mentions.every((item) => item.sourceUrl?.startsWith("https://example.invalid/")));
  assert.ok(LETICIA_DEMO_SCENARIO.signals.every((signal) => signal.evidenceIds.length > 0));
  assert.match(LETICIA_DEMO_SCENARIO.signals[0]!.title, /disponibilit/i);
  assert.match(LETICIA_DEMO_SCENARIO.signals[0]!.territory ?? "", /Oran/i);
  assert.deepEqual(LETICIA_DEMO_SCENARIO.authorizedInputChannels, ["facebook", "google_maps", "audio", "youtube"]);
  assert.ok(LETICIA_DEMO_SCENARIO.monitors.every((monitor) => !monitor.sources.includes("tiktok")));
  assert.ok(LETICIA_DEMO_SCENARIO.mentions.every((mention) => mention.source !== "tiktok"));
  assert.ok(LETICIA_DEMO_SCENARIO.overview.sourceHealth.every((source) => source.source !== "tiktok"));
  assert.equal(
    LETICIA_DEMO_SCENARIO.overview.collectedDocuments,
    LETICIA_DEMO_SCENARIO.overview.sourceHealth.reduce((total, source) => total + source.collectedDocuments, 0),
  );
});

test("reset removes only Leticia demo keys", () => {
  const values = new Map([[`${LETICIA_DEMO_STORAGE_PREFIX}points`, "[]"], ["unrelated", "keep"]]);
  const storage = {
    get length() { return values.size; },
    key(index: number) { return [...values.keys()][index] ?? null; },
    removeItem(key: string) { values.delete(key); },
  };
  resetLeticiaDemoState(storage);
  assert.equal(values.has(`${LETICIA_DEMO_STORAGE_PREFIX}points`), false);
  assert.equal(values.get("unrelated"), "keep");
});
