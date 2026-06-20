import { Newspaper } from "lucide-react";

export default function NewsPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center p-8">
      <div className="rounded-full bg-[#16181c] p-5 border border-[#2a2d36]">
        <Newspaper className="h-10 w-10 text-[#0052ff]" />
      </div>
      <h1 className="text-2xl font-semibold text-white">External News</h1>
      <p className="text-[#a8acb3] max-w-sm text-sm">
        Berita pasar terkini dari berbagai sumber — pertimbangkan sentimen dan peristiwa makro sebelum mengambil keputusan investasi.
      </p>
      <span className="text-xs text-[#5b616e] border border-[#2a2d36] rounded-full px-3 py-1">
        Segera hadir
      </span>
    </div>
  );
}
