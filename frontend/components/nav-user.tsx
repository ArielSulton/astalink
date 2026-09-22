"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronsUpDownIcon,
  KeyRoundIcon,
  LogOutIcon,
  ScaleIcon,
  SettingsIcon,
} from "lucide-react";
import { toast } from "sonner";

import { createClient } from "@/lib/supabase/client";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";

export function NavUser({
  variant = "sidebar",
  isAdmin = false,
}: {
  variant?: "sidebar" | "header";
  isAdmin?: boolean;
}) {
  const router = useRouter();
  const { isMobile } = useSidebar();
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const sb = createClient();
    sb.auth.getUser().then(({ data: { user } }) => {
      setEmail(user?.email ?? null);
    });
  }, []);

  const name = email ? email.split("@")[0] : "Pengguna";
  const initial = (email?.[0] ?? "A").toUpperCase();

  async function handleLogout() {
    const sb = createClient();
    const { error } = await sb.auth.signOut();
    if (error) {
      toast.error(error.message);
      return;
    }
    router.push("/login");
    router.refresh();
  }

  const menu = (
          <DropdownMenuContent
            className="w-fit min-w-56"
            side={variant === "header" || isMobile ? "bottom" : "right"}
            align="end"
            sideOffset={4}
          >
            <DropdownMenuGroup>
              <DropdownMenuLabel className="p-0 font-normal">
                <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                  <Avatar>
                    <AvatarFallback className="bg-chart-2/15 text-chart-2 font-bold">
                      {initial}
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-medium">{name}</span>
                    <span className="truncate text-xs text-muted-foreground">
                      {email ?? "…"}
                    </span>
                  </div>
                </div>
              </DropdownMenuLabel>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem onClick={() => router.push("/settings")}>
                <SettingsIcon />
                Pengaturan
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push("/settings/pin")}>
                <KeyRoundIcon />
                PIN Persetujuan
              </DropdownMenuItem>
              {isAdmin && (
                <DropdownMenuItem onClick={() => router.push("/legal-docs")}>
                  <ScaleIcon />
                  Dokumen Regulasi
                </DropdownMenuItem>
              )}
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout}>
              <LogOutIcon />
              Keluar
            </DropdownMenuItem>
          </DropdownMenuContent>
  );

  // The header variant is the only account surface on mobile: the sidebar that
  // holds the sidebar variant has no trigger below the `lg` breakpoint.
  if (variant === "header") {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <button
              type="button"
              aria-label="Menu akun"
              className="inline-flex size-11 items-center justify-center rounded-full aria-expanded:bg-muted"
            />
          }
        >
          <Avatar className="size-8">
            <AvatarFallback className="bg-chart-2/15 text-chart-2 font-bold">
              {initial}
            </AvatarFallback>
          </Avatar>
        </DropdownMenuTrigger>
        {menu}
      </DropdownMenu>
    );
  }

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <SidebarMenuButton size="lg" className="aria-expanded:bg-muted" />
            }
          >
            <Avatar>
              <AvatarFallback className="bg-chart-2/15 text-chart-2 font-bold">
                {initial}
              </AvatarFallback>
            </Avatar>
            <div className="grid flex-1 text-left text-sm leading-tight">
              <span className="truncate font-medium">{name}</span>
              <span className="truncate text-xs text-muted-foreground">
                {email ?? "…"}
              </span>
            </div>
            <ChevronsUpDownIcon className="ml-auto size-4" />
          </DropdownMenuTrigger>
          {menu}
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
