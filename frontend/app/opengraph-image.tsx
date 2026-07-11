import { ImageResponse } from "next/og";
import { readFileSync } from "node:fs";
import { join } from "node:path";

export const alt = "Astalink AI — Investasi IDX Berbasis AI";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OpengraphImage() {
  const logoBuffer = readFileSync(join(process.cwd(), "public", "astalink.png"));
  const logoBase64 = `data:image/png;base64,${logoBuffer.toString("base64")}`;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#0a0a0a",
          backgroundImage:
            "radial-gradient(circle at 25% 20%, rgba(34,197,94,0.16), transparent 55%), radial-gradient(circle at 80% 85%, rgba(34,197,94,0.10), transparent 50%)",
        }}
      >
        <img src={logoBase64} width={168} height={168} alt="" style={{ marginBottom: 32 }} />
        <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
          <span style={{ fontSize: 76, fontWeight: 800, color: "#fafafa", letterSpacing: "-0.02em" }}>
            Astalink
          </span>
          <span
            style={{
              fontSize: 26,
              fontWeight: 900,
              color: "#22c55e",
              letterSpacing: "0.14em",
              textTransform: "uppercase",
            }}
          >
            AI
          </span>
        </div>
        <span style={{ fontSize: 30, color: "#a3a3a3", marginTop: 22, maxWidth: 820, textAlign: "center" }}>
          Investasi saham IDX dengan AI multi-agen &amp; kepatuhan OJK otomatis
        </span>
      </div>
    ),
    { ...size },
  );
}
