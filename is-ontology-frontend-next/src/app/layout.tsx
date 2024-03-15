import './globals.css'
import type { Metadata } from 'next'
import { ThemeProvider } from '@mui/material/styles'
import theme from '@/components/ThemeRegistry/theme'


export const metadata: Metadata = {
  title: 'Центр Компетенций «Кибербезопасность» НТИ Энерджинет',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {


  return (
    <html lang="ru">
      <body>
        <ThemeProvider theme={theme}>
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
