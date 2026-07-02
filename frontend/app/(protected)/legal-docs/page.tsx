"use client";
import { useEffect, useRef, useState } from "react";
import { FileText, Scale, Upload } from "lucide-react";
import { api, RegulationDoc } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

export default function LegalDocsPage() {
  const [docs, setDocs] = useState<RegulationDoc[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [docsError, setDocsError] = useState<boolean>(false);

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadSource, setUploadSource] = useState("");
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .listLegalDocs()
      .then(setDocs)
      .catch(() => { setDocsError(true); })
      .finally(() => setDocsLoading(false));
  }, []);

  async function handleUpload() {
    if (!uploadFile) return;
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(false);

    try {
      const sb = createClient();
      const {
        data: { session },
      } = await sb.auth.getSession();
      if (!session) { setUploadError("Sesi habis, silakan login ulang."); return; }

      const newDoc = await api.uploadLegalDoc(
        uploadFile,
        uploadSource || "user",
        uploadTitle || uploadFile.name,
        session.access_token,
      );
      setDocs((prev) => [newDoc, ...prev]);
      setUploadFile(null);
      setUploadSource("");
      setUploadTitle("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      setUploadSuccess(true);
      setTimeout(() => setUploadSuccess(false), 3000);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Upload gagal.";
      setUploadError(msg);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="p-8 space-y-8 max-w-4xl w-full mx-auto bg-background min-h-screen text-foreground">
      <div>
        <p className="text-muted-foreground text-[10px] font-black font-mono uppercase tracking-[0.2em] mb-1">Regulations</p>
        <h1 className="text-foreground text-2xl font-bold tracking-tight">Legal Documents</h1>
      </div>

      {/* ── Indexed docs ── */}
      <section className="space-y-3">
        <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
          Dokumen Regulasi Terindeks
        </h2>

        {docsLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-16 rounded-xl bg-card animate-pulse border border-border"
              />
            ))}
          </div>
        )}

        {!docsLoading && docsError && (
          <p className="text-xs text-rose-400 p-4 rounded-xl border border-rose-500/10 bg-rose-500/5">
            Gagal memuat daftar dokumen. Coba muat ulang halaman.
          </p>
        )}

        {!docsLoading && !docsError && docs.length === 0 && (
          <div className="flex items-center gap-3 p-5 rounded-xl border border-border bg-card text-muted-foreground">
            <Scale className="h-5 w-5 shrink-0 text-primary" />
            <p className="text-sm">
              Belum ada dokumen terindeks. Unggah dokumen pertama di bawah.
            </p>
          </div>
        )}

        {!docsLoading && docs.length > 0 && (
          <div className="space-y-2.5">
            {docs.map((doc) => (
              <div
                key={doc.id}
                className="flex items-start gap-3.5 p-4 rounded-xl border border-border bg-card hover:border-border/60 hover:bg-secondary/30 transition-all duration-200"
              >
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center border border-primary/20 mt-0.5 shrink-0">
                  <FileText className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground font-semibold truncate leading-tight">{doc.title}</p>
                  <div className="flex items-center gap-2 mt-1.5 text-[10px] text-muted-foreground font-medium">
                    <span className="px-1.5 py-0.5 rounded bg-secondary border border-border font-mono text-[9px] font-bold uppercase tracking-wider text-foreground">
                      {doc.source}
                    </span>
                    {doc.version && <span className="bg-secondary px-1.5 py-0.5 rounded text-[9px] border border-border">{doc.version}</span>}
                    <span>·</span>
                    <span className="font-mono">
                      {new Date(doc.indexed_at).toLocaleDateString("id-ID", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Upload section ── */}
      <section className="space-y-3">
        <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
          Unggah Dokumen Mandiri
        </h2>

        <div className="rounded-2xl border border-border bg-card p-6 space-y-5 shadow-xl">
          <div>
            <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">File PDF</label>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border border-dashed border-border hover:border-primary rounded-xl p-8 flex flex-col items-center gap-3 cursor-pointer bg-secondary hover:bg-primary/[0.04] transition-all duration-200"
            >
              <Upload className="h-6 w-6 text-muted-foreground" />
              <p className="text-sm text-muted-foreground font-medium">
                {uploadFile ? uploadFile.name : "Klik untuk pilih file PDF"}
              </p>
              {uploadFile && (
                <p className="text-[10px] text-muted-foreground/60 font-mono">
                  {(uploadFile.size / 1024).toFixed(0)} KB
                </p>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">Sumber</label>
              <input
                value={uploadSource}
                onChange={(e) => setUploadSource(e.target.value)}
                placeholder="cth. OJK, UUPM, user"
                className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all duration-200"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">Judul</label>
              <input
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                placeholder="Judul dokumen"
                className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all duration-200"
              />
            </div>
          </div>

          {uploadError && (
            <p className="text-xs text-rose-400 p-3.5 rounded-xl bg-rose-500/5 border border-rose-500/10">
              {uploadError}
            </p>
          )}
          {uploadSuccess && (
            <p className="text-xs text-emerald-400 p-3.5 rounded-xl bg-emerald-500/5 border border-emerald-500/10">
              Dokumen berhasil diunggah dan diindeks ke BM25.
            </p>
          )}

          <button
            onClick={handleUpload}
            disabled={!uploadFile || uploading}
            className="w-full py-3 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 hover:shadow-[0_0_16px_rgba(37,99,235,0.3)] disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed disabled:shadow-none transition-all duration-200"
          >
            {uploading ? "Mengunggah…" : "Unggah & Indeks"}
          </button>
        </div>
      </section>
    </div>
  );
}
