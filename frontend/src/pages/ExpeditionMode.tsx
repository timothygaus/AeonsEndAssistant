import { useQuery } from "@tanstack/react-query"
import { getExpeditions, getUserSets } from "../api"
import { useNavigate } from "react-router-dom"
import Button from "../components/Button"
import type { UserSet, Expedition } from "../types"
import BackButton from "../components/BackButton"

function ExpeditionMode() {
    const navigate = useNavigate()

    const {data: expeditions} = useQuery<Expedition[]>({
        queryKey: ['expeditions'],
        queryFn: getExpeditions
    })

    const {data: userSets} = useQuery<UserSet[]>({
        queryKey: ['userSets'],
        queryFn: getUserSets
    })

    const activeExpeditions = expeditions?.filter((e: Expedition) => e.status === 'active') ?? []

    if (userSets?.length === 0) {
        return (
            <div className="min-h-screen bg-gray-900 text-white p-8">
                <BackButton />
                <h1 className="text-3xl font-bold mb-8">Expedition Mode</h1>
                <p className="mb-4">No sets saved. Please select your sets before playing.</p>
                <Button onClick={() => navigate('/sets')}>Manage Sets</Button>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
            <BackButton />
            <h1 className="text-3xl font-bold mb-8">Expedition Mode</h1>

            <div className="flex flex-col gap-4 max-w-sm">
                <Button onClick={() => navigate('/expedition/new')}>New Expedition</Button>
                <Button onClick={() => navigate('/expedition/resume')} disabled={activeExpeditions.length === 0}>Resume Expedition</Button>
            </div>

            {activeExpeditions.length > 0 && (
                <div className="mt-8">
                    <h2 className="text-xl font-semibold mb-4">In Progress</h2>
                    {activeExpeditions.map((expedition: Expedition) => (
                        <div key={expedition.id} className="flex items-center justify-between mb-2">
                            <span>{expedition.name || `Expedition ${expedition.id}`}</span>
                            <Button onClick={() => navigate(`/expedition/${expedition.id}`)}>Resume</Button>
                        </div>
                    ))}
                </div>
            )}
        </div>

    )
}

export default ExpeditionMode