import { useQuery } from "@tanstack/react-query"
import { useParams } from "react-router-dom"
import { getExpeditionById } from "../api"

function ExpeditionView() {
    const { id } = useParams()

    const { data } = useQuery({
        queryKey: ['expedition-id', Number(id)],
        queryFn: () => getExpeditionById(Number(id))
    })

    return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
            <h1 className="text-3xl font-bold mb-8">
                {data?.expedition?.name || `Expedition ${id}`}
            </h1>
        </div>
    )
}

export default ExpeditionView