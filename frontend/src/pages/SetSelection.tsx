import { useState, useEffect } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { getSets, getUserSets, updateUserSets } from "../api"

function SetSelection() {
    const { data: allSets, isLoading: setsLoading } = useQuery({
        queryKey: ['sets'],
        queryFn: getSets
    })

    const { data: userSets, isLoading: userSetsLoading } = useQuery({
        queryKey: ['userSets'],
        queryFn: getUserSets
    })

    const [selectedIds, setSelectedIds] = useState<number[]>([])

    useEffect(() => {
        if (userSets) {
            setSelectedIds(userSets.map((us: any) => us.set_id))
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
            <h1 className='text-3xl font-bold mb-6'>Select your Sets</h1>

            <div className='space-y-2'>
                {allSets?.map((set:any) => (
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

            <button
                onClick={() => mutation.mutate(selectedIds)}
                className="mt-6 px-4 bg-blue-600 rounded hover:bg-blue-700"
            >
                Save
            </button>
        </div>
    )
}

export default SetSelection