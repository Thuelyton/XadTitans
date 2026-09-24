"""Internacionalização e mensagens em português (pt-BR) do XadTitans.

Centraliza todas as cadeias de texto da interface, menus e estatísticas,
garantindo fácil manutenção e extensibilidade futura.
"""

from __future__ import annotations

TEXTS: dict[str, str] = {
    # Modos de jogo
    "mode.human_vs_human": "2 Jogadores (Local)",
    "mode.human_vs_ai": "Jogador vs IA",
    "mode.ai_vs_ai": "IA vs IA",
    # Níveis de dificuldade da IA
    "level.iniciante": "Iniciante",
    "level.facil": "Fácil",
    "level.medio": "Médio",
    "level.dificil": "Difícil",
    # Cores / Lados
    "color.white": "Brancas",
    "color.black": "Pretas",
    "color.random": "Aleatório",
    # Status de jogo e resultados
    "status.in_progress": "Em andamento",
    "status.checkmate": "Xeque-mate",
    "status.stalemate": "Afogamento",
    "status.insufficient_material": "Material insuficiente",
    "status.fifty_moves": "Regra dos 50 lances",
    "status.threefold_repetition": "Tripla repetição",
    "status.draw_agreement": "Empate por acordo",
    "status.resignation": "Desistência",
    "status.time_out": "Tempo esgotado",
    # Textos principais de menus e navegação
    "menu.title": "XadTitans",
    "menu.new_game": "Novo Jogo",
    "menu.continue": "Continuar",
    "menu.load": "Carregar Partida",
    "menu.settings": "Configurações",
    "menu.stats": "Estatísticas",
    "menu.quit": "Sair",
    # Dicas e atalhos da partida
    "game.thinking": "Pensando...",
    "game.game_over": "Fim de partida",
    "game.wins": "vencem",
    "game.resigned_wins": "vencem por desistência",
    "game.draw": "Empate",
    "hint.endgame": "Enter: nova partida    Esc: sair",
}


def t(key: str, default: str | None = None, **kwargs: object) -> str:
    """Retorna o texto traduzido correspondente à chave informada em pt-BR.

    Se a chave não existir, retorna ``default`` (ou a própria chave se ``default`` for None).
    Se ``kwargs`` forem fornecidos, formata a string usando ``.format(**kwargs)``.
    """
    text = TEXTS.get(key, default if default is not None else key)
    if kwargs:
        return text.format(**kwargs)
    return text
