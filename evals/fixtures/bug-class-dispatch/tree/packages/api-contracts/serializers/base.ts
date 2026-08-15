// The single place the last-4 rule is implemented. See docs/pii-display-rule.md.
// Anything that emits a sensitive identifier is supposed to come through here.
export function last4(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length < 4) {
    throw new Error("last4: value shorter than 4 digits");
  }
  return `****${digits.slice(-4)}`;
}
