from library.base.BaseModel import BaseModel


class ClaudeTraderModel(BaseModel):
    """Guia da estratégia Claude Trader (claude_trader_operacao) — gerada e mantida
    pelo cérebro no iavest-backend (rule/ClaudeTrader.py). Aqui é SÓ LEITURA: este
    app só consome a guia pra repassar a instrução pro MT5 de cada conta."""

    def table(self):
        return 'claude_trader_operacao'

    def pk(self):
        return 'id_operacao'

    def fields(self):
        return {
            "id_operacao":        "id_operacao",
            "id_ativos_base":     "id_ativos_base",
            "id_market_analysis": "id_market_analysis",
            "id_intraday_origem": "id_intraday_origem",
            "id_estrategia":      "id_estrategia",
            "origem":             "origem",
            "tipo_posicao":       "tipo_posicao",
            "contratos":          "contratos",
            "preco_entrada":      "preco_entrada",
            "stop_inicial":       "stop_inicial",
            "stop_loss":          "stop_loss",
            "stop_gain":          "stop_gain",
            "alvo_1":             "alvo_1",
            "alvo_2":             "alvo_2",
            "protegido_nivel":    "protegido_nivel",
            "status":             "status",
            "acao_mt5":           "acao_mt5",
            "modo":               "modo",
            "abertura_em":        "abertura_em",
            "encerramento_em":    "encerramento_em",
            "preco_saida":        "preco_saida",
            "resultado":          "resultado",
            "resultado_pontos":   "resultado_pontos",
            "mfe_pontos":         "mfe_pontos",
            "mae_pontos":         "mae_pontos",
            "motivo":             "motivo",
            "created_at":         "created_at",
            "updated_at":         "updated_at",
        }
