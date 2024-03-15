export type Document = {
    desc: string,
    url: string
}

export type Term = {
    term: string,
    doc: Document,
    expert: string,
    date: string
}

export type TermsResponse = {
    terms: Term[]
}

export type Triple = {
    left: string,
    rel: string,
    right: string,
    doc: Document,
    expert: string,
    date: string
}

export type TripleResponse = {
    triples: Triple[]
}
