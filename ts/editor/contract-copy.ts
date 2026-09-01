/** Return an independent copy of generated, JSON-compatible contract data. */
export function copyContractValue<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map(copyContractValue) as T;
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, entry]) => [key, copyContractValue(entry)])
    ) as T;
  }
  return value;
}
