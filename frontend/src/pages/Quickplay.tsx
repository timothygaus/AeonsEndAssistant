import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { getQuickplay } from "../api"

function Quickplay() {
    const [numMages, setNumMages] = useState(2)

    const { data, isLoading, refetch } = useQuery<any>({
        queryKey: ['quickplay', numMages],
        queryFn: () => getQuickplay(numMages),
        enabled: false
    })

    const handleRandomize = () => {
        refetch()
    }
    console.log('data:', data)
    return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
            <h1 className="text-3xl font-bold mb-8">Quickplay</h1>

            <div className="flex flex-col gap-4 max-w-sm">
                <label className="flex flex-col gap-1">
                    Number of Mages
                    <input
                        type="text"
                        min={1}
                        max={4}
                        value={numMages}
                        onChange={(e) => setNumMages(Number(e.target.value))}
                        className="bg-gray-700 rounded px-3 py-2 text-white"
                    />
                </label>

                <button
                    onClick={handleRandomize}
                    className="px-6 py-3 bg-blue-300 rounded font-semibold hover:bg-blue-700"
                >
                    Create Game
                </button>
            </div>

            {isLoading && <p className="mt-8">Loading...</p>}

            {data?.nemesis && (
                <div className="mt-8">
                    <h2 className="text-2xl font-bold mb-4">Results</h2>
                    <h3 className="mt-3">
                        Mages: {data.mages.map((mage: any) => (
                            <p key={mage.id}>{mage.name}</p>
                    ))}</h3>
                    <h3 className="mt-3">
                        Gems: {data.player_cards.filter((card: any) => card.type === 'gem').map((card: any) => (
                            <p key={card.id}>{card.name}</p>
                    ))}</h3>
                    <h3 className="mt-3">
                        Relics: {data.player_cards.filter((card: any) => card.type === 'relic').map((card: any) => (
                            <p key={card.id}>{card.name}</p>
                    ))}</h3>
                    <h3 className="mt-3">
                        Spells: {data.player_cards.filter((card: any) => card.type === 'spell').map((card: any) => (
                            <p key={card.id}>{card.name}</p>
                    ))}</h3>
                    <h3 className="mt-3">
                        Nemesis: {data.nemesis.name}
                    </h3>
                </div>
            )}
        </div>
    )
}

export default Quickplay