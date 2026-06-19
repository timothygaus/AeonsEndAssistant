import { useQuery } from "@tanstack/react-query"
import { useParams } from "react-router-dom"
import { getExpeditionById } from "../api"
import type { BattleDetail, ExpeditionState } from "../types"
import BackButton from "../components/BackButton"
import { useEffect, useState } from "react"
import Button from "../components/Button"

function ExpeditionView() {
    const { id } = useParams()
    const [phase, setPhase] = useState<'selecting' | 'locked' | 'resolving-win' | 'resolving-loss' | 'complete'>('selecting')
    const [selectedIds, setSelectedIds] = useState<number[]>([])
    const [lossRandomizerType, setLossRandomizerType] = useState<string | null>(null)

    const { data } = useQuery<ExpeditionState>({
        queryKey: ['expedition-id', Number(id)],
        queryFn: () => getExpeditionById(Number(id))
    })

    const currentBattle = data?.battles?.find((b: BattleDetail) => b.result === null)
    const selectedPlayerCards = data?.barracks_cards.filter(card => selectedIds.includes(card.id)) ?? []
    const notSelectedPlayerCards = data?.barracks_cards.filter(card => !selectedIds.includes(card.id)) ?? []
    const currentNemesis = currentBattle?.nemesis

    useEffect(() => {
        if (!data) return
        setSelectedIds(data.barracks_cards.slice(0, 9).map(card => card.id))
        setPhase('selecting')
        setLossRandomizerType(null)
    }, [data])

    return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
            <BackButton />
            <h1 className="text-3xl font-bold mb-6">
                {data?.expedition?.name || `Expedition ${id}`}
            </h1>
            <h1 className="text-2xl font-bold mb-2">
                Supply
            </h1>
            <div className="flex flex-col gap-1 mb-6 max-w-md">
                {data?.barracks_cards.map(card => (
                    <label key={card.id} className="flex items-center gap-3 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={selectedIds.includes(card.id)}
                            onChange={() => {
                                setSelectedIds(prev => 
                                    prev.includes(card.id)
                                        ? prev.filter(id => id !== card.id)
                                        : [...prev, card.id]
                                )
                            }}
                            disabled={
                                (!selectedIds.includes(card.id) && selectedIds.length >= 9) ||
                                phase !== 'selecting'} 
                            />
                            {card.name} ({card.type})
                    </label>
                ))}
            </div>
            <div>
                <Button onClick={() => setPhase('locked')} disabled={phase !== 'selecting' || selectedIds.length !== 9}>Lock Supply</Button>
            </div>
            <h1 className="text-2xl font-bold mb-1 mt-4">
                Mages
            </h1>
            <div className="flex flex-col gap-4 max-w-md">
                {data?.mages.map(mage => (
                    <p key={mage.id}>{mage.name}</p>
                ))}
            </div>
            <h1 className="text-2xl font-bold mb-1 mt-4">
                Nemesis
            </h1>
            <div className="mb-6">
                {currentNemesis?.name}
            </div>
            <div className="flex-col gap-4 max-w-md">
                {phase === 'locked' && 
                    <div>
                        <Button onClick={() => setPhase('resolving-win')}>Win</Button>
                        <Button onClick={() => setPhase('resolving-loss')}>Loss</Button>
                    </div>
                }
                {phase === 'resolving-win' &&
                    <div>
                        <h1 className="text-2xl">New Supply Cards:</h1>
                        <Button onClick={() => setPhase('selecting')}>Continue</Button>
                    </div>
                }
                {phase === 'resolving-loss' &&
                    <div>
                        <h1 className="text-2xl">Add to barracks</h1>
                        {/* temp */}
                        <Button onClick={() => setPhase('selecting')}>Lock choice</Button>
                    </div>
                }
            </div>
        </div>
    )
}

export default ExpeditionView