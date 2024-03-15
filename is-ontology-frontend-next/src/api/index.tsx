"use client"

import axios from "axios"
import { TermsResponse, TripleResponse } from "./types"

let baseURL = ""

export const axios_instance = axios.create({
    baseURL: baseURL,
    headers: {
        'X-CSRFToken': getCookie('csrftoken')
    }
})

export async function getUserInfo() {
    return await axios_instance.get<{ username: string }>('/api/user')
}

function getCookie(name: string) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()!.split(';').shift();
  }

  export async function getTerms() {
    return await axios_instance.post<TermsResponse>('/api/terms/')
}

export async function getTriples() {
    return await axios_instance.post<TripleResponse>('/api/triples/')
}
