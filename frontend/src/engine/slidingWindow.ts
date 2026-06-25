import { MAX_SNAKE_LENGTH } from "./constants";

export type SlidingWindowResult<T> = {
  items: T[];
  evicted: T | null;
};

export function applySlidingWindow<T>(
  items: T[],
  newItem: T,
  maxLength: number = MAX_SNAKE_LENGTH,
): SlidingWindowResult<T> {
  const next = [...items, newItem];
  if (next.length <= maxLength) {
    return { items: next, evicted: null };
  }
  const evicted = next.shift() ?? null;
  return { items: next, evicted };
}
