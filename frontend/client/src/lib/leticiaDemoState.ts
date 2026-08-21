export const LETICIA_DEMO_STORAGE_PREFIX = "lidal.demo.leticia." as const;

export function resetLeticiaDemoState(
  storage: Pick<Storage, "key" | "length" | "removeItem">,
): void {
  const keys = Array.from({ length: storage.length }, (_, index) => storage.key(index))
    .filter((key): key is string => Boolean(key?.startsWith(LETICIA_DEMO_STORAGE_PREFIX)));

  keys.forEach((key) => storage.removeItem(key));
}
