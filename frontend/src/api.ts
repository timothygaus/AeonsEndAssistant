import type { CreateExpeditionRequest } from "./types"

const BASE_URL = 'http://localhost:8000'

export const getSets = () =>
    fetch(`${BASE_URL}/sets`).then(res => res.json())

export const getUserSets = () =>
    fetch(`${BASE_URL}/sets/saved`).then(res => res.json())

export const updateUserSets = (setIds: number[]) =>
    fetch(`${BASE_URL}/sets/saved`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(setIds)
    }).then(res => res.json())

export const getQuickplay = (numMages: number) =>
    fetch(`${BASE_URL}/quickplay?num_mages=${numMages}`).then(res => res.json())

export const getExpeditions = () =>
    fetch(`${BASE_URL}/expeditions`).then(res => res.json())

export const getExpeditionById = (id: number) =>
    fetch(`${BASE_URL}/expeditions/${id}`).then(res => res.json())
    
export const createExpedition = (data: CreateExpeditionRequest) =>
    fetch(`${BASE_URL}/expeditions`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    }).then(res => res.json())
