import { Tokens } from "@/authentication"
import { createContext } from "react"

type AuthContextType = {
    tokens: Tokens,
    username: string | undefined
}

export const AuthContext = createContext<AuthContextType>({
    tokens: {
        access: null,
        refresh: null
    },
    username: undefined
})
export function AuthProvider({tokens, children}: {tokens: Tokens, children: JSX.Element | JSX.Element[]}) {    
    return <AuthContext.Provider value={{
        tokens: tokens,
        username: undefined
    }}>
        {children}
    </AuthContext.Provider>
}

export default AuthProvider