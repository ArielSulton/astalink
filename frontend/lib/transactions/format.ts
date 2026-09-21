export function idr(value: number | null | undefined): string {
  if (value == null) return "—";
  return `Rp ${value.toLocaleString("id-ID", { maximumFractionDigits: 0 })}`;
}

/** Keeps the minus sign in front of the currency symbol: -Rp 125.000. */
export function signedIdr(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value < 0 ? "-" : "+"}${idr(Math.abs(value))}`;
}

export function shares(quantity: number): string {
  return `${quantity.toLocaleString("id-ID", { maximumFractionDigits: 2 })} lembar`;
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
