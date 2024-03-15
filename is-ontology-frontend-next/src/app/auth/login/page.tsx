"use client"
import { getToken } from "@/api"
import Authentication from "@/authentication"
import Button from "@mui/material/Button"
import Input from "@mui/material/Input"
import Typography from "@mui/material/Typography"
import Paper from "@mui/material/Paper"
import { useRouter } from "next/navigation"
import { useRef, useState } from "react"

export default function Page() {
    const username = useRef<HTMLInputElement>(null)
    const password = useRef<HTMLInputElement>(null)
    const router = useRouter()
    const [wrong, setWrong] = useState(false)

    async function login() {
        try {
            const r = await getToken((username.current!.children[0] as any).value, (password.current!.children[0] as any).value)

            Authentication.setToken({
                access: r.data.access,
                refresh: r.data.refresh
            })
            router.replace("/")
        } catch (_) {
            setWrong(true)
        }

    }
    return <Paper elevation={1} sx={{
        width: 'fit-content'
    }}>
        <Typography variant="h1">Вход в систему</Typography>
        <label htmlFor="username"><Typography>Имя пользователя</Typography></label>
        <Input name='username' id='username' ref={username} />
        <label htmlFor="password"><Typography>Пароль</Typography></label>
        <Input name="password" type="password" id='password' ref={password} />
        {wrong && <Typography color="error">Неверное имя пользователя или пароль</Typography>}
        <Button onClick={login}>Войти</Button>
    </Paper>
}