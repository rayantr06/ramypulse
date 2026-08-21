import { LETICIA_DEMO_STORAGE_PREFIX } from "./leticiaDemoState";

const LISTENING_POINTS_STORAGE_KEY = `${LETICIA_DEMO_STORAGE_PREFIX}listening-points`;
const LISTENING_POINT_SUBMISSIONS_STORAGE_KEY = `${LETICIA_DEMO_STORAGE_PREFIX}listening-point-submissions`;

export type ListeningPointStatus = "active" | "paused" | "closed";

export type ListeningPoint = {
  id: string;
  organizationId: string;
  name: string;
  token: string;
  status: ListeningPointStatus;
  createdAt: string;
  scanCount: number;
};

export type ListeningPointCreateInput = {
  organizationId: string;
  name: string;
  token: string;
  status?: ListeningPointStatus;
};

export type ListeningPointSubmissionInput = {
  organizationId: string;
  listeningPointId: string;
  rating: number;
  text: string;
  channels: string[];
  imageName: string | null;
  audioDurationSeconds: number | null;
  consent: boolean;
};

export type ListeningPointSubmission = ListeningPointSubmissionInput & {
  id: string;
  createdAt: string;
  validationStatus: "pending";
};

export interface ListeningPointsRepository {
  list(organizationId: string): ListeningPoint[];
  findByToken(token: string): ListeningPoint | null;
  create(input: ListeningPointCreateInput): ListeningPoint;
  setStatus(id: string, status: ListeningPointStatus): ListeningPoint;
  recordScan(token: string): void;
  submit(input: ListeningPointSubmissionInput): ListeningPointSubmission;
  listSubmissions(listeningPointId: string): ListeningPointSubmission[];
}

const seedListeningPoints: readonly ListeningPoint[] = [
  {
    id: "lp_produit_pilote_demo",
    organizationId: "demo-expo-2026",
    name: "Produit pilote 1 L",
    token: "produit-pilote-demo",
    status: "active",
    createdAt: "2026-08-20T09:00:00Z",
    scanCount: 0,
  },
  {
    id: "lp_stand_oran_demo",
    organizationId: "demo-expo-2026",
    name: "Stand dégustation Oran",
    token: "stand-oran-demo",
    status: "active",
    createdAt: "2026-08-20T09:05:00Z",
    scanCount: 0,
  },
  {
    id: "lp_magasin_alger_demo",
    organizationId: "demo-expo-2026",
    name: "Magasin pilote Alger",
    token: "magasin-alger-demo",
    status: "paused",
    createdAt: "2026-08-20T09:10:00Z",
    scanCount: 0,
  },
];

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function parseStoredArray<T>(storage: Pick<Storage, "getItem">, key: string, fallback: T[]): T[] {
  try {
    const value = storage.getItem(key);
    if (!value) return clone(fallback);
    const parsed: unknown = JSON.parse(value);
    return Array.isArray(parsed) ? parsed as T[] : clone(fallback);
  } catch {
    return clone(fallback);
  }
}

function createInMemoryStorage(): Storage {
  const values = new Map<string, string>();

  return {
    get length() {
      return values.size;
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => Array.from(values.keys())[index] ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, value),
  };
}

function getBrowserStorage(): Storage {
  if (typeof window === "undefined") return createInMemoryStorage();

  try {
    return window.localStorage;
  } catch {
    return createInMemoryStorage();
  }
}

export function createListeningPointsRepository(
  storage: Pick<Storage, "getItem" | "setItem">,
  clock: () => string = () => new Date().toISOString(),
  makeId: () => string = () => crypto.randomUUID(),
): ListeningPointsRepository {
  const readPoints = () => parseStoredArray(storage, LISTENING_POINTS_STORAGE_KEY, [...seedListeningPoints]);
  const readSubmissions = () => parseStoredArray<ListeningPointSubmission>(storage, LISTENING_POINT_SUBMISSIONS_STORAGE_KEY, []);
  const writePoints = (points: ListeningPoint[]) => storage.setItem(LISTENING_POINTS_STORAGE_KEY, JSON.stringify(points));
  const writeSubmissions = (submissions: ListeningPointSubmission[]) => storage.setItem(LISTENING_POINT_SUBMISSIONS_STORAGE_KEY, JSON.stringify(submissions));

  return {
    list(organizationId) {
      return readPoints().filter((point) => point.organizationId === organizationId);
    },
    findByToken(token) {
      return readPoints().find((point) => point.token === token) ?? null;
    },
    create(input) {
      const points = readPoints();
      if (points.some((point) => point.token === input.token)) {
        throw new Error("Un point d'écoute utilise déjà ce jeton QR.");
      }

      const point: ListeningPoint = {
        id: makeId(),
        organizationId: input.organizationId,
        name: input.name,
        token: input.token,
        status: input.status ?? "active",
        createdAt: clock(),
        scanCount: 0,
      };
      writePoints([...points, point]);
      return point;
    },
    setStatus(id, status) {
      const points = readPoints();
      const point = points.find((item) => item.id === id);
      if (!point) throw new Error("Point d'écoute introuvable.");

      const updated = { ...point, status };
      writePoints(points.map((item) => item.id === id ? updated : item));
      return updated;
    },
    recordScan(token) {
      const points = readPoints();
      const point = points.find((item) => item.token === token);
      if (!point) throw new Error("Point d'écoute introuvable.");
      writePoints(points.map((item) => item.id === point.id ? { ...item, scanCount: item.scanCount + 1 } : item));
    },
    submit(input) {
      const point = readPoints().find((item) => item.id === input.listeningPointId);
      if (!point || point.organizationId !== input.organizationId) {
        throw new Error("Point d'écoute introuvable pour cette organisation.");
      }
      if (!point.status || point.status !== "active") {
        throw new Error("Ce point d'écoute n'accepte plus de retours.");
      }
      if (!input.consent) throw new Error("Le consentement est requis.");

      const submission: ListeningPointSubmission = {
        ...input,
        id: makeId(),
        createdAt: clock(),
        validationStatus: "pending",
      };
      writeSubmissions([...readSubmissions(), submission]);
      return submission;
    },
    listSubmissions(listeningPointId) {
      return readSubmissions().filter((submission) => submission.listeningPointId === listeningPointId);
    },
  };
}

export const listeningPointsRepository = createListeningPointsRepository(getBrowserStorage());
