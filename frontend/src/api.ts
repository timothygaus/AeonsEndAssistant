const BASE_URL = 'http://localhost:8000'

export const getSets = () =>
    fetch(`${BASE_URL}/sets`).then(res => res.json())

export const getUserSets = () =>
    fetch(`${BASE_URL}/sets/saved`).then(res => res.json())

export const updateUserSets = (setIds: number[]) =>
    fetch(`${BASE_URL}/sets/saved`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(setIds)
    }).then(res => res.json())