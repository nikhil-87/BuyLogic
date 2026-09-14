import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "BuyLogic | AI Purchasing Agent",
  description: "BuyLogic — Full-stack purchasing assistant evaluating inventory, demand anomalies, supplier constraints, and budgets.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className="bg-[#09090b] text-slate-100 antialiased selection:bg-indigo-500/30 selection:text-indigo-200"
        suppressHydrationWarning
      >
        <Navbar />
        <main className="min-h-[calc(100vh-3.5rem)]">{children}</main>
      </body>
    </html>
  );
}
