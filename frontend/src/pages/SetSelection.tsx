import { useState, useEffect } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { getSets, getUserSets, updateUserSets } from "../api"
import Button from "../components/Button"
import type { SetBox, UserSet } from "../types"
import BackButton from "../components/BackButton"

function SetSelection() {
    const { data: allSets, isLoading: setsLoading } = useQuery<SetBox[]>({
        queryKey: ['sets'],
        queryFn: getSets
    })

    const { data: userSets, isLoading: userSetsLoading } = useQuery<UserSet[]>({
        queryKey: ['userSets'],
        queryFn: getUserSets
    })

    const [selectedIds, setSelectedIds] = useState<number[]>([])

    useEffect(() => {
        if (userSets) {
            setSelectedIds(userSets.map((us: UserSet) => us.set_id))
        }
    }, [userSets])

    const mutation = useMutation({
        mutationFn: updateUserSets
    })

    if (setsLoading || userSetsLoading) {
        return <div className="p-8 text-white">Loading...</div>
    }

    return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
            <BackButton />
            <h1 className='text-3xl font-bold mb-6'>Select your Sets</h1>

            <div className='space-y-2'>
                {allSets?.map((set: SetBox) => (
                    <label key={set.id} className="flex items-center gap-3 cursor-pointer">
                        <input
                            type='checkbox'
                            checked={selectedIds.includes(set.id)}
                            onChange={() => {
                                setSelectedIds(prev =>
                                    prev.includes(set.id)
                                        ? prev.filter(id => id !== set.id)
                                        : [...prev, set.id]
                                )
                            }}
                        />
                        {set.name}
                    </label>
                ))}
            </div> 

            <Button onClick={() => mutation.mutate(selectedIds)}>Save</Button>
            {mutation.isSuccess && <p className="text-green-400 mt-2">Sets saved!</p>}
        </div>
    )
}

export default SetSelection