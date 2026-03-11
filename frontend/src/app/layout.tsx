import type { Metadata } from "next";
import { Space_Grotesk, Inter, JetBrains_Mono } from "next/font/google";
import { QueryProvider } from "@/lib/query-client";
import { Sidebar } from "@/components/layout/sidebar";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-heading",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const inter = Inter({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Rede de Conselheiros CVM",
  description:
    "Analise de redes sociais dos conselheiros de empresas abertas brasileiras",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className={`${spaceGrotesk.variable} ${inter.variable} ${jetbrainsMono.variable}`}>
      <body>
        <QueryProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <div className="flex-1 ml-56">{children}</div>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
