import { useMutation, useQuery } from "@tanstack/react-query"
import { createExpedition, getUserSets } from "../api"
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import Button from "../components/Button"
import type { CreateExpeditionRequest, Expedition, UserSet } from "../types"
import BackButton from "../components/BackButton"

function NewExpedition() {
    const navigate = useNavigate()
    const [expeditionName, setExpeditionName] = useState<string | undefined>()
    const [variant, setVariant] = useState<string>('standard')

    const {data: userSets} = useQuery<UserSet[]>({
        queryKey: ['userSets'],
        queryFn: getUserSets
    })

    const mutation = useMutation<Expedition, Error, CreateExpeditionRequest>({
        mutationFn: createExpedition,
        onSuccess: (data) => {
            navigate(`/expedition/${data.id}`)
        }
    })

    const handleCreateExpedition = () => {
        const setIds = userSets?.map((userSet: UserSet) => userSet.set_id) ?? []
        mutation.mutate({set_ids: setIds, variant, name: expeditionName || undefined})
    }

    return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
            <BackButton />
            <h1 className="text-3xl font-bold mb-8">New Expedition</h1>  

            <div className="flex flex-col gap-4 max-w-sm">
                <label className="flex flex-col gap-1">
                    Name
                    <input
                        type="text"
                        onChange={(e) => setExpeditionName(e.target.value)}
                        className="bg-gray-700 rounded px-3 py-2 text-white"
                    />
                </label>
                
                <select
                    title="variant-dropdown"
                    value={variant}
                    onChange={(e) => setVariant(e.target.value)}  
                    className="bg-gray-700 rounded px-3 py-2 text-white"
                >
                    <option value="standard">Standard</option>
                    <option value="short">Short</option>
                    <option value="extended">Extended</option>
                </select>

                <Button onClick={handleCreateExpedition}>Create</Button>
            </div>          
        </div>
    )
}

export default NewExpedition