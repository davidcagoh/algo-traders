import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "algo-traders — live paper-trading tape",
  description:
    "Live read-only view of a Freqtrade paper-trading bot running HmmSmaSlopeV2 on Hyperliquid. " +
    "Pre-registered 30-day dry-run. No real capital.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="grain min-h-screen">
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
