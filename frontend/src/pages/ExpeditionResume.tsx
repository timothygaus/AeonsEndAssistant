import { useQuery } from "@tanstack/react-query";
import BackButton from "../components/BackButton";
import type { Expedition } from "../types";
import { getExpeditions } from "../api";
import Button from "../components/Button";
import { useNavigate } from "react-router-dom";

function ExpeditionResume() {
    const navigate = useNavigate()

    const {data: expeditions} = useQuery<Expedition[]>({
        queryKey: ['expeditions'],
        queryFn: getExpeditions
    })
    
    const activeExpeditions = expeditions?.filter((e: Expedition) => e.status === 'active') ?? []

    return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
            <BackButton />

            {activeExpeditions.length > 0 && (
                <div className="mt-8">
                    <h2 className="text-xl font-semibold mb-4">Active Expeditions</h2>
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

export default ExpeditionResume