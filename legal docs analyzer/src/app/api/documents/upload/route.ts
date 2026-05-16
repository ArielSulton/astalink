import { NextRequest, NextResponse } from "next/server";
import { db } from "@/db";
import { documents as documentsTable } from "@/db/schema/documents";
import { EmbeddingsService } from "@/lib/embeddings";
import pdf from "pdf-parse";
import { ChatGroq } from "@langchain/groq";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { RecursiveCharacterTextSplitter } from "@langchain/textsplitters";

export async function POST(req: NextRequest) {
  console.log("Starting document upload processing...");
  
  // Validate Environment Variables
  if (!process.env.DATABASE_URL || !process.env.GROQ_API_KEY) {
    console.error("Missing environment variables: DATABASE_URL or GROQ_API_KEY");
    return NextResponse.json({ 
      error: "Server configuration error: Missing API keys or Database URL. Please check your .env.local file." 
    }, { status: 500 });
  }

  try {
    const formData = await req.formData();
    const file = formData.get("file") as File;

    if (!file) {
      console.error("No file found in form data");
      return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
    }

    console.log(`Processing file: ${file.name}, size: ${file.size} bytes`);

    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    let text = "";

    try {
      if (file.name.endsWith(".pdf")) {
        console.log("Parsing PDF...");
        const data = await pdf(buffer);
        text = data.text;
        console.log(`PDF parsed successfully. Extracted ${text.length} characters.`);
      } else {
        text = buffer.toString("utf-8");
      }
    } catch (parseError: any) {
      console.error("Error parsing file:", parseError);
      return NextResponse.json({ error: `Failed to parse file: ${parseError.message}` }, { status: 500 });
    }

    if (!text || text.trim().length === 0) {
      return NextResponse.json({ error: "No text content extracted from file" }, { status: 400 });
    }

    // Split text into chunks using LangChain splitter
    const splitter = new RecursiveCharacterTextSplitter({
      chunkSize: 1000,
      chunkOverlap: 200,
    });
    
    console.log("Splitting text into chunks...");
    const chunks = await splitter.splitText(text);
    console.log(`Split into ${chunks.length} chunks.`);

    // Vectorize and store - Use a small batch size to avoid overloading or timeouts
    const batchSize = 5;
    for (let i = 0; i < chunks.length; i += batchSize) {
      const batch = chunks.slice(i, i + batchSize);
      console.log(`Processing batch ${Math.floor(i / batchSize) + 1} of ${Math.ceil(chunks.length / batchSize)}...`);
      
      const embeddingPromises = batch.map(chunk => EmbeddingsService.embedQuery(chunk));
      const embeddings = await Promise.all(embeddingPromises);

      const insertPromises = batch.map((chunk, index) => {
        return db.insert(documentsTable).values({
          content: chunk,
          metadata: {
            source: file.name,
            page: 0,
            chunk_index: i + index,
          },
          embedding: embeddings[index],
        });
      });

      await Promise.all(insertPromises);
    }

    console.log("All chunks stored. Generating summary...");

    // Generate Summary using Llama 3 70B
    const model = new ChatGroq({
      apiKey: process.env.GROQ_API_KEY,
      model: "llama-3.3-70b-versatile",
    });

    const prompt = ChatPromptTemplate.fromMessages([
      ["system", "You are a senior legal analyst. Provide a concise yet comprehensive summary of the following legal document. Use Markdown formatting with clear headings, bullet points, and highlight key obligations or risks."],
      ["human", "Document Text:\n{text}"],
    ]);

    const chain = prompt.pipe(model).pipe(new StringOutputParser());
    // Use more text for summary but still capped for performance
    const summary = await chain.invoke({ text: text.slice(0, 15000) });

    console.log("Summary generated. Processing complete.");

    return NextResponse.json({
      message: `Successfully processed ${file.name}`,
      summary: summary,
    });
  } catch (error: any) {
    console.error("Upload error details:", error);
    return NextResponse.json({ error: `Upload failed: ${error.message}` }, { status: 500 });
  }
}
