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

test("repository round-trips every listening-point composer field", () => {
  const repository = createListeningPointsRepository(
    memoryStorage(),
    () => "2026-08-20T12:00:00Z",
    () => "fixed-id",
  );

  const created = repository.create({
    organizationId: "demo-expo-2026",
    name: "QR rayon boissons",
    token: "rayon-boissons-fixed",
    status: "active",
    targetType: "location",
    targetName: "Rayon boissons Oran",
    ownerName: "Nadia B.",
    channels: { rating: true, text: true, audio: false, image: false },
    alertEnabled: true,
    alertThreshold: 2,
  });

  assert.deepEqual(created, {
    id: "fixed-id",
    organizationId: "demo-expo-2026",
    name: "QR rayon boissons",
    token: "rayon-boissons-fixed",
    status: "active",
    createdAt: "2026-08-20T12:00:00Z",
    scanCount: 0,
    targetType: "location",
    targetName: "Rayon boissons Oran",
    ownerName: "Nadia B.",
    channels: { rating: true, text: true, audio: false, image: false },
    alertEnabled: true,
    alertThreshold: 2,
  });
  assert.deepEqual(repository.findByToken("rayon-boissons-fixed"), created);
});

test("repository rejects a listening point without the mandatory rating channel", () => {
  const repository = createListeningPointsRepository(memoryStorage());

  assert.throws(() => repository.create({
    organizationId: "demo-expo-2026",
    name: "QR sans note",
    token: "qr-sans-note",
    status: "active",
    targetType: "service",
    targetName: "Service test",
    ownerName: "Nadia B.",
    channels: { rating: false, text: true, audio: false, image: false },
    alertEnabled: false,
    alertThreshold: 2,
  }), /note est obligatoire/i);
});

test("repository rejects feedback without a rating", () => {
  const repository = createListeningPointsRepository(memoryStorage());
  const point = repository.findByToken("produit-pilote-demo");
  assert.ok(point);

  assert.throws(() => repository.submit({
    organizationId: point.organizationId,
    listeningPointId: point.id,
    rating: null,
    text: "Message sans note",
    channels: ["text"],
    imageName: null,
    audioDurationSeconds: null,
    consent: true,
  }), /note est obligatoire/i);
});
