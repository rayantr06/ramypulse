import assert from "node:assert/strict";
import test from "node:test";

import { createListeningPointsRepository } from "../client/src/lib/listeningPoints";

function memoryStorage(): Storage {
  const values = new Map<string, string>();

  return {
    get length() {
      return values.size;
    },
    clear() {
      values.clear();
    },
    getItem(key) {
      return values.get(key) ?? null;
    },
    key(index) {
      return [...values.keys()][index] ?? null;
    },
    removeItem(key) {
      values.delete(key);
    },
    setItem(key, value) {
      values.set(key, value);
    },
  };
}

test("repository records a same-origin QR submission as pending", () => {
  const repository = createListeningPointsRepository(
    memoryStorage(),
    () => "2026-08-20T12:00:00Z",
    () => "fixed-id",
  );
  const point = repository.findByToken("produit-pilote-demo");
  assert.ok(point);

  const submission = repository.submit({
    organizationId: point.organizationId,
    listeningPointId: point.id,
    rating: 2,
    text: "Ma l9itch le produit fi Oran.",
    channels: ["text"],
    imageName: null,
    audioDurationSeconds: null,
    consent: true,
  });

  assert.equal(submission.validationStatus, "pending");
  assert.equal(repository.listSubmissions(point.id).length, 1);
});

test("repository isolates points by organization", () => {
  const repository = createListeningPointsRepository(
    memoryStorage(),
    () => "2026-08-20T12:00:00Z",
    () => "fixed-id",
  );

  assert.ok(repository.list("demo-expo-2026").length > 0);
  assert.deepEqual(repository.list("another-tenant"), []);
});
