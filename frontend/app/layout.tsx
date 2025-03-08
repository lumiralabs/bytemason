import type { Metadata } from "next";
import "./globals.css";
import { pixelifySans } from "./fonts";

export const metadata: Metadata = {
  title: "ByteMason",
  description: "Prompt to code in CLI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={pixelifySans.className}>
        {children}
      </body>
    </html>
  );
}
