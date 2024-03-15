'use client'
import { Roboto } from 'next/font/google';
import { createTheme } from '@mui/material/styles';

const roboto = Roboto({
  weight: ['300', '400', '500', '700'],
  display: 'swap',
  subsets: [
    'cyrillic',
    'latin'
  ]
});

const theme = createTheme({
  palette: {
    mode: 'light',
  },
  typography: {
    fontFamily: roboto.style.fontFamily,
    h1: { fontSize: '2.5rem' },
    h2: { fontSize: '2.5rem' },
    h3: { fontSize: '2rem' },
    h4: { fontSize: '1.6rem' },
    h5: { fontSize: '1.4rem' },
    h6: { fontSize: '1.2rem' },
    
  },
});

export default theme;