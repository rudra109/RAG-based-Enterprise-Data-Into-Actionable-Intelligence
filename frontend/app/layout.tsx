import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { Toaster } from "@/components/ui/sonner";

export const metadata: Metadata = {
  title: "EnterpriseIQ | AI-Driven Analytics",
  description: "Enterprise Intelligence Platform for RAG, Pipelines, and Predictive Analytics.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-200 antialiased">
        <div className="flex h-screen overflow-hidden">
          <div className="hidden lg:flex h-full">
            <Sidebar />
          </div>
          <div className="flex flex-1 flex-col overflow-hidden">
            <Header />
            <main className="flex-1 overflow-y-auto bg-slate-900/50 p-8">
              {children}
            </main>
          </div>
        </div>
        <Toaster position="top-right" />
      </body>
    </html>
  );
}
