import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://earthpulse-cat-model.vercel.app"),
  title: "RiskChain — Transparent catastrophe intelligence",
  description:
    "A map-first catastrophe-modelling workspace for source-backed live events and transparent, governed risk analysis.",
  openGraph: {
    title: "RiskChain — Transparent catastrophe intelligence",
    description: "Explore official events, run approved catastrophe models, and inspect every source, assumption and uncertainty.",
    type: "website",
    images: [{ url: "/og.png", width: 1731, height: 909, alt: "EarthPulse map intelligence interface for Bethlehem and the Lehigh Valley" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "RiskChain — Transparent catastrophe intelligence",
    description: "Map-first, source-visible catastrophe modelling without false precision.",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
