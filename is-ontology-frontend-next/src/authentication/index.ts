'use client'

export type Tokens = {
    access: string | null
    refresh: string | null
}

export default class Authentication {
    static authenticated = false
    static setToken(tokens: Tokens) {
        localStorage.setItem("access", tokens.access!)
        localStorage.setItem("refresh", tokens.refresh!)
    }

    static getToken() : Tokens {
        return {
            access: localStorage.getItem("access"),
            refresh: localStorage.getItem("refresh")
        }
    }

    static removeToken(){
        localStorage.removeItem("access")
        localStorage.removeItem("refresh")
    }
}