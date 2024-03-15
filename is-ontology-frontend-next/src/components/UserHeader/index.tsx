import { getUserInfo } from '@/api'
import Authentication from '@/authentication'
import { AuthContext } from '@/contexts/AuthContext'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import { useRouter } from 'next/navigation'
import React, { useContext, useEffect, useState } from 'react'

export default function UserHeader() {
    const user = useContext(AuthContext)
    const [username, setUsername] = useState('')
    const router = useRouter()

    useEffect(() => {
        getUserInfo().then(r => {
            user.username = r.data.username
            // console.log(r)
            setUsername(r.data.username)
            Authentication.authenticated = true
        })
    }, [user])
    return (
        <>
            <Typography sx={{ flexGrow: 1 }}>
                Приветствуем, {username}!
            </Typography>
            <Button color="inherit" onClick={()=>{
                Authentication.removeToken()
                router.replace('/')
                location.reload()
            }}>Выход</Button>
        </>
    )
}
