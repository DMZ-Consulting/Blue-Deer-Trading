import type { Metadata } from "next";
import { ThemeProvider } from "../components/theme-provider";
import { Header } from "../components/Header"
import localFont from "next/font/local";
import "./globals.css";
import { PasswordProtected } from "../components/PasswordProtected";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});

/*const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});*/

export const metadata: Metadata = {
  title: "Blue Deer Trading",
  description: "Trading Journal Application",
};

interface RootLayoutProps {
  children: React.ReactNode
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" suppressHydrationWarning className={geistSans.variable}>
      <head />
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <PasswordProtected>
            <Header />
            <main>{children}</main>
          </PasswordProtected>
        </ThemeProvider>
      </body>
    </html>
  )
}
