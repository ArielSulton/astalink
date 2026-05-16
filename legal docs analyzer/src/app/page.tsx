"use client";

import { useState } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import { Upload, Send, FileText, Loader2, Sparkles, Brain } from "lucide-react";

const API_BASE_URL = "/api";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [summary, setSummary] = useState<string>("");
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<{ role: string; content: string; routing?: string }[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setSummary(""); // Reset summary
      
      const formData = new FormData();
      formData.append("file", selectedFile);
      
      setIsUploading(true);
      try {
        const response = await axios.post(`${API_BASE_URL}/documents/upload`, formData);
        alert("File uploaded and processed successfully!");
        if (response.data.summary) {
          setSummary(response.data.summary);
        }
      } catch (error) {
        console.error("Upload error:", error);
        alert("Failed to upload file.");
      } finally {
        setIsUploading(false);
      }
    }
  };

  const handleQuery = async () => {
    if (!query.trim()) return;
    
    const userMessage = { role: "user", content: query };
    setMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setIsQuerying(true);
    
    try {
      const response = await axios.post(`${API_BASE_URL}/query`, { query });
      const assistantMessage = { 
        role: "assistant", 
        content: response.data.answer,
        routing: response.data.routing
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Query error:", error);
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I encountered an error while processing your request." }]);
    } finally {
      setIsQuerying(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 font-sans">
      {/* Sidebar */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-8">
          <div className="bg-indigo-600 p-2 rounded-lg">
            <FileText className="text-white w-6 h-6" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-gray-800">LegalDocs <span className="text-indigo-600">AI</span></h1>
        </div>
        
        <div className="flex-1">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Document Management</h2>
          <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:bg-gray-50 hover:border-indigo-400 transition-all duration-200">
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              {isUploading ? (
                <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
              ) : (
                <>
                  <Upload className="w-8 h-8 text-gray-400 mb-2" />
                  <p className="text-sm text-gray-600 font-medium">Click to upload PDF</p>
                </>
              )}
            </div>
            <input type="file" className="hidden" onChange={handleFileUpload} accept=".pdf,.txt,.md" />
          </label>
          
          {file && (
            <div className="mt-4 p-3 bg-indigo-50 rounded-lg flex items-center gap-3">
              <FileText className="text-indigo-600 w-5 h-5" />
              <span className="text-sm font-medium text-indigo-900 truncate">{file.name}</span>
            </div>
          )}
        </div>
        
        <div className="mt-auto pt-6 border-t border-gray-100">
          <div className="bg-gradient-to-br from-indigo-50 to-white p-4 rounded-xl border border-indigo-100">
            <p className="text-xs text-indigo-700 font-medium leading-relaxed">
              Powered by Groq & Supabase. <br/> 
              Intelligent routing enabled.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <div className="flex-1 flex overflow-hidden">
          {/* Chat Panel */}
          <div className="flex-1 flex flex-col max-w-4xl mx-auto px-4 md:px-8 overflow-hidden">
            {/* Header */}
            <header className="py-6 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-800">Legal Analysis Workspace</h2>
                <p className="text-sm text-gray-500">Ask anything about your uploaded documents</p>
              </div>
            </header>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto py-8 space-y-6 scrollbar-hide">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full opacity-40 grayscale">
                  <Sparkles className="w-16 h-16 mb-4 text-indigo-200" />
                  <p className="text-lg text-center">No analysis yet.<br/>Upload a document to start.</p>
                </div>
              ) : (
                messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[85%] p-5 rounded-2xl shadow-sm border ${
                      msg.role === "user" 
                        ? "bg-indigo-600 text-white border-indigo-500" 
                        : "bg-white text-gray-800 border-gray-100"
                    }`}>
                      {msg.role === "assistant" && msg.routing && (
                        <div className="flex items-center gap-1.5 mb-3 text-[10px] font-bold uppercase tracking-widest text-indigo-500 bg-indigo-50 px-2 py-0.5 rounded-full w-fit">
                          {msg.routing === "complex" ? <Brain className="w-3 h-3" /> : <Sparkles className="w-3 h-3" />}
                          {msg.routing} Analysis Path
                        </div>
                      )}
                      <div className="prose prose-sm max-w-none prose-p:leading-relaxed prose-headings:font-bold prose-indigo">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                ))
              )}
              {isQuerying && (
                <div className="flex justify-start">
                  <div className="bg-white p-5 rounded-2xl border border-gray-100 flex items-center gap-3">
                    <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
                    <span className="text-sm font-medium text-gray-500 italic">Analyzing documents...</span>
                  </div>
                </div>
              )}
            </div>

            {/* Input Area */}
            <div className="py-8">
              <div className="relative group">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleQuery()}
                  placeholder="Query your legal documents..."
                  className="w-full p-4 pr-16 bg-white border border-gray-200 rounded-2xl shadow-md focus:ring-4 focus:ring-indigo-50 focus:border-indigo-500 outline-none transition-all duration-300 placeholder:text-gray-400 text-gray-800 font-medium"
                />
                <button
                  onClick={handleQuery}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 hover:scale-105 active:scale-95 transition-all duration-200 shadow-lg shadow-indigo-100 disabled:opacity-50"
                  disabled={isQuerying}
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>

          {/* Summary Panel (Right side) */}
          <div className="w-96 bg-white border-l border-gray-200 flex flex-col overflow-hidden">
            <header className="p-6 border-b border-gray-100 flex items-center gap-2">
              <Brain className="w-5 h-5 text-indigo-600" />
              <h2 className="font-bold text-gray-800">Document Summary</h2>
            </header>
            <div className="flex-1 overflow-y-auto p-6 scrollbar-hide">
              {!summary && !isUploading ? (
                <div className="h-full flex flex-col items-center justify-center text-center opacity-30">
                  <FileText className="w-12 h-12 mb-3" />
                  <p className="text-sm">Summary will appear here after upload</p>
                </div>
              ) : isUploading ? (
                <div className="h-full flex flex-col items-center justify-center text-center gap-4">
                  <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
                  <p className="text-sm font-medium text-gray-500">Generating summary...</p>
                </div>
              ) : (
                <div className="prose prose-sm max-w-none prose-p:leading-relaxed prose-headings:font-bold prose-indigo">
                  <ReactMarkdown>{summary}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Footer */}
        <footer className="px-8 py-3 border-t border-gray-50 bg-white">
          <p className="text-center text-[10px] text-gray-400 font-medium uppercase tracking-widest">
            AI-generated responses should be reviewed by legal professionals.
          </p>
        </footer>
      </div>
    </div>
  );
}
