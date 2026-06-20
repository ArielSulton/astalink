"use client";
import { useEffect, useRef, useState } from "react";
import { FileText, Scale, Upload } from "lucide-react";
import { api, RegulationDoc } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

export default function LegalDocsPage() {
  const [docs, setDocs] = useState<RegulationDoc[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadSource, setUploadSource] = useState("");
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load default docs on mount
  useEffect(() => {
    api
      .listLegalDocs()
      .then(setDocs)
      .catch(() => {})
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
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-xl font-semibold text-white">Legal Document</h1>

      {/* ── Default / indexed docs ─────────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="text-xs font-medium text-[#5b616e] uppercase tracking-wide">
          Dokumen Regulasi Terindeks
        </h2>

        {docsLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-14 rounded-xl bg-[#16181c] animate-pulse border border-[#2a2d36]"
              />
            ))}
          </div>
        )}

        {!docsLoading && docs.length === 0 && (
          <div className="flex items-center gap-3 p-4 rounded-xl border border-[#2a2d36] bg-[#16181c] text-[#5b616e]">
            <Scale className="h-5 w-5 shrink-0" />
            <p className="text-sm">
              Belum ada dokumen terindeks. Unggah dokumen pertama di bawah.
            </p>
          </div>
        )}

        {!docsLoading && docs.length > 0 && (
          <div className="space-y-2">
            {docs.map((doc) => (
              <div
                key={doc.id}
                className="flex items-start gap-3 p-3.5 rounded-xl border border-[#2a2d36] bg-[#16181c]"
              >
                <FileText className="h-4 w-4 text-[#0052ff] shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium truncate">{doc.title}</p>
                  <div className="flex items-center gap-2 mt-0.5 text-[11px] text-[#5b616e]">
                    <span className="px-1.5 py-0.5 rounded bg-[#0a0b0d] border border-[#2a2d36] font-mono">
                      {doc.source}
                    </span>
                    {doc.version && <span>{doc.version}</span>}
                    <span>·</span>
                    <span>
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

      {/* ── Upload section ─────────────────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="text-xs font-medium text-[#5b616e] uppercase tracking-wide">
          Unggah Dokumen Mandiri
        </h2>

        <div className="rounded-xl border border-[#2a2d36] bg-[#16181c] p-5 space-y-4">
          {/* File picker */}
          <div>
            <label className="text-xs text-[#a8acb3] mb-1.5 block">File PDF</label>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border border-dashed border-[#2a2d36] rounded-xl p-6 flex flex-col items-center gap-2 cursor-pointer hover:border-[#0052ff] transition-colors"
            >
              <Upload className="h-6 w-6 text-[#5b616e]" />
              <p className="text-sm text-[#5b616e]">
                {uploadFile ? uploadFile.name : "Klik untuk pilih file PDF"}
              </p>
              {uploadFile && (
                <p className="text-[11px] text-[#3a3d46]">
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

          {/* Source + Title */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-[#a8acb3] mb-1.5 block">Sumber</label>
              <input
                value={uploadSource}
                onChange={(e) => setUploadSource(e.target.value)}
                placeholder="cth. OJK, UUPM, user"
                className="w-full bg-[#0a0b0d] border border-[#2a2d36] rounded-lg px-3 py-2 text-sm text-white placeholder:text-[#5b616e] focus:outline-none focus:border-[#0052ff] transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-[#a8acb3] mb-1.5 block">Judul</label>
              <input
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                placeholder="Judul dokumen"
                className="w-full bg-[#0a0b0d] border border-[#2a2d36] rounded-lg px-3 py-2 text-sm text-white placeholder:text-[#5b616e] focus:outline-none focus:border-[#0052ff] transition-colors"
              />
            </div>
          </div>

          {/* Feedback */}
          {uploadError && (
            <p className="text-xs text-[#cf202f] p-3 rounded-lg bg-[#cf202f08] border border-[#cf202f30]">
              {uploadError}
            </p>
          )}
          {uploadSuccess && (
            <p className="text-xs text-[#05b169] p-3 rounded-lg bg-[#05b16908] border border-[#05b16930]">
              Dokumen berhasil diunggah dan diindeks ke BM25.
            </p>
          )}

          {/* Submit */}
          <button
            onClick={handleUpload}
            disabled={!uploadFile || uploading}
            className="w-full py-2.5 rounded-lg bg-[#0052ff] text-white text-sm font-medium hover:bg-[#0047db] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? "Mengunggah…" : "Unggah & Indeks"}
          </button>
        </div>
      </section>
    </div>
  );
}
