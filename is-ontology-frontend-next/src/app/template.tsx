'use client'

import { axios_instance } from '@/api'
import Authentication, { Tokens } from '@/authentication'
import Menu from '@/components/Menu'
import UserHeader from '@/components/UserHeader'
import AuthProvider from '@/contexts/AuthContext'
import { AppBar, Toolbar, Typography } from '@mui/material'
import Box from '@mui/material/Box'
import { useEffect, useState } from 'react'

export default function Template({ children }: { children: React.ReactElement }) {
    const [token, setToken] = useState<Tokens>({ access: null, refresh: null })
    useEffect(() => {
        const token = Authentication.getToken()
        axios_instance.defaults.headers.common['Authorization'] = `Bearer ${token.access}`
        setToken(token)
    }, [])


    return <AuthProvider tokens={token}>
        <AppBar position='relative'>
            <Toolbar>
                {/* {token.access &&*/} <UserHeader />{/*} */}

                {/* {!token.access && <><Box sx={{ flexGrow: 1 }} /><Link href="/auth/login"><Button color='inherit'>Вход</Button></Link><Button color='inherit'>Регистрация</Button></>} */}
            </Toolbar>
        </AppBar>

        <Box display='grid' gridTemplateColumns='repeat(12, 1fr)'>
            <Box gridColumn='span 2'>
                <Menu />
            </Box>
            <Box gridColumn='span 10'>

                {children}
            </Box>
        </Box>
        <footer><Typography><i>&copy; ЦК КБ &ldquo;Энерджинет&rdquo;, 2021 г.</i></Typography></footer>
    </AuthProvider>
}