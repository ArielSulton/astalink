import { pgTable, serial, text, jsonb, customType } from "drizzle-orm/pg-core";

// Define a custom vector type for Drizzle (since it's not natively supported in all dialects)
const vector = customType<{ data: number[]; driverData: string }>({
  dataType() {
    return "vector(384)";
  },
  toDriver(value) {
    return JSON.stringify(value);
  },
});

export const documents = pgTable("documents", {
  id: serial("id").primaryKey(),
  content: text("content").notNull(),
  metadata: jsonb("metadata").$type<{
    source: string;
    page: number;
    chunk_index: number;
  }>(),
  embedding: vector("embedding"),
});
