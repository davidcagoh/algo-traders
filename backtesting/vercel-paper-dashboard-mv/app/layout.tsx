import "./globals.css";

export const metadata = {
  title: "Signed MV Paper Dashboard",
  description: "Paper-trading monitor for the signed mean-variance portfolio"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
