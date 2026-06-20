import Link from "next/link";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KeyRound } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="p-6 max-w-lg mx-auto space-y-4">
      <h1 className="text-2xl font-semibold">Pengaturan</h1>
      <Link href="/settings/pin">
        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <CardHeader className="flex flex-row items-center gap-3 space-y-0">
            <KeyRound className="h-5 w-5 text-muted-foreground" />
            <div>
              <CardTitle className="text-base">PIN Persetujuan</CardTitle>
              <CardDescription>Atur PIN untuk mengkonfirmasi transaksi</CardDescription>
            </div>
          </CardHeader>
        </Card>
      </Link>
    </div>
  );
}
