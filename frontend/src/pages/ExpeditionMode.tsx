import { useQuery } from "@tanstack/react-query"
import { getExpeditions } from "../api"
import { useNavigate } from "react-router-dom"
import Button from "../components/Button"

function ExpeditionMode() {
    const navigate = useNavigate()

    const {data: expeditions} = useQuery({
        queryKey: ['expeditions'],
        queryFn: getExpeditions
    })

    const activeExpeditions = expeditions?.filter((e: any) => e.status === 'active') ?? []

    return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
            <h1 className="text-3xl font-bold mb-8">Expedition Mode</h1>

            <div className="flex flex-col gap-4 max-w-sm">
                <Button onClick={() => navigate('/expedition/new')}>New Expedition</Button>
                <Button onClick={() => navigate('/expedition/resume')} disabled={activeExpeditions.length === 0}>Resume Expedition</Button>
            </div>

            {activeExpeditions.length > 0 && (
                <div className="mt-8">
                    <h2 className="text-x1 font-semibold mb-4">In Progress</h2>
                    {activeExpeditions.map((expedition: any) => (
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