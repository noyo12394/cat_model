import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { AppShell } from "@/components/shell/AppShell";

export const metadata: Metadata = {
  metadataBase: new URL("https://earthpulse-cat-model.vercel.app"),
  title: "EarthPulse — Global compound-hazard intelligence",
  description:
    "Global disaster awareness plus evidence-linked compound-hazard, infrastructure, route, and community consequence intelligence.",
  openGraph: {
    title: "EarthPulse — Global compound-hazard intelligence",
    description: "Live GDACS events meet evidence-linked consequence analysis, route exposure, possible futures, and uncertainty.",
    type: "website",
    images: [{ url: "/og.png", width: 1731, height: 909, alt: "EarthPulse map intelligence interface for Bethlehem and the Lehigh Valley" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "EarthPulse — Global compound-hazard intelligence",
    description: "From observed hazard to possible infrastructure and community consequences.",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
