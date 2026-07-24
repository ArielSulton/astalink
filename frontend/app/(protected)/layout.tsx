import { AppSidebar } from "@/components/app-sidebar";
import { Separator } from "@/components/ui/separator";
import { WorkspaceProvider } from "@/components/workspace-context";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return (
    <TooltipProvider>
      <WorkspaceProvider>
        <SidebarProvider className="h-svh">
          <AppSidebar />
          <SidebarInset className="min-h-0">
            <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-4">
              <SidebarTrigger className="-ml-1" />
              <Separator orientation="vertical" className="mr-1 data-[orientation=vertical]:h-4" />
              <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
                Astalink Console
              </span>
            </header>
            <div className="flex-1 overflow-auto min-h-0">{children}</div>
          </SidebarInset>
        </SidebarProvider>
      </WorkspaceProvider>
    </TooltipProvider>
  );
}
