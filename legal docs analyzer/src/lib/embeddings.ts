import { pipeline, env } from "@xenova/transformers";

// Disable local models during development to avoid path issues in Next.js
(env as any).allowLocalModels = false;
(env as any).useBrowserCache = false;

export class EmbeddingsService {
  private static extractor: any = null;

  static async getInstance() {
    if (!this.extractor) {
      console.log("Loading Transformers.js model: Xenova/all-MiniLM-L6-v2...");
      try {
        this.extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
        console.log("Model loaded successfully.");
      } catch (error) {
        console.error("Failed to load model:", error);
        throw error;
      }
    }
    return this.extractor;
  }

  static async embedQuery(text: string): Promise<number[]> {
    try {
      const extractor = await this.getInstance();
      const output = await extractor(text, { pooling: 'mean', normalize: true });
      return Array.from(output.data);
    } catch (error) {
      console.error("Embedding generation failed:", error);
      throw error;
    }
  }
}
