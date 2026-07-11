import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/login", "/signup", "/forgot-password"],
      disallow: [
        "/dashboard",
        "/assets",
        "/transactions",
        "/legal-docs",
        "/approvals",
        "/audit",
        "/news",
        "/business",
        "/chatbot",
        "/settings",
        "/reset-password",
        "/auth/callback",
      ],
    },
    sitemap: "https://astalink.my.id/sitemap.xml",
  };
}
