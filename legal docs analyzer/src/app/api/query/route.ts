import { NextRequest, NextResponse } from "next/server";
import { ChatGroq } from "@langchain/groq";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { StateGraph, END } from "@langchain/langgraph";
import { EmbeddingsService } from "@/lib/embeddings";
import { db } from "@/db";
import { documents as documentsTable } from "@/db/schema/documents";
import { sql } from "drizzle-orm";
import fs from "fs";
import path from "path";

interface GraphState {
  query: string;
  context: string;
  routing_decision: string;
  answer: string;
}

export async function POST(req: NextRequest) {
  // Validate Environment Variables
  if (!process.env.DATABASE_URL || !process.env.GROQ_API_KEY) {
    console.error("Missing environment variables: DATABASE_URL or GROQ_API_KEY");
    return NextResponse.json({ 
      error: "Server configuration error: Missing API keys or Database URL. Please check your .env.local file." 
    }, { status: 500 });
  }

  try {
    const { query } = await req.json();

    const routerModel = new ChatGroq({ apiKey: process.env.GROQ_API_KEY, model: "llama-3.3-70b-versatile" });
    const simpleModel = new ChatGroq({ apiKey: process.env.GROQ_API_KEY, model: "llama-3.3-70b-versatile" });
    const complexModel = new ChatGroq({ apiKey: process.env.GROQ_API_KEY, model: "llama-3.3-70b-versatile" });

    // Load personalization profile
    const personalizationPath = path.join(process.cwd(), "src/lib/personalization.md");
    const personalizationProfile = fs.readFileSync(personalizationPath, "utf-8");

    // 1. Retrieve Node
    const retrieve = async (state: GraphState) => {
      const embedding = await EmbeddingsService.embedQuery(state.query);
      
      // Vector search using Drizzle and raw SQL (since pgvector isn't fully integrated in Drizzle helpers)
      const results = await db.execute(sql`
        SELECT content, 1 - (embedding <=> ${JSON.stringify(embedding)}::vector) as similarity
        FROM documents
        WHERE 1 - (embedding <=> ${JSON.stringify(embedding)}::vector) > 0.5
        ORDER BY similarity DESC
        LIMIT 5
      `);

      const context = results.map((r: any) => r.content).join("\n\n");
      return { context };
    };

    // 2. Route Node
    const route = async (state: GraphState) => {
      const prompt = ChatPromptTemplate.fromMessages([
        ["system", "You are a routing expert. Determine if the following legal query is 'simple' (basic fact extraction, definitions) or 'complex' (analysis, synthesis, legal reasoning). Output only 'simple' or 'complex'."],
        ["human", "{query}"],
      ]);
      const chain = prompt.pipe(routerModel).pipe(new StringOutputParser());
      const decision = (await chain.invoke({ query: state.query })).toLowerCase().trim();
      return { routing_decision: decision.includes("complex") ? "complex" : "simple" };
    };

    // 3. Generate Node
    const generate = async (state: GraphState) => {
      const model = state.routing_decision === "complex" ? complexModel : simpleModel;
      const prompt = ChatPromptTemplate.fromMessages([
        ["system", `You are a professional legal assistant. Follow this personalization profile strictly:\n\n${personalizationProfile}\n\nUse the following context to answer the user's query:\n\nContext:\n{context}`],
        ["human", "{query}"],
      ]);
      const chain = prompt.pipe(model).pipe(new StringOutputParser());
      const answer = await chain.invoke({ query: state.query, context: state.context });
      return { answer };
    };

    // Build Graph
    const workflow = new StateGraph<GraphState>({
        channels: {
            query: null,
            context: null,
            routing_decision: null,
            answer: null
        }
    })
      .addNode("retrieve", retrieve)
      .addNode("route", route)
      .addNode("generate", generate)
      .addEdge("__start__", "retrieve")
      .addEdge("retrieve", "route")
      .addEdge("route", "generate")
      .addEdge("generate", END);

    const app = workflow.compile();
    const result = await app.invoke({ query, context: "", routing_decision: "", answer: "" });

    return NextResponse.json({
      answer: result.answer,
      routing: result.routing_decision,
    });
  } catch (error: any) {
    console.error("Query error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
