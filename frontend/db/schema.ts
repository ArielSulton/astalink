import { pgTable, text, uuid, jsonb, timestamp } from "drizzle-orm/pg-core";

export const regulationDocuments = pgTable("regulation_documents", {
  id: uuid("id").primaryKey().defaultRandom(),
  source: text("source").notNull(),
  title: text("title").notNull(),
  version: text("version"),
  docHash: text("doc_hash").notNull().unique(),
  indexedAt: timestamp("indexed_at", { withTimezone: true }).notNull().defaultNow(),
  metadata: jsonb("metadata").notNull().default({}),
});
