from library.base.BaseModel import BaseModel


class ClaudeTraderMt5OrdensModel(BaseModel):
    """Entrega da ordem do Claude Trader pra uma conta MT5 — 1 linha por entrega real
    (abrir/mover_stop/encerrar) feita a uma conta. Não grava nada quando não há mudança."""

    def table(self):
        return 'claude_trader_mt5_ordens'

    def pk(self):
        return 'id_ordem'

    def fields(self):
        return {
            "id_ordem":                     "id_ordem",
            "id_operacao":                  "id_operacao",
            "account_number":               "account_number",
            "id_estrategia":                "id_estrategia",
            "status":                       "status",
            "tipo_posicao":                 "tipo_posicao",
            "acao":                         "acao",
            "preco_entrada":                "preco_entrada",
            "stop_loss":                    "stop_loss",
            "stop_gain":                    "stop_gain",
            "posicao_atual_recebida":       "posicao_atual_recebida",
            "tem_posicao_aberta_recebida":  "tem_posicao_aberta_recebida",
            "tipo_posicao_mt5_recebida":    "tipo_posicao_mt5_recebida",
            "motivo":                       "motivo",
            "created_at":                   "created_at",
        }
