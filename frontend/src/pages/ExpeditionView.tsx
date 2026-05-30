import { useQuery } from "@tanstack/react-query"
import { useParams } from "react-router-dom"
import { getExpeditionById } from "../api"
import type { BattleDetail, ExpeditionState } from "../types"

function ExpeditionView() {
    const { id } = useParams()

    const { data } = useQuery<ExpeditionState>({
        queryKey: ['expedition-id', Number(id)],
        queryFn: () => getExpeditionById(Number(id))
    })

    const currentBattle = data?.battles?.find((b: BattleDetail) => b.result === null)
    const currentNemesis = currentBattle?.nemesis

    return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
            <h1 className="text-3xl font-bold mb-8">
                {data?.expedition?.name || `Expedition ${id}`}
            </h1>
        </div>
    )
}

export default ExpeditionView