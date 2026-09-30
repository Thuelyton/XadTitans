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
    "menu.subtitle": "Xadrez com Inteligência Artificial e Estilo Titan",
    "menu.new_game": "Novo Jogo",
    "menu.continue": "Continuar",
    "menu.load": "Carregar Partida",
    "menu.settings": "Configurações",
    "menu.stats": "Estatísticas",
    "menu.quit": "Sair",
    # Genéricos e Ações
    "common.back": "Voltar",
    "common.save": "Salvar",
    "common.reset": "Restaurar Padrões",
    "common.ok": "OK",
    # Tela de Nova Partida
    "new_game.title": "Nova Partida",
    "new_game.mode": "Modo de Jogo",
    "new_game.side": "Sua Cor",
    "new_game.level": "Dificuldade da IA",
    "new_game.clock": "Relógio",
    "new_game.clock_none": "Sem relógio",
    "new_game.start": "Iniciar Partida",
    # Tela de Configurações
    "settings.title": "Configurações",
    "settings.volume": "Volume do Som",
    "settings.anim_speed": "Velocidade das Animações",
    "settings.fps": "Taxa de Quadros (FPS)",
    "settings.resolution": "Resolução",
    "settings.visual_hints": "Ajudas Visuais",
    "settings.enabled": "Ativado",
    "settings.disabled": "Desativado",
    # Tela de Estatísticas
    "stats.title": "Estatísticas",
    "stats.total": "Total de Partidas",
    "stats.by_mode": "Por Modo de Jogo",
    "stats.by_level": "Por Nível de IA",
    "stats.wins": "Vitórias",
    "stats.losses": "Derrotas",
    "stats.draws": "Empates",
    # Tela / Mensagem de Carregar e Continuar
    "load.title": "Carregar Partida",
    "load.no_autosave": "Nenhuma partida salva para continuar.",
    "load.no_pgns": "Nenhum arquivo PGN encontrado.",
    "load.select_pgn": "Selecione um arquivo PGN:",
    # Dicas e atalhos da partida
    "game.thinking": "Pensando...",
    "game.game_over": "Fim de partida",
    "game.wins": "vencem",
    "game.resigned_wins": "vencem por desistência",
    "game.draw": "Empate",
    "hint.endgame": "Enter: nova partida    Esc: voltar ao menu",
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
