export interface CreateExpeditionRequest {
    set_ids: number[]
    variant: string
    name?: string
}

export interface SetBox {
    id: number
    name: string
}

export interface UserSet {
    id: number
    set_id: number
}

export interface PlayerCard {
    id: number
    name: string
    type: string
    is_supply: boolean
    set_id: number
}

export interface BreachMage {
    id: number
    name: string
    set_id: number
    complexity: number | null
}

export interface Nemesis {
    id: number
    name: string
    set_id: number
    expedition_battle: number | null
    difficulty: number | null
}

export interface Expedition {
    id: number
    name: string | null
    status: string
    current_battle: number
    variant: string
    created_at: string
}

export interface ExpeditionState {
    expedition: Expedition
    barracks_cards: PlayerCard[]
    banished_cards: PlayerCard[]
    mages: BreachMage[]
    battles: BattleDetail[]
}

export interface BattleDetail {
    battle_number: number
    result: string | null
    nemesis: Nemesis
}

export interface QuickplayResponse {
    player_cards: PlayerCard[]
    mages: BreachMage[]
    nemesis: Nemesis
}