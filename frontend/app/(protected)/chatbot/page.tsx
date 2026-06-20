import { Bot } from "lucide-react";

export default function ChatbotPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center p-8">
      <div className="rounded-full bg-[#16181c] p-5 border border-[#2a2d36]">
        <Bot className="h-10 w-10 text-[#0052ff]" />
      </div>
      <h1 className="text-2xl font-semibold text-white">Chatbot AI</h1>
      <p className="text-[#a8acb3] max-w-sm text-sm">
        Tanyakan apa saja tentang portofolio, regulasi, atau kondisi pasar kepada asisten AI Astalink.
      </p>
      <span className="text-xs text-[#5b616e] border border-[#2a2d36] rounded-full px-3 py-1">
        Segera hadir
      </span>
    </div>
  );
}
