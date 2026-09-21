export interface TransactionItem {
  id: string;
  audit_id?: string | null;
  workspace_id?: string | null;
  ticker: string;
  side: string;
  quantity: number;
  price?: number | null;
  realized_pnl?: number | null;
  status: string;
  broker_ref: string | null;
  executed_at?: string | null;
  created_at: string;
}
